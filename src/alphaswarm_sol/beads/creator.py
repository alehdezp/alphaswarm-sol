"""Bead creation from pattern matches.

This module provides the core integration between VKG's pattern engine
and the beads system. It creates self-contained VulnerabilityBead objects
from pattern match findings.

Usage:
    from alphaswarm_sol.beads.creator import BeadCreator, create_bead

    # Create beads from findings
    creator = BeadCreator(graph)
    findings = pattern_engine.run(graph, patterns)
    beads = creator.create_beads_from_findings(findings)

    # Single bead creation
    bead = create_bead(finding, graph)
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import hashlib

from ..kg.schema import KnowledgeGraph, Node
from ..kg.slicer import GraphSlicer, slice_graph_for_finding
from ..kg.property_sets import VulnerabilityCategory, get_category_from_pattern_id
from .schema import (
    VulnerabilityBead,
    PatternContext,
    InvestigationGuide,
    TestContext,
)
from .types import (
    CodeSnippet,
    ExploitReference,
    Severity,
    BeadStatus,
    InvestigationStep,
)
from .templates.loader import load_template
from .exploits.loader import find_exploits_by_pattern, find_exploits_by_class


@dataclass
class BeadCreationConfig:
    """Configuration for bead creation."""

    max_related_code: int = 5  # Max related functions to include
    include_full_contract: bool = False  # Include full contract source
    max_contract_lines: int = 500  # Skip full contract if larger
    context_lines_before: int = 5  # Lines before vulnerable code
    context_lines_after: int = 5  # Lines after vulnerable code

    # === Graph Slicing Options (Task 9.D) ===
    include_graph_context: bool = True  # Include category-sliced graph context
    graph_slicing_strict: bool = False  # Only required properties (not optional)
    include_core_properties: bool = True  # Always include core properties

    # === Tool Integration Options (Phase 5.1) ===
    include_tool_context: bool = True  # Include tool metadata in beads
    merge_tool_findings: bool = True  # Merge tool findings with pattern matches
    tool_confidence_weight: float = 0.3  # How much tool confidence affects bead


class BeadCreator:
    """Creates VulnerabilityBeads from pattern match findings.

    This is the core integration between VKG's pattern engine and the
    beads system. It extracts all necessary context to create a
    self-contained investigation package.

    Example:
        from alphaswarm_sol.beads.creator import BeadCreator

        creator = BeadCreator(graph)
        findings = pattern_engine.run(graph, patterns)
        beads = creator.create_beads_from_findings(findings)

        for bead in beads:
            print(bead.get_llm_prompt())
    """

    def __init__(
        self, graph: KnowledgeGraph, config: Optional[BeadCreationConfig] = None
    ):
        """Initialize bead creator.

        Args:
            graph: Knowledge graph with code analysis results
            config: Optional configuration for bead creation
        """
        self.graph = graph
        self.config = config or BeadCreationConfig()
        self._bead_counter = 0

        # Initialize GraphSlicer for category-aware context (Task 9.D)
        self._slicer = GraphSlicer(
            include_core=self.config.include_core_properties,
            strict_mode=self.config.graph_slicing_strict,
        )

    def create_bead(self, finding: Dict[str, Any]) -> VulnerabilityBead:
        """Create a bead from a pattern engine finding.

        Args:
            finding: Dict from pattern_engine.run() containing:
                - pattern_id: Pattern identifier
                - pattern_name: Human-readable pattern name
                - severity: Severity level
                - node_id: ID of matched node
                - node_label: Label of matched node
                - node_type: Type of matched node
                - lens: Vulnerability lens categories

        Returns:
            Complete VulnerabilityBead ready for investigation
        """
        # Generate unique ID
        bead_id = self._generate_bead_id(finding)

        # Get the matched node
        node = self.graph.nodes.get(finding.get("node_id", ""))
        if node is None:
            raise ValueError(f"Node not found: {finding.get('node_id')}")

        # Extract code context
        vulnerable_code = self._extract_code_snippet(node, finding)
        related_code = self._extract_related_code(node)
        full_contract = self._get_full_contract(node)
        inheritance = self._get_inheritance_chain(node)

        # Build pattern context
        pattern_context = self._build_pattern_context(finding)

        # Determine vulnerability class from lens or pattern
        vuln_class = self._determine_vulnerability_class(finding)

        # Load investigation template
        investigation_guide = load_template(vuln_class)
        if investigation_guide is None:
            investigation_guide = self._fallback_investigation_guide()

        # Build test context
        test_context = self._build_test_context(finding, node, vuln_class)

        # Find similar exploits
        exploits = self._find_similar_exploits(finding, vuln_class)

        # Extract category-sliced graph context (Task 9.D)
        graph_context = None
        graph_context_category = ""
        if self.config.include_graph_context:
            graph_context, graph_context_category = self._extract_graph_context(
                finding, vuln_class
            )

        # Create the bead
        return VulnerabilityBead(
            id=bead_id,
            vulnerability_class=vuln_class,
            pattern_id=finding.get("pattern_id", "unknown"),
            function_id=finding.get("node_id", ""),
            severity=self._determine_severity(finding),
            confidence=self._determine_confidence(finding),
            vulnerable_code=vulnerable_code,
            related_code=related_code,
            full_contract=full_contract,
            inheritance_chain=inheritance,
            pattern_context=pattern_context,
            investigation_guide=investigation_guide,
            test_context=test_context,
            similar_exploits=exploits,
            fix_recommendations=self._get_fix_recommendations(vuln_class),
            status=BeadStatus.PENDING,
            graph_context=graph_context,
            graph_context_category=graph_context_category,
            full_graph_available=True,  # Full graph can always be requested
        )

    def create_beads_from_findings(
        self, findings: List[Dict[str, Any]]
    ) -> List[VulnerabilityBead]:
        """Create beads from multiple pattern findings.

        Args:
            findings: List of finding dicts from pattern_engine.run()

        Returns:
            List of VulnerabilityBeads, one per finding

        Example:
            findings = pattern_engine.run(graph, patterns)
            beads = creator.create_beads_from_findings(findings)
        """
        beads = []
        for finding in findings:
            try:
                bead = self.create_bead(finding)
                beads.append(bead)
            except Exception as e:
                # Log error but continue with other beads
                # TODO: Add proper logging
                import sys

                print(f"Error creating bead for {finding}: {e}", file=sys.stderr)
        return beads

    # === Private methods ===

    def _extract_graph_context(
        self, finding: Dict[str, Any], vuln_class: str
    ) -> tuple[Optional[Dict[str, Any]], str]:
        """Extract category-sliced graph context for the finding (Task 9.D).

        Uses GraphSlicer to extract only category-relevant properties,
        reducing token usage while preserving detection-relevant information.

        Args:
            finding: The finding dict
            vuln_class: Vulnerability class (reentrancy, access_control, etc.)

        Returns:
            Tuple of (graph_context_dict, category_name)
        """
        try:
            # Map vulnerability class to category
            category_mapping = {
                "reentrancy": VulnerabilityCategory.REENTRANCY,
                "access_control": VulnerabilityCategory.ACCESS_CONTROL,
                "oracle": VulnerabilityCategory.ORACLE,
                "dos": VulnerabilityCategory.DOS,
                "mev": VulnerabilityCategory.MEV,
                "token": VulnerabilityCategory.TOKEN,
                "upgrade": VulnerabilityCategory.UPGRADE,
                "crypto": VulnerabilityCategory.CRYPTO,
            }

            category = category_mapping.get(vuln_class, VulnerabilityCategory.GENERAL)

            # Slice the graph for this category
            sliced = self._slicer.slice_for_category(self.graph, category)

            # Return as dict for JSON serialization
            return sliced.to_dict(), category.value

        except Exception as e:
            # If slicing fails, return None (bead still works without it)
            import sys
            print(f"Warning: Graph slicing failed: {e}", file=sys.stderr)
            return None, ""

    def _generate_bead_id(self, finding: Dict[str, Any]) -> str:
        """Generate unique bead ID."""
        self._bead_counter += 1
        # Include hash of finding for uniqueness across runs
        pattern_id = finding.get("pattern_id", "unknown")
        node_id = finding.get("node_id", "unknown")
        match_hash = hashlib.md5(f"{pattern_id}:{node_id}".encode()).hexdigest()[:6]
        return f"VKG-{self._bead_counter:04d}-{match_hash}"

    def _extract_code_snippet(
        self, node: Node, finding: Dict[str, Any]
    ) -> CodeSnippet:
        """Extract the vulnerable code snippet from the node."""
        props = node.properties

        # Get source code from node properties or evidence
        source = props.get("source_code", "")
        if not source and node.evidence:
            source = f"// Source at {node.evidence[0].file}:{node.evidence[0].line_start}"

        # Extract location info
        file_path = ""
        start_line = 0
        end_line = 0

        if node.evidence:
            file_path = node.evidence[0].file or ""
            start_line = node.evidence[0].line_start or 0
            end_line = node.evidence[0].line_end or start_line

        # Extract function/contract names from properties or label
        function_name = props.get("name", node.label)
        contract_name = props.get("contract_name", "")

        # Try to parse from label if not in properties
        if not contract_name and "." in node.label:
            parts = node.label.split(".")
            if len(parts) >= 2:
                contract_name = parts[0]
                function_name = parts[1]

        return CodeSnippet(
            source=source or f"// Code for {node.label}",
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            function_name=function_name,
            contract_name=contract_name,
        )

    def _extract_related_code(self, node: Node) -> List[CodeSnippet]:
        """Extract related code (called functions, modifiers)."""
        related = []
        props = node.properties

        # Get called functions from properties
        calls = props.get("internal_calls", [])
        if isinstance(calls, list):
            for call_id in calls[: self.config.max_related_code]:
                called_node = self.graph.nodes.get(call_id)
                if called_node:
                    snippet = self._node_to_snippet(called_node)
                    if snippet:
                        related.append(snippet)

        # Get modifiers from properties
        modifiers = props.get("modifiers", [])
        if isinstance(modifiers, list):
            remaining_slots = self.config.max_related_code - len(related)
            for mod_name in modifiers[:remaining_slots]:
                # Try to find modifier node
                mod_id = f"modifier_{mod_name}"
                mod_node = self.graph.nodes.get(mod_id)
                if mod_node:
                    snippet = self._node_to_snippet(mod_node)
                    if snippet:
                        related.append(snippet)

        return related

    def _node_to_snippet(self, node: Node) -> Optional[CodeSnippet]:
        """Convert a node to a code snippet."""
        props = node.properties

        file_path = ""
        start_line = 0
        end_line = 0

        if node.evidence:
            file_path = node.evidence[0].file or ""
            start_line = node.evidence[0].line_start or 0
            end_line = node.evidence[0].line_end or start_line

        source = props.get("source_code", "")

        return CodeSnippet(
            source=source or f"// Code for {node.label}",
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            function_name=props.get("name", node.label),
            contract_name=props.get("contract_name", ""),
        )

    def _get_full_contract(self, node: Node) -> Optional[str]:
        """Get full contract source if configured and small enough."""
        if not self.config.include_full_contract:
            return None

        # Find contract node
        contract_name = node.properties.get("contract_name", "")
        if not contract_name:
            return None

        for n in self.graph.nodes.values():
            if n.type == "Contract" and n.label == contract_name:
                source = n.properties.get("source_code", "")
                if source:
                    # Check size
                    line_count = source.count("\n") + 1
                    if line_count <= self.config.max_contract_lines:
                        return source
                break

        return None

    def _get_inheritance_chain(self, node: Node) -> List[str]:
        """Get list of parent contracts."""
        contract_name = node.properties.get("contract_name", "")
        if not contract_name:
            return []

        # Find contract node
        for n in self.graph.nodes.values():
            if n.type == "Contract" and n.label == contract_name:
                inheritance = n.properties.get("inheritance", [])
                if isinstance(inheritance, list):
                    return inheritance
                break

        return []

    def _build_pattern_context(self, finding: Dict[str, Any]) -> PatternContext:
        """Build pattern context from finding."""
        # Extract matched properties from explain if available
        explain = finding.get("explain", {})
        matched_properties = []

        if isinstance(explain, dict):
            if "all_conditions" in explain:
                matched_properties = list(explain.get("all_conditions", {}).keys())
            elif "matched" in explain:
                matched_properties = explain.get("matched", [])

        # Build why_flagged explanation
        why_flagged = self._build_why_flagged(finding)

        # Extract evidence lines
        evidence_lines = []
        if isinstance(explain, dict) and "evidence_lines" in explain:
            evidence_lines = explain["evidence_lines"]

        return PatternContext(
            pattern_name=finding.get("pattern_name", finding.get("pattern_id", "")),
            pattern_description=finding.get("description", ""),
            why_flagged=why_flagged,
            matched_properties=matched_properties,
            evidence_lines=evidence_lines,
        )

    def _build_why_flagged(self, finding: Dict[str, Any]) -> str:
        """Build human-readable explanation of why code was flagged."""
        parts = []

        pattern_name = finding.get("pattern_name", finding.get("pattern_id", ""))
        if pattern_name:
            parts.append(f"Matched pattern: {pattern_name}")

        severity = finding.get("severity", "")
        if severity:
            parts.append(f"Severity: {severity}")

        lens = finding.get("lens", [])
        if lens:
            lens_str = ", ".join(lens) if isinstance(lens, list) else str(lens)
            parts.append(f"Lens: {lens_str}")

        return " | ".join(parts) if parts else "Pattern matched"

    def _determine_vulnerability_class(self, finding: Dict[str, Any]) -> str:
        """Determine vulnerability class from finding."""
        # First try from lens
        lens = finding.get("lens", [])
        if isinstance(lens, list) and lens:
            # Map lens names to our standard classes
            lens_mapping = {
                "reentrancy": "reentrancy",
                "access-control": "access_control",
                "access_control": "access_control",
                "accesscontrol": "access_control",
                "authority": "access_control",
                "oracle": "oracle",
                "dos": "dos",
                "denial-of-service": "dos",
                "mev": "mev",
                "token": "token",
                "upgrade": "upgrade",
                "proxy": "upgrade",
                "value-movement": "reentrancy",  # Often reentrancy related
                "crypto": "access_control",  # Often signature issues
            }
            for l in lens:
                l_lower = l.lower().replace(" ", "-")
                if l_lower in lens_mapping:
                    return lens_mapping[l_lower]

        # Fall back to pattern ID analysis
        pattern_id = finding.get("pattern_id", "").lower()

        class_mappings = {
            "reentrancy": ["reentrancy", "state-write-after", "vm-001", "vm-002"],
            "access_control": ["access", "auth", "owner", "permission", "role"],
            "oracle": ["oracle", "price", "staleness", "chainlink", "twap"],
            "dos": ["dos", "unbounded", "loop", "gas", "griefing"],
            "mev": ["mev", "slippage", "deadline", "sandwich", "frontrun"],
            "token": ["token", "erc20", "transfer", "approval", "fee-on"],
            "upgrade": ["upgrade", "proxy", "initializer", "storage", "delegatecall"],
        }

        for vuln_class, keywords in class_mappings.items():
            if any(kw in pattern_id for kw in keywords):
                return vuln_class

        return "unknown"

    def _determine_severity(self, finding: Dict[str, Any]) -> Severity:
        """Determine severity from finding."""
        severity_str = finding.get("severity", "medium").lower()

        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
            "informational": Severity.INFO,
        }

        return severity_map.get(severity_str, Severity.MEDIUM)

    def _determine_confidence(self, finding: Dict[str, Any]) -> float:
        """Determine confidence from finding."""
        # Check for explicit confidence
        if "confidence" in finding:
            return float(finding["confidence"])

        # Infer from tier matching
        explain = finding.get("explain", {})
        if isinstance(explain, dict):
            # If tier_b matched, higher confidence
            if explain.get("tier_b_matched"):
                return 0.95

            # If all conditions matched, moderate confidence
            all_cond = explain.get("all_conditions", {})
            if all_cond and all(all_cond.values()):
                return 0.85

        # Default moderate confidence
        return 0.75

    def _build_test_context(
        self, finding: Dict[str, Any], node: Node, vuln_class: str
    ) -> TestContext:
        """Build test context for exploit verification."""
        # Extract names for scaffold
        contract_name = node.properties.get("contract_name", "Target")
        function_name = node.properties.get("name", node.label)

        # Clean up names
        if "." in function_name:
            function_name = function_name.split(".")[-1]

        scaffold = self._generate_test_scaffold(contract_name, function_name, vuln_class)
        scenario = self._generate_attack_scenario(vuln_class)

        return TestContext(
            scaffold_code=scaffold,
            attack_scenario=scenario,
            setup_requirements=self._get_setup_requirements(vuln_class),
            expected_outcome=self._get_expected_outcome(vuln_class),
        )

    def _generate_test_scaffold(
        self, contract_name: str, function_name: str, vuln_class: str
    ) -> str:
        """Generate Foundry test scaffold."""
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "../src/{contract_name}.sol";

contract {contract_name}ExploitTest is Test {{
    {contract_name} target;
    address attacker = address(0xBAD);

    function setUp() public {{
        target = new {contract_name}();
        // TODO: Setup initial state
        // - Fund the contract if needed
        // - Set up attacker account
        // - Configure any dependencies
    }}

    function test_exploit_{function_name}() public {{
        vm.startPrank(attacker);

        // TODO: Implement exploit for {vuln_class}
        // 1. Setup preconditions
        // 2. Execute attack
        // 3. Verify exploitation

        vm.stopPrank();

        // TODO: Add assertions to verify exploit success
        // assertGt(attacker.balance, initialBalance);
    }}
}}
"""

    def _generate_attack_scenario(self, vuln_class: str) -> str:
        """Generate attack scenario description."""
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
            "dos": """
1. Attacker identifies loop or batch operation
2. Attacker grows array or creates many entries
3. Legitimate users try to call affected function
4. Transaction reverts due to out-of-gas
5. Protocol functionality is blocked
""",
            "mev": """
1. User submits swap or sensitive transaction
2. MEV bot sees transaction in mempool
3. Bot front-runs: executes same direction trade first
4. User transaction executes at worse price
5. Bot back-runs: reverses position for profit
""",
            "token": """
1. Attacker identifies protocol's token assumptions
2. Attacker uses non-standard token (fee-on-transfer, etc.)
3. Protocol's accounting becomes incorrect
4. Attacker exploits discrepancy to profit
""",
            "upgrade": """
1. Attacker identifies unprotected upgrade or initialize
2. Attacker calls upgrade with malicious implementation
   OR attacker calls initialize to take ownership
3. Attacker gains control of protocol
4. Attacker drains funds or disrupts service
""",
        }
        return scenarios.get(vuln_class, "TODO: Document specific attack scenario")

    def _get_setup_requirements(self, vuln_class: str) -> List[str]:
        """Get setup requirements for testing."""
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
            "dos": [
                "Ability to grow array/iteration count",
                "Gas measurement tools",
                "Target function with unbounded loop",
            ],
            "mev": [
                "DEX with liquidity for target pair",
                "Victim transaction to sandwich",
                "MEV infrastructure (block builder access)",
            ],
            "token": [
                "Non-standard token (fee-on-transfer, rebasing)",
                "Target protocol accepting arbitrary tokens",
                "Initial setup with normal tokens for comparison",
            ],
            "upgrade": [
                "Proxy contract deployment",
                "Malicious implementation contract",
                "Access to upgrade or initialize function",
            ],
        }
        return requirements.get(vuln_class, ["TODO: Define requirements"])

    def _get_expected_outcome(self, vuln_class: str) -> str:
        """Get expected outcome of successful exploit."""
        outcomes = {
            "reentrancy": "Attacker extracts more funds than their fair share",
            "access_control": "Unauthorized privileged operation succeeds",
            "oracle": "Attacker profits from manipulated price valuation",
            "dos": "Function becomes unusable due to gas exhaustion",
            "mev": "User receives significantly worse execution price",
            "token": "Accounting discrepancy allows attacker to profit",
            "upgrade": "Attacker gains control or ownership of contract",
        }
        return outcomes.get(vuln_class, "Exploit succeeds with measurable impact")

    def _find_similar_exploits(
        self, finding: Dict[str, Any], vuln_class: str
    ) -> List[ExploitReference]:
        """Find similar real-world exploits."""
        # Try by pattern ID first
        pattern_id = finding.get("pattern_id", "")
        exploits = find_exploits_by_pattern(pattern_id)
        if exploits:
            return exploits[:3]  # Max 3

        # Fall back to class
        exploits = find_exploits_by_class(vuln_class)
        return exploits[:3]

    def _get_fix_recommendations(self, vuln_class: str) -> List[str]:
        """Get fix recommendations by vulnerability class."""
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
                "Add gas limits for external calls in loops",
            ],
            "mev": [
                "Add user-controlled slippage parameter",
                "Require deadline parameter for time-sensitive operations",
                "Consider private transaction submission (Flashbots)",
                "Implement commit-reveal for sensitive operations",
            ],
            "token": [
                "Use SafeERC20 for all token transfers",
                "Check actual balance changes, not transfer amounts",
                "Whitelist supported tokens or validate compatibility",
                "Handle fee-on-transfer and rebasing tokens explicitly",
            ],
            "upgrade": [
                "Add initializer protection (initializer modifier)",
                "Use reinitializer for version-controlled upgrades",
                "Implement timelock for upgrade operations",
                "Add storage gaps for future variables",
                "Never use selfdestruct in implementation contracts",
            ],
        }
        return recommendations.get(vuln_class, ["Review and fix the vulnerability"])

    def _fallback_investigation_guide(self) -> InvestigationGuide:
        """Fallback investigation guide when template not found."""
        return InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Review the flagged code",
                    look_for="The specific vulnerability pattern identified",
                    evidence_needed="Code evidence confirming the issue",
                ),
                InvestigationStep(
                    step_number=2,
                    action="Check for existing protections",
                    look_for="Guards, modifiers, or checks that prevent exploitation",
                    evidence_needed="Protection mechanisms in place",
                ),
                InvestigationStep(
                    step_number=3,
                    action="Assess exploitability",
                    look_for="Whether an attacker can actually exploit this",
                    evidence_needed="Concrete attack scenario",
                ),
            ],
            questions_to_answer=[
                "Is the flagged pattern actually exploitable?",
                "Are there protections not detected by the pattern?",
                "What is the potential impact if exploited?",
            ],
            common_false_positives=[
                "Protection exists but not detected by pattern",
                "Pattern matches safe code variant",
                "Context makes exploitation impractical",
            ],
            key_indicators=["Pattern-specific indicators"],
            safe_patterns=["Pattern-specific safe alternatives"],
        )

    # === Tool Finding Integration Methods (Phase 5.1) ===

    def create_bead_from_tool_finding(
        self,
        finding: "VKGFinding",
        tool_sources: Optional[List[str]] = None,
        project_path: Optional["Path"] = None,
    ) -> VulnerabilityBead:
        """Create bead from tool finding, optionally enriched with VKG context.

        If graph is available, enriches bead with:
        - Related code from call graph
        - Graph context for the vulnerability category
        - Similar exploits from VulnDocs

        Args:
            finding: VKGFinding from tool adapter
            tool_sources: List of tools that found this issue
            project_path: Path to project (for code extraction)

        Returns:
            VulnerabilityBead ready for verification
        """
        # Use ToolFindingToBead for base conversion
        from .from_tools import ToolFindingToBead

        # Determine project path
        if project_path is None:
            # Try to infer from graph evidence
            project_path = self._infer_project_path()

        converter = ToolFindingToBead(project_path, self.graph)
        bead = converter.create_bead(finding, tool_sources)

        # Enrich with VKG context if graph available and configured
        if self.graph and self.config.include_graph_context:
            bead = self._enrich_with_graph_context(bead, finding)

        return bead

    def _enrich_with_graph_context(
        self,
        bead: VulnerabilityBead,
        finding: "VKGFinding",
    ) -> VulnerabilityBead:
        """Enrich tool-generated bead with VKG context.

        Adds:
        - Related code from graph nodes
        - Category-sliced graph context
        - Similar exploits from VulnDocs

        Args:
            bead: Tool-generated bead to enrich
            finding: Original VKGFinding

        Returns:
            Enriched bead (mutates original)
        """
        # Find matching node in graph
        node = self._find_node_for_finding(finding)

        if node:
            # Add related code from graph
            related = self._extract_related_code(node)
            if related:
                bead.related_code = related

            # Add graph context
            if self.config.include_graph_context:
                graph_context, category = self._extract_graph_context(
                    {"node_id": node.id},
                    bead.vulnerability_class
                )
                bead.graph_context = graph_context
                bead.graph_context_category = category

            # Add similar exploits from VulnDocs
            similar = self._find_similar_exploits(
                {"pattern_id": finding.rule_id},
                bead.vulnerability_class
            )
            if similar:
                bead.similar_exploits = similar

        return bead

    def _find_node_for_finding(self, finding: "VKGFinding") -> Optional[Node]:
        """Find graph node matching the tool finding location.

        Matches by:
        1. Function name (exact match)
        2. File and line proximity (within 5 lines)

        Args:
            finding: VKGFinding to find node for

        Returns:
            Matching Node or None
        """
        if not self.graph:
            return None

        # Search by function name and file
        for node in self.graph.nodes.values():
            if node.type != "Function":
                continue

            props = node.properties

            # Match by function name
            if finding.function and props.get("name") == finding.function:
                return node

            # Match by file and line proximity
            if node.evidence:
                for ev in node.evidence:
                    if (ev.file and finding.file in ev.file and
                        ev.line_start and abs(ev.line_start - finding.line) < 5):
                        return node

        return None

    def _infer_project_path(self) -> "Path":
        """Infer project path from graph evidence.

        Looks at file paths in graph evidence to determine
        common project root.

        Returns:
            Inferred project path or current directory
        """
        from pathlib import Path

        # Try to find common path from graph evidence
        if self.graph:
            paths = []
            for node in self.graph.nodes.values():
                if node.evidence:
                    for ev in node.evidence:
                        if ev.file:
                            paths.append(Path(ev.file))

            if paths:
                # Find common ancestor
                try:
                    common = Path(paths[0]).parent
                    for p in paths[1:]:
                        while not str(p).startswith(str(common)):
                            common = common.parent
                            if common == common.parent:  # Reached root
                                break
                    return common
                except Exception:
                    pass

        # Default to current directory
        return Path(".")


