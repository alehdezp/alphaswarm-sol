"""Phase 12: Micro-Agent Framework.

This module provides the base framework for micro-agents - isolated
AI agents that perform specific verification or test generation tasks.

Micro-agents receive a VulnerabilityBead as context and return structured
results. They can be spawned by either:
1. Parent AI agent (Claude Code, Codex, etc.)
2. VKG itself (for batch operations, CI/CD)

Key features:
- Isolated context (no cross-contamination)
- Budget control
- Structured output
- Timeout enforcement
- Cost tracking

Usage:
    from alphaswarm_sol.agents.microagent import (
        MicroAgent,
        MicroAgentConfig,
        MicroAgentResult,
        MicroAgentStatus,
    )

    # Create verification micro-agent
    config = MicroAgentConfig(
        agent_type="verifier",
        budget_usd=0.50,
        timeout_seconds=120,
    )

    agent = MicroAgent(config)
    result = await agent.execute(bead)
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic
import logging

from alphaswarm_sol.beads import VulnerabilityBead, Verdict, VerdictType
from alphaswarm_sol.agents.sdk import (
    SDKManager,
    SDKType,
    SDKInfo,
    SDKConfig,
    sdk_available,
    get_fallback_message,
)


logger = logging.getLogger(__name__)


class MicroAgentType(str, Enum):
    """Types of micro-agents."""
    VERIFIER = "verifier"         # Confirms/rejects findings
    TEST_GENERATOR = "test_gen"   # Generates exploit tests
    ATTACKER = "attacker"         # Constructs attack scenarios
    DEFENDER = "defender"         # Finds mitigating factors
    DEBATER = "debater"           # Multi-agent debate


class MicroAgentStatus(str, Enum):
    """Status of micro-agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BUDGET_EXCEEDED = "budget_exceeded"


@dataclass
class MicroAgentConfig:
    """Configuration for a micro-agent.

    Attributes:
        agent_type: Type of micro-agent
        budget_usd: Maximum cost in USD
        timeout_seconds: Timeout for execution
        max_turns: Maximum interaction turns
        allowed_tools: Tools the agent can use
        sdk_preference: Preferred SDK (auto-selects if None)
    """
    agent_type: MicroAgentType
    budget_usd: float = 0.50
    timeout_seconds: int = 120
    max_turns: int = 15
    allowed_tools: List[str] = field(default_factory=lambda: ["Read", "Bash"])
    sdk_preference: Optional[SDKType] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_type": self.agent_type.value,
            "budget_usd": self.budget_usd,
            "timeout_seconds": self.timeout_seconds,
            "max_turns": self.max_turns,
            "allowed_tools": self.allowed_tools,
            "sdk_preference": self.sdk_preference.value if self.sdk_preference else None,
        }


@dataclass
class MicroAgentCost:
    """Cost tracking for micro-agent execution.

    Attributes:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
        total_tokens: Total tokens used
        estimated_cost_usd: Estimated cost in USD
        actual_cost_usd: Actual cost if available
    """
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    actual_cost_usd: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "actual_cost_usd": self.actual_cost_usd,
        }


