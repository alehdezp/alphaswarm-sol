"""Phase 17: Semantic Scaffolding.

This module provides functionality for generating token-efficient
semantic scaffolds from subgraphs for LLM consumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node


class ScaffoldFormat(str, Enum):
    """Output format for scaffold."""
    COMPACT = "compact"        # Minimal tokens
    STRUCTURED = "structured"  # Readable structure
    YAML_LIKE = "yaml_like"    # YAML-inspired format


@dataclass
class FunctionSummary:
    """Compressed summary of a function for scaffolding.

    Attributes:
        name: Function name
        role: Semantic role (e.g., "Guardian", "CriticalState")
        visibility: public/external/internal/private
        guards: Access control guards
        operations: Key semantic operations
        mutations: State variables modified
        externals: External calls made
        risk_factors: Primary risk factors
        signature: Behavioral signature
    """
    name: str
    role: str = ""
    visibility: str = ""
    guards: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    mutations: List[str] = field(default_factory=list)
    externals: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    signature: str = ""

    def to_compact(self) -> str:
        """Generate compact representation (~10-20 tokens)."""
        parts = [f"fn:{self.name}"]
        if self.role:
            parts.append(f"role:{self.role}")
        if self.guards:
            parts.append(f"guards:{','.join(self.guards)}")
        if self.operations:
            parts.append(f"ops:{','.join(self.operations[:3])}")
        if self.risk_factors:
            parts.append(f"risk:{','.join(self.risk_factors[:2])}")
        return " | ".join(parts)

    def to_structured(self) -> str:
        """Generate structured representation."""
        lines = [f"FUNCTION: {self.name}"]
        if self.role:
            lines.append(f"├── Role: {self.role}")
        if self.guards:
            lines.append(f"├── Guards: {', '.join(self.guards)}")
        if self.operations:
            lines.append(f"├── Ops: {', '.join(self.operations)}")
        if self.mutations:
            lines.append(f"├── Mutates: {', '.join(self.mutations)}")
        if self.externals:
            lines.append(f"├── Externals: {', '.join(self.externals)}")
        if self.risk_factors:
            lines.append(f"└── Risks: {', '.join(self.risk_factors)}")
        return "\n".join(lines)


@dataclass
class RiskMatrixEntry:
    """Entry in the risk matrix."""
    category: str
    severity: int  # 1-10
    functions: List[str]
    evidence: List[str]


@dataclass
class SemanticScaffold:
    """Token-optimized semantic scaffold for LLM consumption.

    Attributes:
        contract_name: Name of the contract
        functions: Summarized functions
        risk_matrix: Risk categories and severity
        attack_surface: Key attack surface points
        dependencies: Critical external dependencies
        token_estimate: Estimated token count
    """
    contract_name: str = ""
    functions: List[FunctionSummary] = field(default_factory=list)
    risk_matrix: List[RiskMatrixEntry] = field(default_factory=list)
    attack_surface: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    token_estimate: int = 0

    def to_string(self, format: ScaffoldFormat = ScaffoldFormat.COMPACT) -> str:
        """Generate scaffold string.

        Args:
            format: Output format

        Returns:
            Scaffold string
        """
        if format == ScaffoldFormat.COMPACT:
            return self._to_compact()
        elif format == ScaffoldFormat.STRUCTURED:
            return self._to_structured()
        else:
            return self._to_yaml_like()

    def _to_compact(self) -> str:
        """Generate compact scaffold (minimal tokens)."""
        sections = []

        # Contract header
        sections.append(f"CONTRACT: {self.contract_name}")

        # Functions (compact)
        for func in self.functions:
            sections.append(func.to_compact())

        # Risk summary (single line)
        if self.risk_matrix:
            risks = [f"{r.category}:{r.severity}" for r in self.risk_matrix[:3]]
            sections.append(f"RISKS: {' '.join(risks)}")

        # Attack surface (single line)
        if self.attack_surface:
            sections.append(f"SURFACE: {', '.join(self.attack_surface[:3])}")

        return "\n".join(sections)

    def _to_structured(self) -> str:
        """Generate structured scaffold."""
        sections = []

        # Contract header
        sections.append(f"═══ {self.contract_name} ═══")
        sections.append("")

        # Functions
        for func in self.functions:
            sections.append(func.to_structured())
            sections.append("")

        # Risk matrix
        if self.risk_matrix:
            sections.append("RISK MATRIX:")
            for entry in self.risk_matrix:
                sections.append(f"  [{entry.severity}/10] {entry.category}: {', '.join(entry.functions)}")
            sections.append("")

        # Attack surface
        if self.attack_surface:
            sections.append("ATTACK SURFACE:")
            for surface in self.attack_surface:
                sections.append(f"  • {surface}")

        return "\n".join(sections)

    def _to_yaml_like(self) -> str:
        """Generate YAML-like scaffold."""
        lines = []
        lines.append(f"contract: {self.contract_name}")
        lines.append("functions:")
        for func in self.functions:
            lines.append(f"  - name: {func.name}")
            if func.role:
                lines.append(f"    role: {func.role}")
            if func.guards:
                lines.append(f"    guards: [{', '.join(func.guards)}]")
            if func.operations:
                lines.append(f"    ops: [{', '.join(func.operations)}]")
            if func.risk_factors:
                lines.append(f"    risks: [{', '.join(func.risk_factors)}]")

        if self.risk_matrix:
            lines.append("risks:")
            for entry in self.risk_matrix:
                lines.append(f"  - category: {entry.category}")
                lines.append(f"    severity: {entry.severity}")

        return "\n".join(lines)


class ScaffoldGenerator:
    """Generates semantic scaffolds from knowledge graphs.

    Produces token-efficient representations for LLM consumption.
    """

    # Risk factor keywords
    RISK_KEYWORDS = {
        "reentrancy": ["state_write_after_external_call", "has_reentrancy_guard"],
        "access": ["has_access_gate", "writes_privileged_state"],
        "oracle": ["reads_oracle_price", "has_staleness_check"],
        "dos": ["has_unbounded_loop", "external_calls_in_loop"],
        "crypto": ["uses_ecrecover", "checks_zero_address"],
    }

    def __init__(self, graph: KnowledgeGraph):
        """Initialize generator with knowledge graph.

        Args:
            graph: Knowledge graph to generate scaffold from
        """
        self.graph = graph

    def generate(
        self,
        contract_id: Optional[str] = None,
        max_functions: int = 10,
        format: ScaffoldFormat = ScaffoldFormat.COMPACT,
    ) -> SemanticScaffold:
        """Generate semantic scaffold.

        Args:
            contract_id: Optional contract to focus on
            max_functions: Maximum functions to include
            format: Output format

        Returns:
            SemanticScaffold
        """
        # Get contract name
        contract_name = "Unknown"
        contract_label = None
        if contract_id:
            contract_node = self.graph.nodes.get(contract_id)
            if contract_node:
                contract_name = contract_node.label
                contract_label = contract_node.label

        # Extract function summaries
        functions = self._extract_functions(contract_label, max_functions)

        # Build risk matrix
        risk_matrix = self._build_risk_matrix(functions)

        # Identify attack surface
        attack_surface = self._identify_attack_surface(functions)

        # Extract dependencies
        dependencies = self._extract_dependencies(functions)

        scaffold = SemanticScaffold(
            contract_name=contract_name,
            functions=functions,
            risk_matrix=risk_matrix,
            attack_surface=attack_surface,
            dependencies=dependencies,
        )

        # Estimate tokens
        scaffold.token_estimate = self._estimate_tokens(
            scaffold.to_string(format)
        )

        return scaffold

    def _extract_functions(
        self,
        contract_label: Optional[str],
        max_functions: int,
    ) -> List[FunctionSummary]:
        """Extract function summaries from graph."""
        functions: List[FunctionSummary] = []

        for node in self.graph.nodes.values():
            if node.type != "Function":
                continue

            # Filter by contract if specified
            if contract_label:
                if node.properties.get("contract_name") != contract_label:
                    continue

            summary = self._summarize_function(node)
            functions.append(summary)

            if len(functions) >= max_functions:
                break

        # Sort by risk (functions with more risk factors first)
        functions.sort(key=lambda f: len(f.risk_factors), reverse=True)

        return functions

    def _summarize_function(self, node: Node) -> FunctionSummary:
        """Summarize a function node."""
        props = node.properties

        # Extract guards
        guards: List[str] = []
        if props.get("has_access_gate"):
            guards.append("access")
        if props.get("has_reentrancy_guard"):
            guards.append("reentrancy")
        modifiers = props.get("modifiers", []) or []
        for mod in modifiers[:2]:
            if mod not in guards:
                guards.append(mod)

        # Extract operations
        operations = (props.get("semantic_ops", []) or [])[:5]

        # Extract mutations
        mutations: List[str] = []
        if props.get("writes_state"):
            mutations.append("state")
        if props.get("writes_privileged_state"):
            mutations.append("privileged")

        # Extract externals
        externals: List[str] = []
        if props.get("calls_external"):
            externals.append("external_call")
        if props.get("reads_oracle_price"):
            externals.append("oracle")
        if props.get("uses_erc20_transfer"):
            externals.append("token")

        # Extract risk factors
        risk_factors = self._extract_risk_factors(props)

        # Get semantic role
        role = props.get("semantic_role", "")

        # Get visibility
        visibility = props.get("visibility", "")

        # Get signature
        signature = props.get("behavioral_signature", "")

        return FunctionSummary(
            name=node.label,
            role=role,
            visibility=visibility,
            guards=guards,
            operations=operations,
            mutations=mutations,
            externals=externals,
            risk_factors=risk_factors,
            signature=signature,
        )

    def _extract_risk_factors(self, props: Dict[str, Any]) -> List[str]:
        """Extract risk factors from function properties."""
        risks: List[str] = []

        # Reentrancy
        if props.get("state_write_after_external_call"):
            if not props.get("has_reentrancy_guard"):
                risks.append("reentrancy")

        # Access control
        if props.get("writes_privileged_state"):
            if not props.get("has_access_gate"):
                risks.append("access_control")

        # Oracle
        if props.get("reads_oracle_price"):
            if not props.get("has_staleness_check"):
                risks.append("stale_price")

        # DoS
        if props.get("has_unbounded_loop"):
            risks.append("dos")
        if props.get("external_calls_in_loop"):
            risks.append("dos_external")

        # Crypto
        if props.get("uses_ecrecover"):
            if not props.get("checks_zero_address"):
                risks.append("ecrecover_zero")

        # Slippage
        if props.get("swap_like"):
            if props.get("risk_missing_slippage_parameter"):
                risks.append("slippage")

        return risks

    def _build_risk_matrix(
        self,
        functions: List[FunctionSummary],
    ) -> List[RiskMatrixEntry]:
        """Build risk matrix from functions."""
        matrix: Dict[str, RiskMatrixEntry] = {}

        for func in functions:
            for risk in func.risk_factors:
                if risk not in matrix:
                    matrix[risk] = RiskMatrixEntry(
                        category=risk,
                        severity=self._severity_for_risk(risk),
                        functions=[],
                        evidence=[],
                    )
                matrix[risk].functions.append(func.name)

        # Sort by severity
        entries = list(matrix.values())
        entries.sort(key=lambda e: e.severity, reverse=True)

        return entries

    def _severity_for_risk(self, risk: str) -> int:
        """Get severity score for a risk category."""
        severity_map = {
            "reentrancy": 9,
            "access_control": 8,
            "stale_price": 7,
            "ecrecover_zero": 7,
            "dos": 6,
            "dos_external": 7,
            "slippage": 6,
        }
        return severity_map.get(risk, 5)

    def _identify_attack_surface(
        self,
        functions: List[FunctionSummary],
    ) -> List[str]:
        """Identify key attack surface points."""
        surface: List[str] = []

        for func in functions:
            if func.visibility in ("public", "external"):
                if func.risk_factors:
                    surface.append(f"{func.name}: {', '.join(func.risk_factors)}")

        return surface[:5]  # Limit to top 5

    def _extract_dependencies(
        self,
        functions: List[FunctionSummary],
    ) -> List[str]:
        """Extract external dependencies."""
        deps: Set[str] = set()

        for func in functions:
            for ext in func.externals:
                deps.add(ext)

        return list(deps)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses rough approximation of ~4 chars per token.
        """
        return len(text) // 4