# Type hints for optional imports
try:
    from ..tools.adapters.sarif import VKGFinding
    from pathlib import Path
except ImportError:
    VKGFinding = Any  # type: ignore
    Path = Any  # type: ignore


# Convenience functions


def create_bead(
    finding: Dict[str, Any],
    graph: KnowledgeGraph,
    config: Optional[BeadCreationConfig] = None,
) -> VulnerabilityBead:
    """Convenience function to create a single bead.

    Args:
        finding: Finding dict from pattern engine
        graph: Knowledge graph
        config: Optional creation config

    Returns:
        VulnerabilityBead ready for investigation
    """
    creator = BeadCreator(graph, config)
    return creator.create_bead(finding)


def create_beads(
    findings: List[Dict[str, Any]],
    graph: KnowledgeGraph,
    config: Optional[BeadCreationConfig] = None,
) -> List[VulnerabilityBead]:
    """Convenience function to create beads from findings.

    Args:
        findings: List of finding dicts from pattern engine
        graph: Knowledge graph
        config: Optional creation config

    Returns:
        List of VulnerabilityBeads
    """
    creator = BeadCreator(graph, config)
    return creator.create_beads_from_findings(findings)


# Export for module
__all__ = [
    "BeadCreator",
    "BeadCreationConfig",
    "create_bead",
    "create_beads",
]
