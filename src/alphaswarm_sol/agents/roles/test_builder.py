"""Test Builder Agent for Generating Foundry Exploit Tests.

This module provides the TestBuilderAgent class for generating Foundry
exploit tests from vulnerability beads.

Per 05.2-CONTEXT.md:
- LLM-generated with pattern/docs assistance
- VulnDocs always retrieved for grounding
- Tests stored in pool directory
- Pass = confirmed confidence

Usage:
    from alphaswarm_sol.agents.roles import TestBuilderAgent, TestGenerationConfig

    builder = TestBuilderAgent(
        runtime=agent_runtime,
        project_path=project_path,
        config=TestGenerationConfig(include_vulndocs=True),
    )

    result = await builder.generate_test(bead)
    if result.test_passed:
        print("Vulnerability confirmed via exploit test")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from alphaswarm_sol.agents.roles.foundry import (
    ForgeBuildResult,
    ForgeTestResult,
    FoundryRunner,
)
from alphaswarm_sol.agents.roles.prompts import TEST_BUILDER_SYSTEM_PROMPT
from alphaswarm_sol.agents.runtime import AgentConfig, AgentResponse, AgentRole, AgentRuntime
from alphaswarm_sol.beads.schema import VulnerabilityBead

logger = logging.getLogger(__name__)


# =============================================================================
# VulnDocs Retrieval Protocol
# =============================================================================


class VulnDocsRetrieverProtocol(Protocol):
    """Protocol for VulnDocs retrieval interface.

    Defines the interface for retrieving VulnDocs documentation.
    Implementations can vary (KnowledgeNavigator, mock for tests).
    """

    def retrieve(
        self,
        vulnerability_class: str,
        max_docs: int = 3,
    ) -> List[Any]:
        """Retrieve relevant VulnDocs for a vulnerability class.

        Args:
            vulnerability_class: The vulnerability category (e.g., "reentrancy")
            max_docs: Maximum number of documents to retrieve

        Returns:
            List of document objects with title and content attributes
        """
        ...


@dataclass
class VulnDoc:
    """Simple VulnDoc representation for test builder."""
    title: str
    content: str


class DefaultVulnDocsRetriever:
    """Default VulnDocs retriever using KnowledgeNavigator.

    Falls back gracefully if knowledge system is not available.
    """

    def __init__(self):
        self._navigator = None
        self._initialized = False

    def _init_navigator(self) -> None:
        """Lazy initialization of KnowledgeNavigator."""
        if self._initialized:
            return
        self._initialized = True
        try:
            from alphaswarm_sol.knowledge.vulndocs import KnowledgeNavigator
            self._navigator = KnowledgeNavigator()
        except ImportError:
            logger.warning("KnowledgeNavigator not available, VulnDocs disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize KnowledgeNavigator: {e}")

    def retrieve(
        self,
        vulnerability_class: str,
        max_docs: int = 3,
    ) -> List[VulnDoc]:
        """Retrieve VulnDocs for a vulnerability class.

        Args:
            vulnerability_class: The vulnerability category
            max_docs: Maximum documents to return

        Returns:
            List of VulnDoc objects with title and content
        """
        self._init_navigator()
        if self._navigator is None:
            return []

        docs = []
        try:
            # Try to get category and subcategory context
            categories = self._navigator.list_categories()
            # Find matching category
            for cat_id in categories:
                if vulnerability_class.lower() in cat_id.lower():
                    try:
                        context = self._navigator.get_context(cat_id, depth="detection")
                        docs.append(VulnDoc(
                            title=f"Detection Guide: {cat_id}",
                            content=context,
                        ))
                        if len(docs) >= max_docs:
                            break
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"VulnDocs retrieval failed: {e}")

        return docs


# =============================================================================
# Configuration and Result Types
# =============================================================================


@dataclass
class TestGenerationConfig:
    """Configuration for test generation.

    Attributes:
        max_attempts: Maximum retry attempts on compile failure
        include_vulndocs: Whether to retrieve and include VulnDocs context
        test_dir: Directory for test files (relative to project root)
        verbose: Enable verbose logging
        timeout_seconds: Timeout for LLM generation
    """
    max_attempts: int = 3
    include_vulndocs: bool = True
    test_dir: str = "test"
    verbose: bool = False
    timeout_seconds: int = 300

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_attempts": self.max_attempts,
            "include_vulndocs": self.include_vulndocs,
            "test_dir": self.test_dir,
            "verbose": self.verbose,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class GeneratedTest:
    """Result of test generation.

    Attributes:
        bead_id: ID of the bead this test was generated for
        test_code: The generated Solidity test code
        test_file: Path to the test file (relative to project root)
        expected_outcome: What a passing test proves
        compile_result: Result of forge build
        test_results: List of test execution results
        vulndocs_used: List of VulnDocs titles used for grounding
    """
    bead_id: str
    test_code: str
    test_file: str
    expected_outcome: str
    compile_result: Optional[ForgeBuildResult] = None
    test_results: List[ForgeTestResult] = field(default_factory=list)
    vulndocs_used: List[str] = field(default_factory=list)

    @property
    def test_passed(self) -> bool:
        """Whether any test passed (proving vulnerability)."""
        return any(r.passed for r in self.test_results)

    @property
    def compile_success(self) -> bool:
        """Whether compilation succeeded."""
        return self.compile_result is not None and self.compile_result.success

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bead_id": self.bead_id,
            "test_code": self.test_code,
            "test_file": self.test_file,
            "expected_outcome": self.expected_outcome,
            "compile_success": self.compile_success,
            "test_passed": self.test_passed,
            "test_results": [r.to_dict() for r in self.test_results],
            "vulndocs_used": self.vulndocs_used,
        }


# =============================================================================
# Test Builder Agent
# =============================================================================


class TestBuilderAgent:
    """Generates Foundry tests from vulnerability beads.

    Per 05.2-CONTEXT.md decisions:
    - LLM-generated with pattern/docs assistance
    - VulnDocs always retrieved for grounding
    - Tests stored in pool directory
    - Pass = confirmed confidence

    The TestBuilderAgent orchestrates:
    1. VulnDocs retrieval for grounding
    2. LLM prompt construction with bead context
    3. Test code generation via agent runtime
    4. Compilation and testing via Foundry
    5. Retry loop on compilation failures

    Usage:
        builder = TestBuilderAgent(
            runtime=agent_runtime,
            project_path=project_path,
            config=TestGenerationConfig(include_vulndocs=True),
        )

        result = await builder.generate_test(bead)
        if result.test_passed:
            # Vulnerability confirmed via exploit test
            bead.confidence = 1.0
    """

    def __init__(
        self,
        runtime: AgentRuntime,
        project_path: Path,
        config: Optional[TestGenerationConfig] = None,
        vulndocs_retriever: Optional[VulnDocsRetrieverProtocol] = None,
    ):
        """Initialize the Test Builder agent.

        Args:
            runtime: Agent runtime for LLM execution
            project_path: Path to the Foundry project
            config: Test generation configuration
            vulndocs_retriever: Optional custom VulnDocs retriever
        """
        self.runtime = runtime
        self.project_path = Path(project_path)
        self.config = config or TestGenerationConfig()
        self.vulndocs = vulndocs_retriever or DefaultVulnDocsRetriever()
        self.foundry = FoundryRunner(project_path)

    async def generate_test(self, bead: VulnerabilityBead) -> GeneratedTest:
        """Generate and validate Foundry test for a bead.

        This is the main entry point for test generation. It:
        1. Retrieves relevant VulnDocs for grounding
        2. Builds an LLM prompt with bead context
        3. Generates test code via LLM
        4. Writes and compiles the test
        5. Retries on compile failure (with error feedback)
        6. Runs the test if compilation succeeds

        Args:
            bead: VulnerabilityBead to generate test for

        Returns:
            GeneratedTest with code, compile results, and test results
        """
        # 1. Retrieve relevant VulnDocs for grounding
        vulndocs_context = ""
        vulndocs_used: List[str] = []
        if self.config.include_vulndocs:
            docs = self.vulndocs.retrieve(
                vulnerability_class=bead.vulnerability_class,
                max_docs=3,
            )
            for doc in docs:
                vulndocs_context += f"\n\n## {doc.title}\n{doc.content}"
                vulndocs_used.append(doc.title)
            if self.config.verbose:
                logger.info(f"Retrieved {len(docs)} VulnDocs for {bead.vulnerability_class}")

        # 2. Build prompt with bead context
        prompt = self._build_prompt(bead, vulndocs_context)

        # 3. Generate test via LLM
        agent_config = AgentConfig(
            role=AgentRole.TEST_BUILDER,
            system_prompt=TEST_BUILDER_SYSTEM_PROMPT,
            tools=[],  # No tools needed for generation
            timeout_seconds=self.config.timeout_seconds,
        )

        response = await self.runtime.spawn_agent(agent_config, prompt)

        # 4. Parse test code from response
        test_code = self._extract_test_code(response.content)
        test_file = self._generate_test_filename(bead)
        expected_outcome = self._extract_expected_outcome(response.content)

        # 5. Write and compile test
        self.foundry.write_test(test_code, test_file)
        compile_result = self.foundry.build()

        # 6. If compile fails, retry with error feedback
        attempts = 1
        while not compile_result.success and attempts < self.config.max_attempts:
            logger.info(f"Compile failed, retrying ({attempts}/{self.config.max_attempts})")
            fix_prompt = self._build_fix_prompt(test_code, compile_result.errors)
            fix_response = await self.runtime.spawn_agent(agent_config, fix_prompt)
            test_code = self._extract_test_code(fix_response.content)
            self.foundry.write_test(test_code, test_file)
            compile_result = self.foundry.build()
            attempts += 1

        # 7. Run test if compile succeeded
        test_results: List[ForgeTestResult] = []
        if compile_result.success:
            test_results = self.foundry.test(test_file=test_file)
            if self.config.verbose:
                passed = sum(1 for r in test_results if r.passed)
                total = len(test_results)
                logger.info(f"Test results: {passed}/{total} passed")

        return GeneratedTest(
            bead_id=bead.id,
            test_code=test_code,
            test_file=test_file,
            expected_outcome=expected_outcome,
            compile_result=compile_result,
            test_results=test_results,
            vulndocs_used=vulndocs_used,
        )

    def _build_prompt(self, bead: VulnerabilityBead, vulndocs_context: str) -> str:
        """Build LLM prompt for test generation.

        Args:
            bead: The vulnerability bead
            vulndocs_context: Retrieved VulnDocs context

        Returns:
            Formatted prompt string for LLM
        """
        # Extract severity value safely
        severity_value = (
            bead.severity.value
            if hasattr(bead.severity, "value")
            else str(bead.severity)
        )

        prompt = f"""Generate a Foundry exploit test for the following vulnerability:

## Vulnerability Summary
- **ID:** {bead.id}
- **Class:** {bead.vulnerability_class}
- **Severity:** {severity_value}
- **Pattern:** {bead.pattern_context.pattern_name}

## Why Flagged
{bead.pattern_context.why_flagged}

## Vulnerable Code
```solidity
{bead.vulnerable_code.source}
```
Location: {bead.vulnerable_code.file_path}:{bead.vulnerable_code.start_line}

## Test Context
{bead.test_context.attack_scenario}
Expected outcome: {bead.test_context.expected_outcome}
"""

        if vulndocs_context:
            prompt += f"""
## VulnDocs Reference
{vulndocs_context}
"""

        prompt += """
## Instructions
1. Write a complete Foundry test that demonstrates this vulnerability
2. Include setUp() to deploy necessary contracts
3. Test function should be named test_[vulnerability_type]_exploit
4. Use assertions to verify the exploit succeeded
5. Add comments explaining each step

Return the complete test file.
"""
        return prompt

    def _build_fix_prompt(self, test_code: str, errors: List[str]) -> str:
        """Build prompt to fix compile errors.

        Args:
            test_code: The test code that failed to compile
            errors: List of compilation errors

        Returns:
            Formatted prompt for error fixing
        """
        return f"""The following test failed to compile:

```solidity
{test_code}
```

## Compile Errors
{chr(10).join(errors)}

Please fix the errors and return the corrected test code.
Ensure all imports are correct and types match.
"""

    def _extract_test_code(self, response: str) -> str:
        """Extract Solidity code from LLM response.

        Args:
            response: LLM response text

        Returns:
            Extracted Solidity code
        """
        # Find code block with solidity language tag
        match = re.search(r"```solidity\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try generic code block
        match = re.search(r"```\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Fallback: assume entire response is code if no block found
        return response.strip()

    def _extract_expected_outcome(self, response: str) -> str:
        """Extract expected outcome from response.

        Args:
            response: LLM response text

        Returns:
            Expected outcome description
        """
        # Look for expected_outcome pattern
        match = re.search(
            r"expected[_\s]outcome:?\s*(.+?)(?:\n|$)",
            response,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        return "Exploit test demonstrates vulnerability"

    def _generate_test_filename(self, bead: VulnerabilityBead) -> str:
        """Generate test filename from bead ID.

        Args:
            bead: The vulnerability bead

        Returns:
            Test file path relative to project root
        """
        # Sanitize bead ID for filename
        safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", bead.id)
        return f"{self.config.test_dir}/Exploit_{safe_id}.t.sol"


# Export for module
__all__ = [
    "TestBuilderAgent",
    "TestGenerationConfig",
    "GeneratedTest",
    "VulnDocsRetrieverProtocol",
    "DefaultVulnDocsRetriever",
    "VulnDoc",
]
