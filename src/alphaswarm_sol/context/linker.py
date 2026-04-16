"""Context linker with causal chain support for function <-> economic context linkage.

Per 05.11-CONTEXT.md: Deterministic linker that maps functions to economic context nodes
using explicit mappings first, with semantic ops backfill (low confidence, quarantined).

Key features:
- ContextLinker: Maps functions to economic nodes with evidence-backed links
- CausalChainLink: Models exploitation chains with probability and counterfactuals
- Two-key evidence: Links require two independent evidence sources to surface
- Overlay edges: Writes causal edges into DomainKnowledgeGraph

Usage:
    from alphaswarm_sol.context.linker import ContextLinker, LinkRecord, CausalChainLink

    linker = ContextLinker()

    # Register explicit mapping from context pack
    linker.register_explicit_link(
        function_id="Vault.withdraw",
        context_node_id="flow.withdraw",
        link_type="VALUE_FLOW_THROUGH_FUNCTION",
        evidence_refs=["whitepaper-v1.2", "code:Vault:120"]
    )

    # Backfill from semantic ops (quarantined until evidence added)
    linker.backfill_from_semantic_ops(kg, dossier)

    # Get surfaced links (only those with two-key evidence)
    surfaced = linker.get_surfaced_links("Vault.withdraw")

    # Build and trace causal chains
    chain = linker.trace_causal_chain("oracle-manipulation-vuln")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from .types import (
    Confidence,
    CausalEdge,
    CausalEdgeType,
    ExpectationProvenance,
)

if TYPE_CHECKING:
    from alphaswarm_sol.knowledge.domain_kg import DomainKnowledgeGraph


class LinkSource(Enum):
    """Source of a context link.

    Per 05.11-CONTEXT.md: Links can come from explicit pack mappings,
    semantic operations, or heuristics.
    """

    PACK = "pack"  # Explicit mapping from ProtocolContextPack (authoritative)
    SEMANTIC = "semantic"  # Inferred from semantic operations (medium confidence)
    HEURISTIC = "heuristic"  # Heuristic-based (low confidence, quarantined)


class LinkType(Enum):
    """Types of context links between functions and economic nodes.

    Per 05.11-CONTEXT.md: Economic overlay edge types.
    """

    ROLE_CONTROLS_FUNCTION = "role_controls_function"
    VALUE_FLOW_THROUGH_FUNCTION = "value_flow_through_function"
    OFFCHAIN_INPUT_FEEDS_FUNCTION = "offchain_input_feeds_function"
    ASSUMPTION_AFFECTS_FUNCTION = "assumption_affects_function"
    GOVERNANCE_CAN_CHANGE_STATE = "governance_can_change_state"
    INVARIANT_ENFORCED_BY = "invariant_enforced_by"


@dataclass
class LinkRecord:
    """A link between a function and an economic context node.

    Per 05.11-CONTEXT.md: Every link must include evidence_refs and confidence.
    Links require two-key evidence to surface to agents.

    Attributes:
        function_id: Function identifier (e.g., "Vault.withdraw")
        context_node_id: Economic context node ID (e.g., "flow.withdraw")
        link_type: Type of relationship
        source: How this link was derived (pack/semantic/heuristic)
        confidence: Confidence level
        evidence_refs: Evidence supporting this link (need 2+ for surfacing)
        signals: Semantic ops/properties that justify the link
        quarantined: Whether this link is hidden from agents
        created_at: When this link was created
    """

    function_id: str
    context_node_id: str
    link_type: LinkType
    source: LinkSource
    confidence: Confidence = Confidence.INFERRED
    evidence_refs: List[str] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)
    quarantined: bool = False
    created_at: str = ""

    def __post_init__(self) -> None:
        """Initialize timestamp if not set."""
        if not self.created_at:
            from datetime import datetime

            self.created_at = datetime.utcnow().isoformat() + "Z"

    @property
    def has_two_key_evidence(self) -> bool:
        """Check if link has two independent evidence sources.

        Per 05.11-CONTEXT.md: Two-key links require:
        (a) semantic ops or code evidence, AND (b) dossier or on-chain mapping.

        Returns:
            True if link has at least 2 evidence refs
        """
        return len(self.evidence_refs) >= 2

    @property
    def can_surface(self) -> bool:
        """Check if link can be surfaced to agents.

        Returns:
            True if not quarantined and has two-key evidence
        """
        return not self.quarantined and self.has_two_key_evidence

    def add_evidence(self, evidence_ref: str) -> None:
        """Add evidence reference to this link.

        Args:
            evidence_ref: Evidence reference to add
        """
        if evidence_ref not in self.evidence_refs:
            self.evidence_refs.append(evidence_ref)

    def upgrade_confidence(self, new_confidence: Confidence) -> bool:
        """Attempt to upgrade confidence level.

        Per 05.11-CONTEXT.md: Cannot upgrade without two-key evidence.

        Args:
            new_confidence: Target confidence level

        Returns:
            True if upgrade succeeded, False if blocked
        """
        if new_confidence > self.confidence:
            if not self.has_two_key_evidence:
                return False
            self.confidence = new_confidence
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "function_id": self.function_id,
            "context_node_id": self.context_node_id,
            "link_type": self.link_type.value,
            "source": self.source.value,
            "confidence": self.confidence.value,
            "evidence_refs": self.evidence_refs,
            "signals": self.signals,
            "quarantined": self.quarantined,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LinkRecord":
        """Create LinkRecord from dictionary."""
        return cls(
            function_id=str(data.get("function_id", "")),
            context_node_id=str(data.get("context_node_id", "")),
            link_type=LinkType(data.get("link_type", "assumption_affects_function")),
            source=LinkSource(data.get("source", "heuristic")),
            confidence=Confidence.from_string(data.get("confidence", "unknown")),
            evidence_refs=list(data.get("evidence_refs", [])),
            signals=list(data.get("signals", [])),
            quarantined=bool(data.get("quarantined", False)),
            created_at=str(data.get("created_at", "")),
        )


@dataclass
class CausalChainLink:
    """A causal chain for exploitation reasoning.

    Per 05.11-CONTEXT.md: Models how vulnerabilities chain together
    to produce financial loss, with probability and counterfactuals.

    Attributes:
        chain_id: Unique identifier for this chain
        root_cause_id: Root vulnerability/condition that starts the chain
        exploit_steps: Ordered list of exploit step IDs
        financial_loss_id: Final loss outcome node ID
        probability_chain: Cumulative probability (product of step probabilities)
        counterfactual_blocks: Mitigations that would break this chain
        evidence_refs: Evidence supporting this chain
        confidence: Confidence in the chain
    """

    chain_id: str
    root_cause_id: str
    exploit_steps: List[str] = field(default_factory=list)
    financial_loss_id: str = ""
    probability_chain: float = 1.0
    counterfactual_blocks: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    confidence: Confidence = Confidence.INFERRED

    def __post_init__(self) -> None:
        """Validate probability range."""
        if not 0.0 <= self.probability_chain <= 1.0:
            raise ValueError(f"probability_chain must be 0.0-1.0, got {self.probability_chain}")

    @property
    def step_count(self) -> int:
        """Number of steps in the exploit chain."""
        return len(self.exploit_steps)

    @property
    def is_high_probability(self) -> bool:
        """Whether this chain has high cumulative probability (>= 0.5)."""
        return self.probability_chain >= 0.5

    @property
    def can_be_blocked(self) -> bool:
        """Whether this chain can be blocked by counterfactual mitigations."""
        return len(self.counterfactual_blocks) > 0

    def add_counterfactual(self, mitigation_id: str) -> None:
        """Add a counterfactual mitigation that would break this chain.

        Args:
            mitigation_id: ID of mitigation that would block the chain
        """
        if mitigation_id not in self.counterfactual_blocks:
            self.counterfactual_blocks.append(mitigation_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chain_id": self.chain_id,
            "root_cause_id": self.root_cause_id,
            "exploit_steps": self.exploit_steps,
            "financial_loss_id": self.financial_loss_id,
            "probability_chain": self.probability_chain,
            "counterfactual_blocks": self.counterfactual_blocks,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalChainLink":
        """Create CausalChainLink from dictionary."""
        return cls(
            chain_id=str(data.get("chain_id", "")),
            root_cause_id=str(data.get("root_cause_id", "")),
            exploit_steps=list(data.get("exploit_steps", [])),
            financial_loss_id=str(data.get("financial_loss_id", "")),
            probability_chain=float(data.get("probability_chain", 1.0)),
            counterfactual_blocks=list(data.get("counterfactual_blocks", [])),
            evidence_refs=list(data.get("evidence_refs", [])),
            confidence=Confidence.from_string(data.get("confidence", "inferred")),
        )


class ContextLinker:
    """Deterministic linker for function <-> economic context linkage.

    Per 05.11-CONTEXT.md: Links functions to economic context nodes using
    explicit mappings first, with semantic ops backfill for gaps.

    Key features:
    - Two-key evidence requirement for surfaced links
    - Quarantine for low-confidence heuristic links
    - Causal chain building with counterfactual analysis
    - Overlay edge injection into DomainKnowledgeGraph

    Usage:
        linker = ContextLinker()

        # Register explicit links
        linker.register_explicit_link(
            function_id="Vault.withdraw",
            context_node_id="flow.withdraw",
            link_type=LinkType.VALUE_FLOW_THROUGH_FUNCTION,
            evidence_refs=["whitepaper-v1.2", "code:Vault:120"]
        )

        # Get links for a function
        links = linker.get_links("Vault.withdraw")

        # Trace causal chains
        chain = linker.trace_causal_chain("oracle-manipulation-vuln")
    """

    def __init__(self) -> None:
        """Initialize the context linker."""
        self._links: Dict[str, List[LinkRecord]] = {}  # function_id -> links
        self._causal_chains: Dict[str, CausalChainLink] = {}  # chain_id -> chain
        self._causal_edges: List[CausalEdge] = []  # overlay edges
        self._context_node_index: Dict[str, Set[str]] = {}  # node_id -> function_ids

    def register_explicit_link(
        self,
        function_id: str,
        context_node_id: str,
        link_type: LinkType,
        evidence_refs: List[str],
        signals: Optional[List[str]] = None,
    ) -> LinkRecord:
        """Register an explicit link from ProtocolContextPack.

        Per 05.11-CONTEXT.md: Explicit pack mappings are authoritative.

        Args:
            function_id: Function identifier
            context_node_id: Economic context node ID
            link_type: Type of relationship
            evidence_refs: Evidence supporting the link
            signals: Optional semantic signals

        Returns:
            Created LinkRecord
        """
        record = LinkRecord(
            function_id=function_id,
            context_node_id=context_node_id,
            link_type=link_type,
            source=LinkSource.PACK,
            confidence=Confidence.CERTAIN if len(evidence_refs) >= 2 else Confidence.INFERRED,
            evidence_refs=evidence_refs,
            signals=signals or [],
            quarantined=False,  # Explicit links are never quarantined
        )

        self._add_link(record)
        return record

    def register_semantic_link(
        self,
        function_id: str,
        context_node_id: str,
        link_type: LinkType,
        signals: List[str],
        evidence_refs: Optional[List[str]] = None,
    ) -> LinkRecord:
        """Register a link inferred from semantic operations.

        Per 05.11-CONTEXT.md: Semantic links have medium confidence.
        Quarantined if missing dossier/pack corroboration.

        Args:
            function_id: Function identifier
            context_node_id: Economic context node ID
            link_type: Type of relationship
            signals: Semantic operations that justify the link
            evidence_refs: Optional corroborating evidence

        Returns:
            Created LinkRecord
        """
        evidence = evidence_refs or []
        has_corroboration = len(evidence) >= 1

        record = LinkRecord(
            function_id=function_id,
            context_node_id=context_node_id,
            link_type=link_type,
            source=LinkSource.SEMANTIC,
            confidence=Confidence.INFERRED if has_corroboration else Confidence.UNKNOWN,
            evidence_refs=evidence,
            signals=signals,
            quarantined=not has_corroboration,  # Quarantine if no corroboration
        )

        self._add_link(record)
        return record

    def register_heuristic_link(
        self,
        function_id: str,
        context_node_id: str,
        link_type: LinkType,
        reason: str,
    ) -> LinkRecord:
        """Register a heuristic-based link (low confidence, always quarantined).

        Per 05.11-CONTEXT.md: Heuristic links are quarantined and hidden
        from agents until corroborating evidence is added.

        Args:
            function_id: Function identifier
            context_node_id: Economic context node ID
            link_type: Type of relationship
            reason: Reason for the heuristic link

        Returns:
            Created LinkRecord
        """
        record = LinkRecord(
            function_id=function_id,
            context_node_id=context_node_id,
            link_type=link_type,
            source=LinkSource.HEURISTIC,
            confidence=Confidence.UNKNOWN,
            evidence_refs=[],
            signals=[f"heuristic:{reason}"],
            quarantined=True,  # Always quarantined
        )

        self._add_link(record)
        return record

    def _add_link(self, record: LinkRecord) -> None:
        """Add a link record to the internal storage.

        Args:
            record: LinkRecord to add
        """
        if record.function_id not in self._links:
            self._links[record.function_id] = []
        self._links[record.function_id].append(record)

        # Update reverse index
        if record.context_node_id not in self._context_node_index:
            self._context_node_index[record.context_node_id] = set()
        self._context_node_index[record.context_node_id].add(record.function_id)

    def get_links(self, function_id: str) -> List[LinkRecord]:
        """Get all links for a function.

        Args:
            function_id: Function identifier

        Returns:
            List of LinkRecord objects
        """
        return self._links.get(function_id, []).copy()

    def get_surfaced_links(self, function_id: str) -> List[LinkRecord]:
        """Get only surfaceable links for a function.

        Per 05.11-CONTEXT.md: Only links with two-key evidence
        and not quarantined can be surfaced to agents.

        Args:
            function_id: Function identifier

        Returns:
            List of surfaceable LinkRecord objects
        """
        return [link for link in self.get_links(function_id) if link.can_surface]

    def get_quarantined_links(self, function_id: str) -> List[LinkRecord]:
        """Get quarantined links for a function.

        Args:
            function_id: Function identifier

        Returns:
            List of quarantined LinkRecord objects
        """
        return [link for link in self.get_links(function_id) if link.quarantined]

    def get_functions_for_context_node(self, context_node_id: str) -> List[str]:
        """Get all functions linked to a context node.

        Args:
            context_node_id: Economic context node ID

        Returns:
            List of function IDs
        """
        return list(self._context_node_index.get(context_node_id, set()))

    def add_evidence_to_link(
        self,
        function_id: str,
        context_node_id: str,
        evidence_ref: str,
    ) -> bool:
        """Add evidence to an existing link.

        If the link gains two-key evidence, it may be unquarantined.

        Args:
            function_id: Function identifier
            context_node_id: Context node ID
            evidence_ref: Evidence reference to add

        Returns:
            True if evidence was added to an existing link
        """
        for link in self._links.get(function_id, []):
            if link.context_node_id == context_node_id:
                link.add_evidence(evidence_ref)
                # Unquarantine if now has two-key evidence
                if link.has_two_key_evidence and link.source != LinkSource.HEURISTIC:
                    link.quarantined = False
                return True
        return False

    def add_causal_edge(self, edge: CausalEdge) -> None:
        """Add a causal edge for overlay injection.

        Args:
            edge: CausalEdge to add
        """
        self._causal_edges.append(edge)

    def get_causal_edges(self) -> List[CausalEdge]:
        """Get all causal edges.

        Returns:
            List of CausalEdge objects
        """
        return self._causal_edges.copy()

    def trace_causal_chain(
        self,
        vulnerability_id: str,
        max_depth: int = 10,
    ) -> Optional[CausalChainLink]:
        """Trace a causal chain from a vulnerability to financial loss.

        Per 05.11-CONTEXT.md: Traces CAUSES, ENABLES, AMPLIFIES edges
        and records counterfactuals (mitigations that would break chain).

        Args:
            vulnerability_id: Starting vulnerability/condition ID
            max_depth: Maximum chain depth to trace

        Returns:
            CausalChainLink if a chain is found, None otherwise
        """
        # Check if we already have this chain cached
        cache_key = f"chain:{vulnerability_id}"
        if cache_key in self._causal_chains:
            return self._causal_chains[cache_key]

        # Build graph of causal edges
        outgoing: Dict[str, List[CausalEdge]] = {}
        for edge in self._causal_edges:
            if edge.source_node not in outgoing:
                outgoing[edge.source_node] = []
            outgoing[edge.source_node].append(edge)

        # BFS to find path to financial loss
        visited: Set[str] = set()
        queue: List[tuple] = [(vulnerability_id, [], 1.0, [])]  # (node, path, prob, counterfactuals)

        financial_loss_id = ""
        exploit_steps: List[str] = []
        probability_chain = 0.0
        counterfactuals: List[str] = []
        evidence_refs: List[str] = []

        while queue:
            current, path, prob, blocks = queue.pop(0)

            if current in visited:
                continue
            visited.add(current)

            if len(path) >= max_depth:
                continue

            # Check if this is a financial loss node
            if "loss" in current.lower() or "financial" in current.lower():
                financial_loss_id = current
                exploit_steps = path
                probability_chain = prob
                counterfactuals = blocks
                break

            # Explore outgoing edges
            for edge in outgoing.get(current, []):
                if edge.edge_type.is_positive:
                    # Follow positive edges (CAUSES, ENABLES, AMPLIFIES)
                    new_path = path + [edge.target_node]
                    new_prob = prob * edge.probability
                    new_blocks = blocks.copy()
                    evidence_refs.extend(edge.evidence_refs)

                    queue.append((edge.target_node, new_path, new_prob, new_blocks))

                elif edge.edge_type == CausalEdgeType.BLOCKS:
                    # Record blocking edge as counterfactual
                    blocks.append(edge.source_node)

        if not financial_loss_id:
            return None

        chain = CausalChainLink(
            chain_id=cache_key,
            root_cause_id=vulnerability_id,
            exploit_steps=exploit_steps,
            financial_loss_id=financial_loss_id,
            probability_chain=probability_chain,
            counterfactual_blocks=counterfactuals,
            evidence_refs=list(set(evidence_refs)),
            confidence=Confidence.INFERRED,
        )

        self._causal_chains[cache_key] = chain
        return chain

    def counterfactual_query(
        self,
        chain: CausalChainLink,
        mitigation_id: str,
    ) -> bool:
        """Query whether a mitigation would break a causal chain.

        Per 05.11-CONTEXT.md: Records counterfactual queries
        ("if X existed, would chain break?").

        Args:
            chain: CausalChainLink to query
            mitigation_id: Mitigation to check

        Returns:
            True if the mitigation would break the chain
        """
        # Check if any edge in the chain is blocked by this mitigation
        for edge in self._causal_edges:
            if edge.edge_type == CausalEdgeType.BLOCKS:
                if edge.source_node == mitigation_id:
                    if edge.target_node in chain.exploit_steps:
                        chain.add_counterfactual(mitigation_id)
                        return True

        return False

    def inject_overlay_edges(
        self,
        domain_kg: "DomainKnowledgeGraph",
    ) -> int:
        """Inject causal edges into DomainKnowledgeGraph overlay.

        Per 05.11-CONTEXT.md: Writes overlay edges (including causal edges)
        into DomainKnowledgeGraph.

        Args:
            domain_kg: DomainKnowledgeGraph to inject edges into

        Returns:
            Number of edges injected
        """
        # DomainKnowledgeGraph currently doesn't have overlay support,
        # but we prepare the edges for future integration
        injected = 0

        for edge in self._causal_edges:
            # Create a specification representing this causal relationship
            # This is a temporary approach until DomainKG has proper overlay support
            spec_id = f"causal:{edge.source_node}:{edge.target_node}"

            # Add to domain_kg if it has overlay support
            if hasattr(domain_kg, "add_overlay_edge"):
                domain_kg.add_overlay_edge(edge.to_dict())
                injected += 1

        return injected

    def backfill_from_semantic_ops(
        self,
        kg_nodes: List[Dict[str, Any]],
        operation_to_link_type: Optional[Dict[str, LinkType]] = None,
    ) -> int:
        """Backfill links from semantic operations in KG nodes.

        Per 05.11-CONTEXT.md: Semantic ops backfill links with low confidence
        and quarantine until corroborating evidence is added.

        Args:
            kg_nodes: List of KG function nodes with semantic operations
            operation_to_link_type: Mapping from op names to link types

        Returns:
            Number of links created
        """
        # Default operation mappings
        if operation_to_link_type is None:
            operation_to_link_type = {
                "TRANSFERS_VALUE_OUT": LinkType.VALUE_FLOW_THROUGH_FUNCTION,
                "READS_USER_BALANCE": LinkType.VALUE_FLOW_THROUGH_FUNCTION,
                "WRITES_USER_BALANCE": LinkType.VALUE_FLOW_THROUGH_FUNCTION,
                "READS_ORACLE": LinkType.OFFCHAIN_INPUT_FEEDS_FUNCTION,
                "CHECKS_PERMISSION": LinkType.ROLE_CONTROLS_FUNCTION,
                "MODIFIES_OWNER": LinkType.ROLE_CONTROLS_FUNCTION,
                "MODIFIES_ROLES": LinkType.ROLE_CONTROLS_FUNCTION,
                "MODIFIES_CRITICAL_STATE": LinkType.GOVERNANCE_CAN_CHANGE_STATE,
            }

        created = 0
        for node in kg_nodes:
            function_id = node.get("id", "")
            props = node.get("properties", {})
            operations = props.get("operations", [])

            for op in operations:
                if op in operation_to_link_type:
                    link_type = operation_to_link_type[op]
                    # Create a context node ID based on the operation
                    context_node_id = f"inferred:{op}:{function_id}"

                    # Register as semantic link (quarantined until corroboration)
                    self.register_semantic_link(
                        function_id=function_id,
                        context_node_id=context_node_id,
                        link_type=link_type,
                        signals=[op],
                    )
                    created += 1

        return created

    def stats(self) -> Dict[str, Any]:
        """Get linker statistics.

        Returns:
            Dict with counts and status
        """
        total_links = sum(len(links) for links in self._links.values())
        surfaced = sum(
            1
            for links in self._links.values()
            for link in links
            if link.can_surface
        )
        quarantined = sum(
            1
            for links in self._links.values()
            for link in links
            if link.quarantined
        )

        return {
            "total_functions": len(self._links),
            "total_links": total_links,
            "surfaced_links": surfaced,
            "quarantined_links": quarantined,
            "causal_edges": len(self._causal_edges),
            "causal_chains": len(self._causal_chains),
            "context_nodes": len(self._context_node_index),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert linker state to dictionary for serialization."""
        return {
            "links": {
                fn_id: [link.to_dict() for link in links]
                for fn_id, links in self._links.items()
            },
            "causal_chains": {
                chain_id: chain.to_dict()
                for chain_id, chain in self._causal_chains.items()
            },
            "causal_edges": [edge.to_dict() for edge in self._causal_edges],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextLinker":
        """Create ContextLinker from dictionary."""
        linker = cls()

        # Restore links
        for fn_id, links_data in data.get("links", {}).items():
            for link_data in links_data:
                record = LinkRecord.from_dict(link_data)
                linker._add_link(record)

        # Restore causal chains
        for chain_id, chain_data in data.get("causal_chains", {}).items():
            linker._causal_chains[chain_id] = CausalChainLink.from_dict(chain_data)

        # Restore causal edges
        for edge_data in data.get("causal_edges", []):
            linker._causal_edges.append(CausalEdge.from_dict(edge_data))

        return linker


# Export all types
__all__ = [
    "LinkSource",
    "LinkType",
    "LinkRecord",
    "CausalChainLink",
    "ContextLinker",
]
