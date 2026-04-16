"""
Domain Knowledge Graph - Core Implementation

Defines specifications, invariants, and DeFi primitives that capture
WHAT CODE SHOULD DO - enabling business logic vulnerability detection.

Phase 05.11-03: Gap Graph Overlay
- GapNode: Represents missing context that needs expansion or human review
- CausalGapNode: Gap node for incomplete causal chains
- OmissionLedger: Tracks all gap nodes for auditability
- Gap nodes trigger context expansion or human review
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Phase 05.11-03: Gap Node Types
# =============================================================================


class GapNodeType(Enum):
    """Types of gap nodes in the gap graph overlay.

    Per 05.11-03: Gap nodes represent missing or uncertain information
    that requires context expansion or human review.
    """

    MISSING_CONTEXT = "missing_context"       # Missing economic/protocol context
    INCOMPLETE_CAUSAL = "incomplete_causal"   # Incomplete causal chain
    STALE_FACT = "stale_fact"                 # Fact that has expired
    CONFLICTING_EVIDENCE = "conflicting_evidence"  # Conflicting sources
    MISSING_EXPECTATION = "missing_expectation"    # No declared expectation
    UNKNOWN_CONTROL = "unknown_control"       # Unknown access control policy
    AMBIGUOUS_INVARIANT = "ambiguous_invariant"    # Unclear invariant


class GapNodeStatus(Enum):
    """Status of a gap node."""

    OPEN = "open"                # Gap is unresolved
    EXPANDING = "expanding"      # Context expansion in progress
    HUMAN_REVIEW = "human_review"  # Assigned to human reviewer
    RESOLVED = "resolved"        # Gap has been filled
    DISMISSED = "dismissed"      # Gap was false positive


@dataclass
class GapNode:
    """A gap node representing missing context.

    Per 05.11-03: Gap nodes are created when:
    - Missing context edges exist (no economic/protocol context)
    - Context is stale (expired TTL)
    - Conflicting evidence exists
    - No declared expectation for misconfig detection

    Gap nodes require context expansion or human review
    before confidence can be upgraded.

    Attributes:
        id: Unique identifier for the gap node
        gap_type: Type of gap (GapNodeType)
        status: Current status (GapNodeStatus)
        related_entity_id: ID of the entity missing context
        description: Human-readable description of what's missing
        evidence_refs: References to what triggered this gap
        expansion_hints: Hints for how to resolve the gap
        created_at: When the gap was created
        resolved_at: When the gap was resolved (if resolved)
        resolution_notes: Notes on how it was resolved
    """

    id: str
    gap_type: GapNodeType
    status: GapNodeStatus = GapNodeStatus.OPEN
    related_entity_id: str = ""
    description: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    expansion_hints: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    resolution_notes: str = ""

    def mark_expanding(self) -> None:
        """Mark gap as being expanded."""
        self.status = GapNodeStatus.EXPANDING
        logger.info(f"Gap {self.id} marked as expanding")

    def mark_human_review(self) -> None:
        """Mark gap for human review."""
        self.status = GapNodeStatus.HUMAN_REVIEW
        logger.info(f"Gap {self.id} assigned to human review")

    def resolve(self, notes: str = "") -> None:
        """Mark gap as resolved."""
        self.status = GapNodeStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc).isoformat()
        self.resolution_notes = notes
        logger.info(f"Gap {self.id} resolved: {notes}")

    def dismiss(self, notes: str = "") -> None:
        """Dismiss gap as false positive."""
        self.status = GapNodeStatus.DISMISSED
        self.resolved_at = datetime.now(timezone.utc).isoformat()
        self.resolution_notes = notes
        logger.info(f"Gap {self.id} dismissed: {notes}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "gap_type": self.gap_type.value,
            "status": self.status.value,
            "related_entity_id": self.related_entity_id,
            "description": self.description,
            "evidence_refs": self.evidence_refs,
            "expansion_hints": self.expansion_hints,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolution_notes": self.resolution_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GapNode":
        """Create GapNode from dictionary."""
        return cls(
            id=data.get("id", ""),
            gap_type=GapNodeType(data.get("gap_type", "missing_context")),
            status=GapNodeStatus(data.get("status", "open")),
            related_entity_id=data.get("related_entity_id", ""),
            description=data.get("description", ""),
            evidence_refs=data.get("evidence_refs", []),
            expansion_hints=data.get("expansion_hints", []),
            created_at=data.get("created_at", ""),
            resolved_at=data.get("resolved_at"),
            resolution_notes=data.get("resolution_notes", ""),
        )


@dataclass
class CausalGapNode(GapNode):
    """Gap node for incomplete causal chains.

    Per 05.11-03: Created when causal chain validation fails.
    Tracks which link types are missing and what probability
    would be needed to make the chain viable.

    Attributes:
        vulnerability_id: ID of the vulnerability with incomplete chain
        missing_link_types: List of missing link types (root_cause, exploit_step, financial_loss)
        current_chain_probability: Current chain probability
        required_probability: Probability needed for viability (0.1)
    """

    vulnerability_id: str = ""
    missing_link_types: List[str] = field(default_factory=list)
    current_chain_probability: float = 0.0
    required_probability: float = 0.1

    def __post_init__(self) -> None:
        """Set gap type to incomplete causal."""
        self.gap_type = GapNodeType.INCOMPLETE_CAUSAL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        base = super().to_dict()
        base.update({
            "vulnerability_id": self.vulnerability_id,
            "missing_link_types": self.missing_link_types,
            "current_chain_probability": self.current_chain_probability,
            "required_probability": self.required_probability,
        })
        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalGapNode":
        """Create CausalGapNode from dictionary."""
        node = cls(
            id=data.get("id", ""),
            gap_type=GapNodeType.INCOMPLETE_CAUSAL,
            status=GapNodeStatus(data.get("status", "open")),
            related_entity_id=data.get("related_entity_id", ""),
            description=data.get("description", ""),
            evidence_refs=data.get("evidence_refs", []),
            expansion_hints=data.get("expansion_hints", []),
            created_at=data.get("created_at", ""),
            resolved_at=data.get("resolved_at"),
            resolution_notes=data.get("resolution_notes", ""),
            vulnerability_id=data.get("vulnerability_id", ""),
            missing_link_types=data.get("missing_link_types", []),
            current_chain_probability=data.get("current_chain_probability", 0.0),
            required_probability=data.get("required_probability", 0.1),
        )
        return node


class OmissionLedger:
    """Ledger tracking all gap nodes for auditability.

    Per 05.11-03: Gap nodes are stored in the omission ledger
    for transparency and auditability. The ledger tracks:
    - All created gap nodes
    - Resolution history
    - Patterns of missing context

    Usage:
        ledger = OmissionLedger()

        # Create gap node
        gap = ledger.create_gap(
            gap_type=GapNodeType.MISSING_CONTEXT,
            related_entity_id="fn:Vault.withdraw",
            description="Missing economic context for value flow"
        )

        # Query open gaps
        open_gaps = ledger.get_open_gaps()

        # Resolve gap
        ledger.resolve_gap(gap.id, "Added protocol context pack")
    """

    def __init__(self) -> None:
        """Initialize empty omission ledger."""
        self._gaps: Dict[str, GapNode] = {}
        self._counter = 0

    def create_gap(
        self,
        gap_type: GapNodeType,
        related_entity_id: str,
        description: str,
        evidence_refs: Optional[List[str]] = None,
        expansion_hints: Optional[List[str]] = None,
    ) -> GapNode:
        """Create a new gap node.

        Args:
            gap_type: Type of gap
            related_entity_id: ID of entity missing context
            description: What's missing
            evidence_refs: References to triggering evidence
            expansion_hints: Hints for resolution

        Returns:
            Created GapNode
        """
        self._counter += 1
        gap_id = f"gap-{self._counter:04d}"

        gap = GapNode(
            id=gap_id,
            gap_type=gap_type,
            related_entity_id=related_entity_id,
            description=description,
            evidence_refs=evidence_refs or [],
            expansion_hints=expansion_hints or [],
        )

        self._gaps[gap_id] = gap
        logger.info(f"Created gap node: {gap_id} ({gap_type.value}) for {related_entity_id}")

        return gap

    def create_causal_gap(
        self,
        vulnerability_id: str,
        missing_link_types: List[str],
        current_probability: float = 0.0,
        description: str = "",
    ) -> CausalGapNode:
        """Create a causal gap node for incomplete chains.

        Args:
            vulnerability_id: ID of the vulnerability
            missing_link_types: List of missing link types
            current_probability: Current chain probability
            description: What's missing

        Returns:
            Created CausalGapNode
        """
        self._counter += 1
        gap_id = f"causal-gap-{self._counter:04d}"

        if not description:
            description = f"Incomplete causal chain: missing {missing_link_types}"

        gap = CausalGapNode(
            id=gap_id,
            related_entity_id=vulnerability_id,
            description=description,
            vulnerability_id=vulnerability_id,
            missing_link_types=missing_link_types,
            current_chain_probability=current_probability,
            expansion_hints=[
                f"Provide evidence for {lt}" for lt in missing_link_types
            ],
        )

        self._gaps[gap_id] = gap
        logger.info(f"Created causal gap: {gap_id} for {vulnerability_id} (missing: {missing_link_types})")

        return gap

    def get_gap(self, gap_id: str) -> Optional[GapNode]:
        """Get gap node by ID."""
        return self._gaps.get(gap_id)

    def get_open_gaps(self) -> List[GapNode]:
        """Get all open gap nodes."""
        return [g for g in self._gaps.values() if g.status == GapNodeStatus.OPEN]

    def get_gaps_for_entity(self, entity_id: str) -> List[GapNode]:
        """Get all gaps for a specific entity."""
        return [g for g in self._gaps.values() if g.related_entity_id == entity_id]

    def get_human_review_gaps(self) -> List[GapNode]:
        """Get gaps assigned to human review."""
        return [g for g in self._gaps.values() if g.status == GapNodeStatus.HUMAN_REVIEW]

    def resolve_gap(self, gap_id: str, notes: str = "") -> bool:
        """Resolve a gap node.

        Args:
            gap_id: ID of gap to resolve
            notes: Resolution notes

        Returns:
            True if resolved, False if not found
        """
        gap = self._gaps.get(gap_id)
        if gap:
            gap.resolve(notes)
            return True
        return False

    def assign_to_human(self, gap_id: str) -> bool:
        """Assign gap to human review.

        Args:
            gap_id: ID of gap to assign

        Returns:
            True if assigned, False if not found
        """
        gap = self._gaps.get(gap_id)
        if gap:
            gap.mark_human_review()
            return True
        return False

    def stats(self) -> Dict[str, int]:
        """Get statistics about gap nodes."""
        by_status = {}
        by_type = {}

        for gap in self._gaps.values():
            status = gap.status.value
            by_status[status] = by_status.get(status, 0) + 1

            gap_type = gap.gap_type.value
            by_type[gap_type] = by_type.get(gap_type, 0) + 1

        return {
            "total": len(self._gaps),
            "by_status": by_status,
            "by_type": by_type,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert ledger to dictionary for serialization."""
        return {
            "gaps": {k: v.to_dict() for k, v in self._gaps.items()},
            "counter": self._counter,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OmissionLedger":
        """Create OmissionLedger from dictionary."""
        ledger = cls()
        ledger._counter = data.get("counter", 0)

        for gap_id, gap_data in data.get("gaps", {}).items():
            if gap_data.get("gap_type") == "incomplete_causal":
                ledger._gaps[gap_id] = CausalGapNode.from_dict(gap_data)
            else:
                ledger._gaps[gap_id] = GapNode.from_dict(gap_data)

        return ledger


# =============================================================================
# Original Types
# =============================================================================


class SpecType(Enum):
    """Types of specifications."""
    ERC_STANDARD = "erc_standard"
    DEFI_PRIMITIVE = "defi_primitive"
    SECURITY_PATTERN = "security_pattern"
    PROTOCOL_INVARIANT = "protocol_invariant"


@dataclass
class Invariant:
    """
    A property that should always hold.

    Invariants are conditions that must remain true throughout execution.
    Violations indicate business logic bugs.
    """
    id: str
    description: str  # Human-readable explanation
    formal: Optional[str] = None  # SMT-LIB or similar (future)
    scope: str = "function"  # "function", "contract", "transaction"

    # Semantic operation signature that would violate this
    # e.g., "W:bal→X:out" violates CEI pattern
    violation_signature: Optional[str] = None

    # Natural language conditions
    must_have: List[str] = field(default_factory=list)  # Required properties
    must_not_have: List[str] = field(default_factory=list)  # Forbidden properties


@dataclass
class InvariantViolation:
    """Detected invariant violation."""
    invariant: Invariant
    function_id: str
    evidence: List[str]  # Why this is a violation
    severity: str  # "critical", "high", "medium", "low"
    confidence: float  # 0.0 to 1.0


@dataclass
class Specification:
    """
    Formal or semi-formal specification of expected behavior.

    This is the KEY data structure enabling business logic detection.
    """
    id: str
    spec_type: SpecType
    name: str
    description: str
    version: str  # e.g., "EIP-20", "ERC-4626"

    # Function signatures this spec applies to
    function_signatures: List[str] = field(default_factory=list)

    # Semantic operation patterns that indicate this spec
    expected_operations: List[str] = field(default_factory=list)

    # What must be true
    invariants: List[Invariant] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)

    # Security considerations
    common_violations: List[str] = field(default_factory=list)
    related_cwes: List[str] = field(default_factory=list)

    # For matching code to specs
    semantic_tags: List[str] = field(default_factory=list)

    # Links to external documentation
    external_refs: Dict[str, str] = field(default_factory=dict)