def generate_semantic_scaffold(
    graph: KnowledgeGraph,
    contract_id: Optional[str] = None,
    format: ScaffoldFormat = ScaffoldFormat.COMPACT,
) -> str:
    """Generate a semantic scaffold from a knowledge graph.

    Convenience function for quick scaffold generation.

    Args:
        graph: Knowledge graph to analyze
        contract_id: Optional contract to focus on
        format: Output format

    Returns:
        Scaffold string
    """
    generator = ScaffoldGenerator(graph)
    scaffold = generator.generate(contract_id, format=format)
    return scaffold.to_string(format)


def compress_for_llm(
    scaffold: SemanticScaffold,
    max_tokens: int = 100,
) -> str:
    """Compress scaffold to fit within token limit.

    Args:
        scaffold: Scaffold to compress
        max_tokens: Maximum tokens allowed

    Returns:
        Compressed scaffold string
    """
    # Start with compact format
    text = scaffold.to_string(ScaffoldFormat.COMPACT)

    # If within limit, return as-is
    if scaffold.token_estimate <= max_tokens:
        return text

    # Further compress by reducing functions
    lines = text.split("\n")
    compressed = []

    for line in lines:
        compressed.append(line)
        current_tokens = len("\n".join(compressed)) // 4
        if current_tokens >= max_tokens:
            compressed.append("... (truncated)")
            break

    return "\n".join(compressed)


__all__ = [
    "ScaffoldFormat",
    "FunctionSummary",
    "RiskMatrixEntry",
    "SemanticScaffold",
    "ScaffoldGenerator",
    "generate_semantic_scaffold",
    "compress_for_llm",
]
