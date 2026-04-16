"""Tool finding to bead conversion.

This module converts deduplicated tool findings (VKGFinding) into
VulnerabilityBeads ready for multi-agent verification.

Key principles (from PHILOSOPHY.md):
- All tool findings start with confidence=0.3 (uncertain)
- Tool findings must go through multi-agent verification
- Beads preserve tool-specific context for investigation

Model tier: haiku-4.5 (parsing, conversion - no reasoning required)

Usage:
    from alphaswarm_sol.beads.from_tools import create_beads_from_tools, ToolFindingToBead
    from alphaswarm_sol.tools.adapters.sarif import VKGFinding

    findings = [VKGFinding(...), ...]
    beads = create_beads_from_tools(findings, project_path)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..tools.adapters.sarif import VKGFinding
from .schema import (
    InvestigationGuide,
    PatternContext,
    TestContext,
    VulnerabilityBead,
)
from .types import (
    BeadStatus,
    CodeSnippet,
    ExploitReference,
    InvestigationStep,
    Severity,
)

# Optional import for knowledge graph
try:
    from ..kg.schema import KnowledgeGraph
except ImportError:
    KnowledgeGraph = None  # type: ignore


# Confidence for tool-generated beads (PHILOSOPHY.md: uncertain)
TOOL_FINDING_CONFIDENCE = 0.3


@dataclass
class ToolBeadContext:
    """Additional context from tool analysis.

    Captures tool-specific metadata that helps in verification.

    Attributes:
        tool_sources: Tools that found this issue (for cross-tool agreement)
        tool_confidence: Per-tool confidence mapping
        detector_ids: Original detector IDs from each tool
        sarif_data: Raw SARIF data if available
    """

    tool_sources: List[str] = field(default_factory=list)
    tool_confidence: Dict[str, float] = field(default_factory=dict)
    detector_ids: List[str] = field(default_factory=list)
    sarif_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tool_sources": self.tool_sources,
            "tool_confidence": self.tool_confidence,
            "detector_ids": self.detector_ids,
            "sarif_data": self.sarif_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolBeadContext":
        """Create ToolBeadContext from dictionary."""
        return cls(
            tool_sources=data.get("tool_sources", []),
            tool_confidence=data.get("tool_confidence", {}),
            detector_ids=data.get("detector_ids", []),
            sarif_data=data.get("sarif_data"),
        )


class ToolFindingToBead:
    """Convert tool findings to VulnerabilityBeads.

    Transforms VKGFinding objects (from tool adapters) into complete
    VulnerabilityBead objects ready for multi-agent verification.

    Model tier: haiku-4.5 (parsing, conversion - no reasoning required)

    Example:
        converter = ToolFindingToBead(project_path)
        bead = converter.create_bead(finding, ['slither', 'aderyn'])
    """

    MODEL_TIER = "haiku-4.5"

    # Context lines to include around finding
    CONTEXT_LINES_BEFORE = 5
    CONTEXT_LINES_AFTER = 5

    def __init__(
        self,
        project_path: Path,
        graph: Optional["KnowledgeGraph"] = None,
    ):
        """Initialize converter.

        Args:
            project_path: Root path of the Solidity project
            graph: Optional knowledge graph for enrichment
        """
        self.project_path = Path(project_path)
        self.graph = graph
        self._bead_counter = 0

    def create_bead(
        self,
        finding: VKGFinding,
        dedup_sources: Optional[List[str]] = None,
    ) -> VulnerabilityBead:
        """Create a bead from a tool finding.

        Per PHILOSOPHY.md:
        - All tool findings start as "uncertain" (confidence=0.3)
        - Must go through multi-agent verification

        Args:
            finding: VKGFinding from tool adapter
            dedup_sources: List of tools that found this (for deduplicated findings)

        Returns:
            VulnerabilityBead ready for verification
        """
        bead_id = self._generate_id(finding)
        sources = dedup_sources or [finding.source]

        # Extract code context
        code_snippet = self._extract_code_snippet(finding)

        # Build pattern context from tool info
        pattern_context = self._build_pattern_context(finding, sources)

        # Create investigation guide for tool finding
        investigation_guide = self._tool_investigation_guide(finding)

        # Build test context scaffold
        test_context = self._build_test_context(finding)

        # Get fix recommendations based on category
        fix_recs = self._get_fix_recommendations(finding.category)

        # Create bead with UNCERTAIN confidence
        return VulnerabilityBead(
            id=bead_id,
            vulnerability_class=finding.category,
            pattern_id=finding.rule_id,
            function_id=finding.function or "",
            severity=self._map_severity(finding.severity),
            confidence=TOOL_FINDING_CONFIDENCE,  # UNCERTAIN - must verify
            vulnerable_code=code_snippet,
            related_code=[],  # Will be populated by verification or enrichment
            full_contract=None,
            inheritance_chain=[],
            pattern_context=pattern_context,
            investigation_guide=investigation_guide,
            test_context=test_context,
            similar_exploits=self._find_similar_exploits(finding),
            fix_recommendations=fix_recs,
            status=BeadStatus.PENDING,
            graph_context=None,
            graph_context_category="",
            full_graph_available=self.graph is not None,
            # Tool-specific metadata
            metadata={
                "tool_sources": sources,
                "detector_ids": [finding.rule_id],
                "tool_confidence": finding.confidence,
                "from_tool": True,
                "original_title": finding.title,
                "sarif_id": finding.id,
            },
        )

    def create_beads_from_findings(
        self,
        findings: List[VKGFinding],
    ) -> List[VulnerabilityBead]:
        """Create beads from multiple findings.

        Args:
            findings: List of VKGFinding objects

        Returns:
            List of VulnerabilityBeads
        """
        beads = []
        for finding in findings:
            try:
                bead = self.create_bead(finding)
                beads.append(bead)
            except Exception as e:
                # Log error but continue processing
                import sys
                print(f"Error creating bead for finding {finding.id}: {e}", file=sys.stderr)
        return beads

    def _generate_id(self, finding: VKGFinding) -> str:
        """Generate unique bead ID from finding.

        Args:
            finding: VKGFinding to generate ID for

        Returns:
            Unique bead ID like "VKG-TOOL-0001-abc123"
        """
        self._bead_counter += 1
        # Create hash from key finding attributes
        hash_input = f"{finding.source}:{finding.rule_id}:{finding.file}:{finding.line}"
        hash_hex = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        return f"VKG-TOOL-{self._bead_counter:04d}-{hash_hex}"

    def _extract_code_snippet(self, finding: VKGFinding) -> CodeSnippet:
        """Extract code snippet from finding location.

        Reads actual file content and extracts context around the finding.

        Args:
            finding: VKGFinding with file and line info

        Returns:
            CodeSnippet with source and metadata
        """
        source = ""
        start_line = max(1, finding.line - self.CONTEXT_LINES_BEFORE)
        end_line = finding.end_line or finding.line
        end_line = end_line + self.CONTEXT_LINES_AFTER

        # Try to read actual file content
        file_path = self.project_path / finding.file
        try:
            if file_path.exists():
                lines = file_path.read_text().splitlines()
                # Extract context lines (1-indexed in finding, 0-indexed in list)
                extracted = lines[max(0, start_line - 1):end_line]
                source = "\n".join(extracted)
            else:
                # File not found, use description as placeholder
                source = f"// Source not found: {finding.file}:{finding.line}\n// {finding.description}"
        except Exception:
            source = f"// Error reading: {finding.file}:{finding.line}\n// {finding.description}"

        return CodeSnippet(
            source=source or f"// {finding.title}",
            file_path=finding.file,
            start_line=start_line,
            end_line=end_line,
            function_name=finding.function,
            contract_name=finding.contract,
        )

    def _build_pattern_context(
        self,
        finding: VKGFinding,
        sources: List[str],
    ) -> PatternContext:
        """Build pattern context from tool finding.

        Args:
            finding: VKGFinding to extract context from
            sources: List of tools that reported this

        Returns:
            PatternContext describing why flagged
        """
        # Build why_flagged from tool information
        if len(sources) > 1:
            source_str = ", ".join(sources)
            why_flagged = (
                f"Found by {len(sources)} tools ({source_str}): {finding.title}. "
                f"Original detector: {finding.rule_id}"
            )
        else:
            why_flagged = (
                f"Found by {finding.source}: {finding.title}. "
                f"Detector: {finding.rule_id}, Confidence: {finding.tool_confidence}"
            )

        return PatternContext(
            pattern_name=finding.rule_id,
            pattern_description=finding.description,
            why_flagged=why_flagged,
            matched_properties=[
                f"tool:{finding.source}",
                f"detector:{finding.rule_id}",
                f"category:{finding.category}",
            ],
            evidence_lines=[finding.line] if finding.line else [],
        )

    def _tool_investigation_guide(self, finding: VKGFinding) -> InvestigationGuide:
        """Create investigation guide tailored for tool findings.

        Tool findings need specific verification to distinguish from false positives.

        Args:
            finding: VKGFinding to create guide for

        Returns:
            InvestigationGuide with tool-appropriate steps
        """
        category = finding.category.lower()

        # Get category-specific steps
        steps = self._get_category_investigation_steps(category, finding)

        # Get category-specific questions
        questions = self._get_category_questions(category)

        # Get common false positives for this category
        false_positives = self._get_category_false_positives(category)

        # Get key indicators
        indicators = self._get_category_indicators(category)

        # Get safe patterns
        safe_patterns = self._get_category_safe_patterns(category)

        return InvestigationGuide(
            steps=steps,
            questions_to_answer=questions,
            common_false_positives=false_positives,
            key_indicators=indicators,
            safe_patterns=safe_patterns,
        )

    def _get_category_investigation_steps(
        self,
        category: str,
        finding: VKGFinding,
    ) -> List[InvestigationStep]:
        """Get investigation steps for vulnerability category.

        Args:
            category: Vulnerability category
            finding: The finding being investigated

        Returns:
            List of InvestigationStep objects
        """
        # Base steps for all tool findings
        base_steps = [
            InvestigationStep(
                step_number=1,
                action="Verify tool finding accuracy",
                look_for=f"Confirm {finding.rule_id} detection at {finding.file}:{finding.line}",
                evidence_needed="Code matches tool's reported pattern",
                red_flag="Tool misidentified the code pattern",
                safe_if="Tool made an obvious misdetection",
            ),
            InvestigationStep(
                step_number=2,
                action="Check for existing protections",
                look_for="Guards, modifiers, or access controls that prevent exploitation",
                evidence_needed="Protection mechanism found",
            ),
        ]

        # Category-specific steps
        category_steps = {
            "reentrancy": [
                InvestigationStep(
                    step_number=3,
                    action="Verify external call before state update",
                    look_for="External calls (call, send, transfer) before state writes",
                    evidence_needed="CEI violation confirmed",
                    red_flag="State update occurs after external call",
                    safe_if="CEI pattern followed or nonReentrant modifier present",
                ),
                InvestigationStep(
                    step_number=4,
                    action="Check reentrancy guards",
                    look_for="nonReentrant modifier, ReentrancyGuard, mutex patterns",
                    evidence_needed="Reentrancy guard found",
                ),
            ],
            "access_control": [
                InvestigationStep(
                    step_number=3,
                    action="Verify function should be restricted",
                    look_for="Privileged operations (ownership change, fund withdrawal)",
                    evidence_needed="Function performs privileged action",
                    red_flag="Privileged function callable by anyone",
                    safe_if="Function has appropriate access modifier",
                ),
                InvestigationStep(
                    step_number=4,
                    action="Check all access paths",
                    look_for="Direct and indirect ways to reach the function",
                    evidence_needed="All paths have appropriate checks",
                ),
            ],
            "oracle": [
                InvestigationStep(
                    step_number=3,
                    action="Verify oracle price is validated",
                    look_for="Staleness checks, price bounds, sequencer uptime",
                    evidence_needed="Price validation exists or is missing",
                    red_flag="Raw oracle price used without validation",
                    safe_if="Price has staleness and bounds checks",
                ),
            ],
        }

        additional_steps = category_steps.get(category, [
            InvestigationStep(
                step_number=3,
                action="Analyze specific vulnerability pattern",
                look_for=f"Evidence supporting {category} vulnerability",
                evidence_needed="Clear evidence of exploitability",
            ),
        ])

        return base_steps + additional_steps

    def _get_category_questions(self, category: str) -> List[str]:
        """Get investigation questions for category.

        Args:
            category: Vulnerability category

        Returns:
            List of questions to answer
        """
        base_questions = [
            "Is the tool's detection accurate for this code?",
            "Are there protections the tool didn't detect?",
            "What is the potential impact if exploited?",
        ]

        category_questions = {
            "reentrancy": [
                "Is there an external call before state update?",
                "Is the external call to a user-controlled address?",
                "Can the reentrancy drain significant value?",
            ],
            "access_control": [
                "Does the function perform privileged operations?",
                "Are there any implicit access controls?",
                "Can an attacker actually call this function?",
            ],
            "oracle": [
                "Is the oracle price validated for staleness?",
                "Can the oracle be manipulated (TWAP vs spot)?",
                "What's the potential loss from price manipulation?",
            ],
        }

        return base_questions + category_questions.get(category, [])

    def _get_category_false_positives(self, category: str) -> List[str]:
        """Get common false positive patterns for category.

        Args:
            category: Vulnerability category

        Returns:
            List of false positive descriptions
        """
        common = [
            "Tool misidentified safe code pattern",
            "Protection exists but wasn't detected by tool",
            "Context makes exploitation impractical",
        ]

        category_fps = {
            "reentrancy": [
                "CEI pattern followed but state write is after event emission",
                "External call is to trusted/immutable contract",
                "nonReentrant modifier applied in base contract",
            ],
            "access_control": [
                "Function is intentionally public (view/getter)",
                "Access control in called internal function",
                "Role check via modifier not detected",
            ],
            "oracle": [
                "Price only used for informational display",
                "TWAP oracle with sufficient window",
                "Multi-oracle aggregation provides protection",
            ],
        }

        return common + category_fps.get(category, [])

    def _get_category_indicators(self, category: str) -> List[str]:
        """Get key vulnerability indicators for category.

        Args:
            category: Vulnerability category

        Returns:
            List of key indicators
        """
        indicators = {
            "reentrancy": [
                "External call before state update",
                "User-controlled callback target",
                "Value transfer in vulnerable function",
            ],
            "access_control": [
                "Missing onlyOwner or role modifier",
                "Privileged state modification",
                "Fund transfer without auth check",
            ],
            "oracle": [
                "Missing staleness check (updatedAt)",
                "No price bounds validation",
                "Single oracle point of failure",
            ],
        }

        return indicators.get(category, ["Pattern matches vulnerability profile"])

    def _get_category_safe_patterns(self, category: str) -> List[str]:
        """Get safe code patterns for category.

        Args:
            category: Vulnerability category

        Returns:
            List of safe patterns
        """
        safe = {
            "reentrancy": [
                "Checks-Effects-Interactions pattern",
                "nonReentrant modifier from OpenZeppelin",
                "Pull payment pattern",
            ],
            "access_control": [
                "onlyOwner modifier applied",
                "Role-based access (AccessControl)",
                "Multi-sig requirement",
            ],
            "oracle": [
                "Staleness validation with maxDelay",
                "Price bounds checking",
                "TWAP with sufficient window",
            ],
        }

        return safe.get(category, ["Appropriate protection mechanism"])

    def _build_test_context(self, finding: VKGFinding) -> TestContext:
        """Build test context scaffold for tool finding.

        Args:
            finding: VKGFinding to create test for

        Returns:
            TestContext with scaffold and scenario
        """
        contract_name = finding.contract or "Target"
        function_name = finding.function or "vulnerableFunction"
        category = finding.category.lower()

        scaffold = self._generate_test_scaffold(contract_name, function_name, category)
        scenario = self._generate_attack_scenario(category)
        requirements = self._get_setup_requirements(category)
        outcome = self._get_expected_outcome(category)

        return TestContext(
            scaffold_code=scaffold,
            attack_scenario=scenario,
            setup_requirements=requirements,
            expected_outcome=outcome,
        )

    def _generate_test_scaffold(
        self,
        contract_name: str,
        function_name: str,
        category: str,
    ) -> str:
        """Generate Foundry test scaffold.

        Args:
            contract_name: Target contract name
            function_name: Target function name
            category: Vulnerability category

        Returns:
            Foundry test code scaffold
        """
        return f'''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "../src/{contract_name}.sol";

contract {contract_name}ToolFindingTest is Test {{
    {contract_name} target;
    address attacker = address(0xBAD);

    function setUp() public {{
        target = new {contract_name}();
        // TODO: Setup initial state
        // - Fund the contract if needed
        // - Set up attacker account
        // - Configure any dependencies
    }}

    function test_tool_finding_{function_name}() public {{
        // Test case for tool finding: {category}
        vm.startPrank(attacker);

        // TODO: Implement exploit for {category}
        // 1. Setup preconditions
        // 2. Execute attack
        // 3. Verify exploitation

        vm.stopPrank();

        // TODO: Add assertions to verify exploit success
    }}
}}
'''

    def _generate_attack_scenario(self, category: str) -> str:
        """Generate attack scenario description.

        Args:
            category: Vulnerability category

        Returns:
            Attack scenario description
        """
        scenarios = {
            "reentrancy": """