@dataclass
class DeFiPrimitive:
    """
    DeFi building block with known security properties.

    Primitives are higher-level than specs - they describe
    common patterns that combine multiple operations.
    """
    id: str
    name: str  # "flash_loan", "amm_swap", "lending_pool"
    description: str

    # Structural pattern
    entry_functions: List[str] = field(default_factory=list)
    callback_pattern: Optional[str] = None  # For flash loans, etc.

    # Related specs this primitive typically implements
    implements_specs: List[str] = field(default_factory=list)

    # Security model
    trust_assumptions: List[str] = field(default_factory=list)
    attack_surface: List[str] = field(default_factory=list)
    known_attack_patterns: List[str] = field(default_factory=list)

    # Invariants specific to this primitive
    primitive_invariants: List[Invariant] = field(default_factory=list)


class DomainKnowledgeGraph:
    """
    Knowledge graph of WHAT SHOULD BE TRUE.

    Enables detecting semantic/business logic bugs by comparing
    actual code behavior against specifications.
    """

    def __init__(self):
        """Initialize empty domain knowledge graph."""
        self.specifications: Dict[str, Specification] = {}
        self.primitives: Dict[str, DeFiPrimitive] = {}
        self._semantic_index: Dict[str, List[str]] = {}  # tag -> spec_ids
        self._sig_index: Dict[str, List[str]] = {}  # signature -> spec_ids

    def add_specification(self, spec: Specification) -> None:
        """
        Add a specification and index it.

        Args:
            spec: Specification to add
        """
        self.specifications[spec.id] = spec

        # Index by semantic tags
        for tag in spec.semantic_tags:
            if tag not in self._semantic_index:
                self._semantic_index[tag] = []
            self._semantic_index[tag].append(spec.id)

        # Index by function signatures
        for sig in spec.function_signatures:
            if sig not in self._sig_index:
                self._sig_index[sig] = []
            self._sig_index[sig].append(spec.id)

    def add_primitive(self, primitive: DeFiPrimitive) -> None:
        """
        Add a DeFi primitive.

        Args:
            primitive: DeFiPrimitive to add
        """
        self.primitives[primitive.id] = primitive

    def find_matching_specs(
        self,
        fn_node: Dict[str, Any],
        min_confidence: float = 0.5
    ) -> List[Tuple[Specification, float]]:
        """
        Find specifications that might apply to a function.

        Matching strategies:
        1. Exact signature match (highest confidence)
        2. Semantic operation overlap
        3. Semantic tag match

        Args:
            fn_node: Function node from Code KG
            min_confidence: Minimum confidence threshold

        Returns:
            List of (spec, confidence) tuples sorted by confidence
        """
        matches: Dict[str, float] = {}  # spec_id -> confidence

        fn_sig = fn_node.get("signature", "")
        fn_ops = set(fn_node.get("properties", {}).get("operations", []))

        # Strategy 1: Exact signature match (1.0 confidence)
        if fn_sig in self._sig_index:
            for spec_id in self._sig_index[fn_sig]:
                matches[spec_id] = 1.0

        # Strategy 2: Semantic operation overlap
        for spec_id, spec in self.specifications.items():
            if spec_id in matches:
                continue  # Already matched exactly

            spec_ops = set(spec.expected_operations)
            if not spec_ops:
                continue

            overlap = len(fn_ops & spec_ops)
            if overlap > 0:
                # Jaccard similarity
                confidence = overlap / len(fn_ops | spec_ops)
                if confidence >= min_confidence:
                    matches[spec_id] = confidence

        # Strategy 3: Semantic tag match (if no operations matched)
        fn_name = fn_node.get("name", "").lower()
        for tag, spec_ids in self._semantic_index.items():
            if tag.lower() in fn_name:
                for spec_id in spec_ids:
                    if spec_id not in matches:
                        matches[spec_id] = 0.5  # Medium confidence

        # Convert to list of (spec, confidence) tuples
        result = [
            (self.specifications[spec_id], conf)
            for spec_id, conf in matches.items()
        ]

        # Sort by confidence descending
        result.sort(key=lambda x: x[1], reverse=True)

        return result

    def check_invariant(
        self,
        fn_node: Dict[str, Any],
        spec: Specification,
        behavioral_signature: str
    ) -> List[InvariantViolation]:
        """
        Check if function violates any spec invariants.

        Args:
            fn_node: Function node from Code KG
            spec: Specification to check against
            behavioral_signature: Function's behavioral signature

        Returns:
            List of detected violations
        """
        violations = []
        props = fn_node.get("properties", {})

        for inv in spec.invariants:
            # Check violation signature
            if inv.violation_signature:
                if inv.violation_signature in behavioral_signature:
                    violations.append(InvariantViolation(
                        invariant=inv,
                        function_id=fn_node.get("id", "unknown"),
                        evidence=[
                            f"Behavioral signature '{behavioral_signature}' matches violation pattern '{inv.violation_signature}'"
                        ],
                        severity="high",
                        confidence=0.9
                    ))

            # Check must_have requirements
            for req in inv.must_have:
                if not props.get(req, False):
                    violations.append(InvariantViolation(
                        invariant=inv,
                        function_id=fn_node.get("id", "unknown"),
                        evidence=[f"Missing required property: {req}"],
                        severity="medium",
                        confidence=0.8
                    ))

            # Check must_not_have restrictions
            for restriction in inv.must_not_have:
                if props.get(restriction, False):
                    violations.append(InvariantViolation(
                        invariant=inv,
                        function_id=fn_node.get("id", "unknown"),
                        evidence=[f"Has forbidden property: {restriction}"],
                        severity="medium",
                        confidence=0.8
                    ))

        return violations

    def get_specification(self, spec_id: str) -> Optional[Specification]:
        """
        Get specification by ID.

        Args:
            spec_id: Specification ID

        Returns:
            Specification if found, None otherwise
        """
        return self.specifications.get(spec_id)

    def get_primitive(self, primitive_id: str) -> Optional[DeFiPrimitive]:
        """
        Get primitive by ID.

        Args:
            primitive_id: Primitive ID

        Returns:
            DeFiPrimitive if found, None otherwise
        """
        return self.primitives.get(primitive_id)

    def list_specifications(self, spec_type: Optional[SpecType] = None) -> List[Specification]:
        """
        List all specifications, optionally filtered by type.

        Args:
            spec_type: Optional type filter

        Returns:
            List of specifications
        """
        if spec_type:
            return [s for s in self.specifications.values() if s.spec_type == spec_type]
        return list(self.specifications.values())

    def list_primitives(self) -> List[DeFiPrimitive]:
        """
        List all DeFi primitives.

        Returns:
            List of primitives
        """
        return list(self.primitives.values())

    def load_all(self) -> None:
        """
        Load all builtin specifications and DeFi primitives.
        """
        from .specs import load_all_specs

        specs, prims = load_all_specs()
        for spec in specs:
            self.add_specification(spec)
        for prim in prims:
            self.add_primitive(prim)

    def stats(self) -> Dict[str, int]:
        """
        Get statistics about the knowledge graph.

        Returns:
            Dict with counts
        """
        return {
            "total_specifications": len(self.specifications),
            "total_primitives": len(self.primitives),
            "erc_standards": len([s for s in self.specifications.values()
                                 if s.spec_type == SpecType.ERC_STANDARD]),
            "defi_primitives_spec": len([s for s in self.specifications.values()
                                        if s.spec_type == SpecType.DEFI_PRIMITIVE]),
            "security_patterns": len([s for s in self.specifications.values()
                                     if s.spec_type == SpecType.SECURITY_PATTERN]),
        }