@dataclass
class MicroAgentResult:
    """Result from micro-agent execution.

    Attributes:
        agent_type: Type of agent that produced this
        status: Execution status
        verdict: Verdict if verification agent
        evidence: Evidence supporting the verdict
        reasoning: Agent's reasoning
        output: Raw output from the agent
        cost: Cost tracking
        duration_seconds: Execution time
        sdk_used: Which SDK was used
        error: Error message if failed
    """
    agent_type: MicroAgentType
    status: MicroAgentStatus
    verdict: Optional[VerdictType] = None
    evidence: List[str] = field(default_factory=list)
    reasoning: str = ""
    output: Optional[str] = None
    cost: MicroAgentCost = field(default_factory=MicroAgentCost)
    duration_seconds: float = 0.0
    sdk_used: Optional[SDKType] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "verdict": self.verdict.value if self.verdict else None,
            "evidence": self.evidence,
            "reasoning": self.reasoning,
            "output": self.output,
            "cost": self.cost.to_dict(),
            "duration_seconds": self.duration_seconds,
            "sdk_used": self.sdk_used.value if self.sdk_used else None,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MicroAgentResult":
        """Create from dictionary."""
        return cls(
            agent_type=MicroAgentType(data["agent_type"]),
            status=MicroAgentStatus(data["status"]),
            verdict=VerdictType(data["verdict"]) if data.get("verdict") else None,
            evidence=data.get("evidence", []),
            reasoning=data.get("reasoning", ""),
            output=data.get("output"),
            cost=MicroAgentCost(**data.get("cost", {})),
            duration_seconds=data.get("duration_seconds", 0.0),
            sdk_used=SDKType(data["sdk_used"]) if data.get("sdk_used") else None,
            error=data.get("error"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
        )

    @property
    def is_success(self) -> bool:
        """Whether execution succeeded."""
        return self.status == MicroAgentStatus.COMPLETED

    @property
    def is_confirmed(self) -> bool:
        """Whether vulnerability was confirmed."""
        return self.verdict == VerdictType.TRUE_POSITIVE

    @property
    def is_rejected(self) -> bool:
        """Whether finding was rejected."""
        return self.verdict == VerdictType.FALSE_POSITIVE


class MicroAgent(ABC):
    """Abstract base class for micro-agents.

    Micro-agents perform isolated verification or generation tasks.
    Each agent receives a VulnerabilityBead and returns structured results.
    """

    def __init__(self, config: MicroAgentConfig):
        """Initialize micro-agent.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.sdk_manager = SDKManager()
        self._sdk_info: Optional[SDKInfo] = None

    @property
    @abstractmethod
    def agent_type(self) -> MicroAgentType:
        """Return the type of this agent."""
        pass

    @abstractmethod
    async def execute(self, bead: VulnerabilityBead) -> MicroAgentResult:
        """Execute the micro-agent task.

        Args:
            bead: VulnerabilityBead context

        Returns:
            MicroAgentResult with verdict and evidence
        """
        pass

    @abstractmethod
    def build_prompt(self, bead: VulnerabilityBead) -> str:
        """Build the prompt for the agent.

        Args:
            bead: VulnerabilityBead context

        Returns:
            Prompt string
        """
        pass

    def get_sdk(self) -> Optional[SDKInfo]:
        """Get the SDK to use for execution.

        Returns:
            SDKInfo or None if no SDK available
        """
        if self._sdk_info is not None:
            return self._sdk_info

        if self.config.sdk_preference:
            info = self.sdk_manager.detect_one(self.config.sdk_preference)
            if info.is_available:
                self._sdk_info = info
                return info

        self._sdk_info = self.sdk_manager.get_best_available()
        return self._sdk_info

    def sdk_available(self) -> bool:
        """Check if any SDK is available."""
        return self.get_sdk() is not None

    def _create_error_result(self, error: str) -> MicroAgentResult:
        """Create an error result."""
        return MicroAgentResult(
            agent_type=self.agent_type,
            status=MicroAgentStatus.FAILED,
            error=error,
        )

    def _create_timeout_result(self, duration: float) -> MicroAgentResult:
        """Create a timeout result."""
        return MicroAgentResult(
            agent_type=self.agent_type,
            status=MicroAgentStatus.TIMEOUT,
            duration_seconds=duration,
            error=f"Execution timed out after {duration:.1f}s",
        )

    def _build_learning_overlay_context(self, bead: VulnerabilityBead) -> str:
        """Build compact overlay context from post-bead learning."""
        try:
            from alphaswarm_sol.learning.post_bead import (
                DEFAULT_LEARNING_DIR,
                build_finding_stub,
                load_learning_config,
            )
            from alphaswarm_sol.learning.overlay import (
                LearningOverlayStore,
                format_overlay_context,
            )
            from alphaswarm_sol.learning.fp_recorder import FalsePositiveRecorder
        except Exception:
            return ""

        config = load_learning_config(DEFAULT_LEARNING_DIR)
        if not config.overlay_enabled and not config.fp_enabled:
            return ""

        labels = []
        edges = []
        if config.overlay_enabled and bead.function_id:
            store = LearningOverlayStore(
                DEFAULT_LEARNING_DIR,
                min_confidence=config.min_confidence,
            )
            labels = store.get_labels(
                bead.function_id,
                category=bead.vulnerability_class,
                max_items=5,
            )
            edges = store.get_edges(
                bead.function_id,
                category=bead.vulnerability_class,
                max_items=3,
            )

        warnings = []
        if config.fp_enabled:
            recorder = FalsePositiveRecorder(DEFAULT_LEARNING_DIR)
            stub = build_finding_stub(bead)
            warnings = [w.message for w in recorder.get_warnings(stub)]

        return format_overlay_context(labels, edges, warnings)

    async def _execute_with_sdk(
        self,
        prompt: str,
        sdk: SDKInfo,
    ) -> MicroAgentResult:
        """Execute using the specified SDK.

        This is a placeholder - actual SDK integration would call
        the SDK's API to spawn a subprocess agent.

        Args:
            prompt: The prompt to send
            sdk: SDK to use

        Returns:
            MicroAgentResult
        """
        start_time = time.time()

        try:
            if sdk.sdk_type == SDKType.MOCK:
                # Mock execution for testing
                await asyncio.sleep(0.1)
                return MicroAgentResult(
                    agent_type=self.agent_type,
                    status=MicroAgentStatus.COMPLETED,
                    verdict=VerdictType.INCONCLUSIVE,
                    evidence=["Mock execution - no real analysis performed"],
                    reasoning="Mock SDK used for testing",
                    output="MOCK OUTPUT",
                    cost=MicroAgentCost(
                        input_tokens=100,
                        output_tokens=50,
                        total_tokens=150,
                        estimated_cost_usd=0.01,
                    ),
                    duration_seconds=time.time() - start_time,
                    sdk_used=sdk.sdk_type,
                )

            # For real SDKs, we would call their APIs here
            # This is the integration point for Claude/Codex/OpenCode

            # Currently returns a placeholder result
            # indicating SDK is available but integration pending
            return MicroAgentResult(
                agent_type=self.agent_type,
                status=MicroAgentStatus.COMPLETED,
                verdict=VerdictType.INCONCLUSIVE,
                evidence=["SDK integration pending"],
                reasoning=f"{sdk.sdk_type.value} SDK detected but full integration pending",
                output=f"SDK: {sdk.sdk_type.value}, Version: {sdk.version}",
                cost=MicroAgentCost(
                    estimated_cost_usd=0.0,
                ),
                duration_seconds=time.time() - start_time,
                sdk_used=sdk.sdk_type,
            )

        except asyncio.TimeoutError:
            return self._create_timeout_result(time.time() - start_time)
        except Exception as e:
            return self._create_error_result(str(e))


class VerificationMicroAgent(MicroAgent):
    """Micro-agent for verifying findings.

    Takes a VulnerabilityBead and determines if the finding is:
    - TRUE_POSITIVE: Real vulnerability
    - FALSE_POSITIVE: Not actually vulnerable
    - INCONCLUSIVE: Unable to determine

    Usage:
        agent = VerificationMicroAgent(config)
        result = await agent.execute(bead)
        if result.is_confirmed:
            print("Vulnerability confirmed!")
    """

    @property
    def agent_type(self) -> MicroAgentType:
        return MicroAgentType.VERIFIER

    def build_prompt(self, bead: VulnerabilityBead) -> str:
        """Build verification prompt from bead.

        Args:
            bead: VulnerabilityBead context

        Returns:
            Verification prompt
        """
        llm_prompt = bead.get_llm_prompt()
        learning_context = self._build_learning_overlay_context(bead)
        if learning_context:
            llm_prompt = f"{llm_prompt}\n\n{learning_context}"

        return f"""
You are a smart contract security expert verifying a potential vulnerability.

## Finding Context
{llm_prompt}

## Your Task
Analyze the code and evidence to determine if this is a real vulnerability.

1. Read the relevant source code files
2. Trace the execution path
3. Check for any mitigating factors (guards, modifiers, etc.)
4. Consider the attack scenario - is it practically exploitable?

## Output Format
Respond with a JSON object:
```json
{{
  "verdict": "TRUE_POSITIVE" | "FALSE_POSITIVE" | "INCONCLUSIVE",
  "confidence": 0.0-1.0,
  "evidence": ["list", "of", "evidence"],
  "reasoning": "Your detailed reasoning",
  "mitigating_factors": ["any", "guards", "found"]
}}
```

Focus on being accurate, not fast. A wrong verdict is worse than inconclusive.
"""

    async def execute(self, bead: VulnerabilityBead) -> MicroAgentResult:
        """Execute verification.

        Args:
            bead: VulnerabilityBead to verify

        Returns:
            MicroAgentResult with verdict
        """
        start_time = time.time()

        # Check SDK availability
        sdk = self.get_sdk()
        if not sdk:
            return self._create_error_result(get_fallback_message())

        # Build prompt
        prompt = self.build_prompt(bead)

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                self._execute_with_sdk(prompt, sdk),
                timeout=self.config.timeout_seconds
            )
            result.duration_seconds = time.time() - start_time
            return result

        except asyncio.TimeoutError:
            return self._create_timeout_result(time.time() - start_time)


class TestGenMicroAgent(MicroAgent):
    """Micro-agent for generating exploit tests.

    Takes a VulnerabilityBead and generates a Foundry/Hardhat test
    that exploits the vulnerability (or proves it's not exploitable).

    The agent can iterate - if the test doesn't compile, it fixes
    and retries internally.

    Usage:
        agent = TestGenMicroAgent(config)
        result = await agent.execute(bead)
        if result.is_success:
            print(result.test_code)
    """

    @property
    def agent_type(self) -> MicroAgentType:
        return MicroAgentType.TEST_GENERATOR

    def build_prompt(self, bead: VulnerabilityBead) -> str:
        """Build test generation prompt from bead.

        Args:
            bead: VulnerabilityBead context

        Returns:
            Test generation prompt
        """
        llm_prompt = bead.get_llm_prompt()
        learning_context = self._build_learning_overlay_context(bead)
        if learning_context:
            llm_prompt = f"{llm_prompt}\n\n{learning_context}"

        # Get test scaffold if available
        test_scaffold = ""
        if bead.test_context:
            test_scaffold = f"""
## Test Scaffold
```solidity
{bead.test_context.scaffold_code or '// No scaffold available'}
```
"""

        return f"""
You are a smart contract security expert writing an exploit test.

## Finding Context
{llm_prompt}

{test_scaffold}

## Your Task
Write a Foundry test that demonstrates this vulnerability.

1. Read the contract source code
2. Understand the attack vector
3. Write a test that exploits the vulnerability
4. If the test doesn't compile, fix it and retry
5. Run the test to verify it works

## Requirements
- Use Foundry (forge) for the test
- Include clear comments explaining each step
- The test should FAIL if the vulnerability is fixed
- Include setup with necessary state

## Output Format
```json
{{
  "test_code": "// Your Foundry test code here",
  "compile_success": true/false,
  "test_result": "PASS" | "FAIL" | "SKIP",
  "iterations": 1-3,
  "reasoning": "Why this test demonstrates the vulnerability"
}}
```

Focus on creating a working test, not speed.
"""

    async def execute(self, bead: VulnerabilityBead) -> MicroAgentResult:
        """Execute test generation.

        Args:
            bead: VulnerabilityBead to generate test for

        Returns:
            MicroAgentResult with test code
        """
        start_time = time.time()

        sdk = self.get_sdk()
        if not sdk:
            return self._create_error_result(get_fallback_message())

        prompt = self.build_prompt(bead)

        try:
            result = await asyncio.wait_for(
                self._execute_with_sdk(prompt, sdk),
                timeout=self.config.timeout_seconds
            )
            result.duration_seconds = time.time() - start_time
            return result

        except asyncio.TimeoutError:
            return self._create_timeout_result(time.time() - start_time)


# Factory functions

def create_verifier(
    budget_usd: float = 0.50,
    timeout_seconds: int = 120,
    max_turns: int = 15,
) -> VerificationMicroAgent:
    """Create a verification micro-agent.

    Args:
        budget_usd: Maximum cost
        timeout_seconds: Timeout
        max_turns: Maximum interaction turns

    Returns:
        Configured VerificationMicroAgent
    """
    config = MicroAgentConfig(
        agent_type=MicroAgentType.VERIFIER,
        budget_usd=budget_usd,
        timeout_seconds=timeout_seconds,
        max_turns=max_turns,
        allowed_tools=["Read", "Bash"],
    )
    return VerificationMicroAgent(config)


def create_test_generator(
    budget_usd: float = 1.00,
    timeout_seconds: int = 180,
    max_turns: int = 20,
) -> TestGenMicroAgent:
    """Create a test generation micro-agent.

    Args:
        budget_usd: Maximum cost
        timeout_seconds: Timeout
        max_turns: Maximum interaction turns

    Returns:
        Configured TestGenMicroAgent
    """
    config = MicroAgentConfig(
        agent_type=MicroAgentType.TEST_GENERATOR,
        budget_usd=budget_usd,
        timeout_seconds=timeout_seconds,
        max_turns=max_turns,
        allowed_tools=["Read", "Bash", "Write"],
    )
    return TestGenMicroAgent(config)