1. Attacker deploys malicious contract with fallback/receive
2. Attacker calls vulnerable function
3. During external call, attacker re-enters the function
4. State not yet updated, so check passes again
5. Repeat until funds drained or gas exhausted
""",
            "access_control": """
1. Attacker identifies unprotected privileged function
2. Attacker calls function directly without authorization
3. Privileged operation executes successfully
4. Attacker gains admin rights or extracts funds
""",
            "oracle": """
1. Attacker takes flash loan to get capital
2. Attacker manipulates oracle price (via swap, deposit, etc.)
3. Protocol reads manipulated price for valuation
4. Attacker profits from incorrect valuation
5. Attacker reverses manipulation and repays flash loan
""",
        }
        return scenarios.get(category, "TODO: Document specific attack scenario")

    def _get_setup_requirements(self, category: str) -> List[str]:
        """Get test setup requirements.

        Args:
            category: Vulnerability category

        Returns:
            List of setup requirements
        """
        requirements = {
            "reentrancy": [
                "Attacker contract with reentrant callback",
                "Target contract with funds to drain",
                "Ability to trigger external call",
            ],
            "access_control": [
                "Non-admin address (attacker)",
                "Target contract deployed with admin set",
                "Identify privileged function to target",
            ],
            "oracle": [
                "Manipulable price source (DEX, etc.)",
                "Flash loan provider for capital",
                "Target protocol using the oracle",
            ],
        }
        return requirements.get(category, ["TODO: Define requirements"])

    def _get_expected_outcome(self, category: str) -> str:
        """Get expected exploit outcome.

        Args:
            category: Vulnerability category

        Returns:
            Expected outcome description
        """
        outcomes = {
            "reentrancy": "Attacker extracts more funds than their fair share",
            "access_control": "Unauthorized privileged operation succeeds",
            "oracle": "Attacker profits from manipulated price valuation",
        }
        return outcomes.get(category, "Exploit succeeds with measurable impact")

    def _map_severity(self, severity_str: str) -> Severity:
        """Map tool severity string to Severity enum.

        Args:
            severity_str: Severity string from tool

        Returns:
            Severity enum value
        """
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
            "informational": Severity.INFO,
            "warning": Severity.MEDIUM,
            "error": Severity.HIGH,
        }
        return severity_map.get(severity_str.lower(), Severity.MEDIUM)

    def _get_fix_recommendations(self, category: str) -> List[str]:
        """Get fix recommendations for category.

        Args:
            category: Vulnerability category

        Returns:
            List of fix recommendations
        """
        recommendations = {
            "reentrancy": [
                "Follow Checks-Effects-Interactions (CEI) pattern",
                "Add nonReentrant modifier from OpenZeppelin",
                "Consider pull payment pattern instead of push",
                "Update state before any external calls",
            ],
            "access_control": [
                "Add onlyOwner or role-based modifier",
                "Use OpenZeppelin AccessControl for complex permissions",
                "Implement proper authorization checks",
                "Consider multi-sig for critical operations",
            ],
            "oracle": [
                "Add staleness check (block.timestamp - updatedAt < maxDelay)",
                "Validate price is positive and within bounds",
                "Use TWAP instead of spot prices",
                "Add L2 sequencer uptime check if applicable",
            ],
            "dos": [
                "Bound loop iterations with explicit max",
                "Use pull pattern instead of push for distributions",
                "Implement pagination for large data operations",
            ],
        }
        return recommendations.get(category, ["Review and fix the vulnerability"])

    def _find_similar_exploits(self, finding: VKGFinding) -> List[ExploitReference]:
        """Find similar real-world exploits.

        Args:
            finding: VKGFinding to find exploits for

        Returns:
            List of similar exploit references
        """
        # Try to load exploits from loader
        try:
            from .exploits.loader import find_exploits_by_class
            exploits = find_exploits_by_class(finding.category)
            return exploits[:3] if exploits else []
        except Exception:
            return []


def create_beads_from_tools(
    findings: List[VKGFinding],
    project_path: Path,
    graph: Optional["KnowledgeGraph"] = None,
) -> List[VulnerabilityBead]:
    """Convenience function for tool finding to bead conversion.

    Creates VulnerabilityBeads from tool findings with appropriate
    uncertain confidence level for multi-agent verification.

    Args:
        findings: List of VKGFinding objects from tool adapters
        project_path: Root path of the Solidity project
        graph: Optional knowledge graph for enrichment

    Returns:
        List of VulnerabilityBeads ready for verification

    Example:
        from alphaswarm_sol.tools.adapters.slither import SlitherAdapter

        adapter = SlitherAdapter()
        findings = adapter.run(Path("./contracts"))
        beads = create_beads_from_tools(findings, Path("./contracts"))
    """
    converter = ToolFindingToBead(project_path, graph)
    return converter.create_beads_from_findings(findings)


__all__ = [
    "TOOL_FINDING_CONFIDENCE",
    "ToolBeadContext",
    "ToolFindingToBead",
    "create_beads_from_tools",
]
