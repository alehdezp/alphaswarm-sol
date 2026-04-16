"""Rich edge schema with intelligence for enhanced VKG.

This module implements Tier 1: Intelligent Edge Layer from the enhanced VKG architecture.
Rich edges carry risk scores, pattern tags, temporal ordering, and guard analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ExecutionContext(Enum):
    """Context in which an edge relationship is executed."""
    NORMAL = "normal"
    DELEGATECALL = "delegatecall"
    STATICCALL = "staticcall"
    CONSTRUCTOR = "constructor"
    FALLBACK = "fallback"
    RECEIVE = "receive"


class TaintSource(Enum):
    """Source of tainted data."""
    USER_INPUT = "user_input"
    EXTERNAL_CALL = "external_call"
    STORAGE = "storage"
    MSG_SENDER = "msg.sender"
    MSG_VALUE = "msg.value"
    BLOCK_DATA = "block_data"
    ORACLE = "oracle"
    UNKNOWN = "unknown"


@dataclass
class RichEdgeEvidence:
    """Evidence for a rich edge relationship."""
    file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    detail: Optional[str] = None
    ir_type: Optional[str] = None  # Slither IR type that created this edge

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "detail": self.detail,
            "ir_type": self.ir_type,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RichEdgeEvidence:
        return RichEdgeEvidence(
            file=str(data.get("file") or ""),
            line_start=data.get("line_start"),
            line_end=data.get("line_end"),
            detail=data.get("detail"),
            ir_type=data.get("ir_type"),
        )


@dataclass
class RichEdge:
    """Enhanced edge with intelligence for vulnerability detection.

    Rich edges carry more than just relationship type - they include:
    - Risk assessment (score and pattern tags)
    - Execution context (normal, delegatecall, etc.)
    - Taint propagation info
    - Temporal ordering (happens-before relationships)
    - Guard analysis (what protections exist/bypassed)
    """

    # Identity
    id: str
    type: str  # Edge type (e.g., "WRITES_STATE", "CALLS_EXTERNAL")
    source: str  # Source node ID
    target: str  # Target node ID

    # Risk Assessment
    risk_score: float = 0.0  # 0-10 scale
    pattern_tags: list[str] = field(default_factory=list)
    # e.g., ["reentrancy", "unchecked_external_call", "cei_violation"]

    # Execution Context
    execution_context: Optional[str] = None  # "normal", "delegatecall", etc.

    # Taint Information
    taint_source: Optional[str] = None  # Where tainted data originates
    taint_confidence: float = 1.0  # 0-1 confidence in taint analysis

    # Temporal Ordering (CFG-based)
    happens_before: list[str] = field(default_factory=list)  # Edge IDs this edge happens before
    happens_after: list[str] = field(default_factory=list)  # Edge IDs this edge happens after
    cfg_order: Optional[int] = None  # Position in CFG traversal

    # Guard Analysis
    guards_at_source: list[str] = field(default_factory=list)  # Guards protecting source
    guards_bypassed: list[str] = field(default_factory=list)  # Guards that could be bypassed

    # Value Transfer (for calls with value)
    transfers_value: bool = False
    value_amount: Optional[str] = None  # Expression for value (e.g., "msg.value", "amount")

    # Evidence
    evidence: list[RichEdgeEvidence] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "target": self.target,
            "risk_score": self.risk_score,
            "pattern_tags": self.pattern_tags,
            "execution_context": self.execution_context,
            "taint_source": self.taint_source,
            "taint_confidence": self.taint_confidence,
            "happens_before": self.happens_before,
            "happens_after": self.happens_after,
            "cfg_order": self.cfg_order,
            "guards_at_source": self.guards_at_source,
            "guards_bypassed": self.guards_bypassed,
            "transfers_value": self.transfers_value,
            "value_amount": self.value_amount,
            "evidence": [e.to_dict() for e in self.evidence],
            "properties": self.properties,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RichEdge:
        """Deserialize from dictionary."""
        return RichEdge(
            id=str(data.get("id") or ""),
            type=str(data.get("type") or ""),
            source=str(data.get("source") or ""),
            target=str(data.get("target") or ""),
            risk_score=float(data.get("risk_score") or 0.0),
            pattern_tags=list(data.get("pattern_tags") or []),
            execution_context=data.get("execution_context"),
            taint_source=data.get("taint_source"),
            taint_confidence=float(data.get("taint_confidence") or 1.0),
            happens_before=list(data.get("happens_before") or []),
            happens_after=list(data.get("happens_after") or []),
            cfg_order=data.get("cfg_order"),
            guards_at_source=list(data.get("guards_at_source") or []),
            guards_bypassed=list(data.get("guards_bypassed") or []),
            transfers_value=bool(data.get("transfers_value")),
            value_amount=data.get("value_amount"),
            evidence=[RichEdgeEvidence.from_dict(e) for e in data.get("evidence", [])],
            properties=dict(data.get("properties") or {}),
        )

    def is_high_risk(self, threshold: float = 7.0) -> bool:
        """Check if edge represents high-risk operation."""
        return self.risk_score >= threshold

    def has_pattern(self, pattern: str) -> bool:
        """Check if edge has a specific pattern tag."""
        return pattern in self.pattern_tags

    def has_any_pattern(self, patterns: list[str]) -> bool:
        """Check if edge has any of the specified pattern tags."""
        return bool(set(patterns) & set(self.pattern_tags))

    def is_guarded(self) -> bool:
        """Check if edge operation is protected by guards."""
        return len(self.guards_at_source) > 0

    def bypasses_guards(self) -> bool:
        """Check if edge could bypass guards."""
        return len(self.guards_bypassed) > 0


# Edge type constants with risk categorization
class EdgeType:
    """Edge type definitions with risk levels."""

    # State modification edges (high risk when unguarded)
    WRITES_STATE = "WRITES_STATE"
    WRITES_CRITICAL_STATE = "WRITES_CRITICAL_STATE"
    WRITES_BALANCE = "WRITES_BALANCE"

    # Read edges (lower risk, but important for taint)
    READS_STATE = "READS_STATE"
    READS_BALANCE = "READS_BALANCE"
    READS_ORACLE = "READS_ORACLE"

    # External call edges (high risk)
    CALLS_EXTERNAL = "CALLS_EXTERNAL"
    CALLS_UNTRUSTED = "CALLS_UNTRUSTED"
    DELEGATECALL = "DELEGATECALL"
    STATICCALL = "STATICCALL"

    # Value transfer edges (critical)
    TRANSFERS_ETH = "TRANSFERS_ETH"
    TRANSFERS_TOKEN = "TRANSFERS_TOKEN"

    # Containment edges (structural)
    CONTAINS_FUNCTION = "CONTAINS_FUNCTION"
    CONTAINS_STATE = "CONTAINS_STATE"
    FUNCTION_HAS_INPUT = "FUNCTION_HAS_INPUT"

    # Taint propagation edges
    INPUT_TAINTS_STATE = "INPUT_TAINTS_STATE"
    EXTERNAL_TAINTS = "EXTERNAL_TAINTS"

    # Meta-edges (for graph intelligence)
    SIMILAR_TO = "SIMILAR_TO"
    BUGGY_PATTERN_MATCH = "BUGGY_PATTERN_MATCH"
    REFACTOR_CANDIDATE = "REFACTOR_CANDIDATE"


# Base risk scores by edge type
EDGE_BASE_RISK: dict[str, float] = {
    EdgeType.WRITES_CRITICAL_STATE: 7.0,
    EdgeType.WRITES_BALANCE: 6.0,
    EdgeType.WRITES_STATE: 3.0,
    EdgeType.CALLS_UNTRUSTED: 8.0,
    EdgeType.DELEGATECALL: 9.0,
    EdgeType.CALLS_EXTERNAL: 5.0,
    EdgeType.STATICCALL: 2.0,
    EdgeType.TRANSFERS_ETH: 7.0,
    EdgeType.TRANSFERS_TOKEN: 6.0,
    EdgeType.INPUT_TAINTS_STATE: 4.0,
    EdgeType.READS_ORACLE: 3.0,
    EdgeType.READS_STATE: 1.0,
    EdgeType.READS_BALANCE: 2.0,
    # Meta-edges don't have inherent risk
    EdgeType.SIMILAR_TO: 0.0,
    EdgeType.BUGGY_PATTERN_MATCH: 0.0,
    EdgeType.REFACTOR_CANDIDATE: 0.0,
}


def compute_edge_risk_score(
    edge_type: str,
    execution_context: Optional[str] = None,
    is_guarded: bool = False,
    has_taint: bool = False,
    transfers_value: bool = False,
    after_external_call: bool = False,
) -> float:
    """Compute risk score for an edge based on various factors.

    Args:
        edge_type: Type of edge relationship
        execution_context: Execution context (delegatecall adds risk)
        is_guarded: Whether the operation is protected
        has_taint: Whether data is user-controlled
        transfers_value: Whether value is being transferred
        after_external_call: Whether this happens after an external call

    Returns:
        Risk score from 0-10
    """
    # Start with base risk
    base = EDGE_BASE_RISK.get(edge_type, 2.0)

    # Apply modifiers
    score = base

    # Execution context modifier
    if execution_context == ExecutionContext.DELEGATECALL.value:
        score += 2.0
    elif execution_context == ExecutionContext.FALLBACK.value:
        score += 1.0

    # Guard modifier (reduces risk)
    if is_guarded:
        score *= 0.5

    # Taint modifier (increases risk)
    if has_taint:
        score += 1.5

    # Value transfer modifier
    if transfers_value:
        score += 1.0

    # Temporal modifier (state write after external call = CEI violation)
    if after_external_call and edge_type in [EdgeType.WRITES_STATE, EdgeType.WRITES_BALANCE]:
        score += 3.0

    # Clamp to 0-10
    return min(10.0, max(0.0, score))


def determine_pattern_tags(
    edge_type: str,
    execution_context: Optional[str] = None,
    after_external_call: bool = False,
    taint_source: Optional[str] = None,
) -> list[str]:
    """Determine pattern tags for an edge based on its characteristics.

    Args:
        edge_type: Type of edge
        execution_context: Execution context
        after_external_call: Whether after external call
        taint_source: Source of tainted data

    Returns:
        List of pattern tags
    """
    tags = []

    # CEI violation pattern
    if after_external_call and edge_type in [EdgeType.WRITES_STATE, EdgeType.WRITES_BALANCE]:
        tags.append("cei_violation")
        tags.append("reentrancy_risk")

    # Delegatecall patterns
    if execution_context == ExecutionContext.DELEGATECALL.value:
        tags.append("delegatecall")
        if edge_type == EdgeType.CALLS_UNTRUSTED:
            tags.append("arbitrary_delegatecall")

    # Taint-related patterns
    if taint_source == TaintSource.USER_INPUT.value:
        tags.append("user_controlled")
    elif taint_source == TaintSource.EXTERNAL_CALL.value:
        tags.append("external_data")
    elif taint_source == TaintSource.ORACLE.value:
        tags.append("oracle_dependent")

    # Value transfer patterns
    if edge_type in [EdgeType.TRANSFERS_ETH, EdgeType.TRANSFERS_TOKEN]:
        tags.append("value_movement")

    # External call patterns
    if edge_type == EdgeType.CALLS_UNTRUSTED:
        tags.append("untrusted_call")
    elif edge_type == EdgeType.CALLS_EXTERNAL:
        tags.append("external_call")

    return tags


@dataclass
class MetaEdge(RichEdge):
    """Meta-edge for higher-order relationships.

    Meta-edges represent relationships between subgraphs or patterns,
    not direct code relationships. Examples:
    - SIMILAR_TO: Two functions have similar behavior
    - BUGGY_PATTERN_MATCH: Function matches a known vulnerability pattern
    - REFACTOR_CANDIDATE: Two code sections could be deduplicated
    """

    # Meta-edge specific fields
    similarity_score: float = 0.0  # For SIMILAR_TO edges
    matched_pattern_id: Optional[str] = None  # For BUGGY_PATTERN_MATCH
    optimization_type: Optional[str] = None  # For REFACTOR_CANDIDATE

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["similarity_score"] = self.similarity_score
        d["matched_pattern_id"] = self.matched_pattern_id
        d["optimization_type"] = self.optimization_type
        return d

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MetaEdge:
        base = RichEdge.from_dict(data)
        return MetaEdge(
            id=base.id,
            type=base.type,
            source=base.source,
            target=base.target,
            risk_score=base.risk_score,
            pattern_tags=base.pattern_tags,
            execution_context=base.execution_context,
            taint_source=base.taint_source,
            taint_confidence=base.taint_confidence,
            happens_before=base.happens_before,
            happens_after=base.happens_after,
            cfg_order=base.cfg_order,
            guards_at_source=base.guards_at_source,
            guards_bypassed=base.guards_bypassed,
            transfers_value=base.transfers_value,
            value_amount=base.value_amount,
            evidence=base.evidence,
            properties=base.properties,
            similarity_score=float(data.get("similarity_score") or 0.0),
            matched_pattern_id=data.get("matched_pattern_id"),
            optimization_type=data.get("optimization_type"),
        )


# ==============================================================================
# Phase 5: Meta-Edge Generation Functions
# ==============================================================================


def find_similar_functions(graph: Any) -> list[tuple[Any, Any, float]]:
    """Find pairs of similar functions based on behavioral signatures.

    Two functions are considered similar if they have the same or very similar
    behavioral signatures, indicating similar security behavior patterns.

    Args:
        graph: KnowledgeGraph containing function nodes

    Returns:
        List of (fn1, fn2, similarity_score) tuples
    """
    similar_pairs = []
    functions = [n for n in graph.nodes.values() if n.type == "Function"]

    # Group by behavioral signature for exact matches
    signature_groups: dict[str, list[Any]] = {}
    for fn in functions:
        sig = fn.properties.get("behavioral_signature", "")
        if sig:
            signature_groups.setdefault(sig, []).append(fn)

    # Find exact signature matches
    for sig, fn_list in signature_groups.items():
        if len(fn_list) > 1:
            for i, fn1 in enumerate(fn_list):
                for fn2 in fn_list[i + 1:]:
                    similar_pairs.append((fn1, fn2, 1.0))

    # Find fuzzy matches based on semantic_ops overlap
    for i, fn1 in enumerate(functions):
        ops1 = set(fn1.properties.get("semantic_ops", []))
        if not ops1:
            continue

        for fn2 in functions[i + 1:]:
            ops2 = set(fn2.properties.get("semantic_ops", []))
            if not ops2:
                continue

            # Jaccard similarity for operations
            intersection = len(ops1 & ops2)
            union = len(ops1 | ops2)
            if union > 0:
                similarity = intersection / union
                if similarity >= 0.7 and similarity < 1.0:  # Only fuzzy matches
                    similar_pairs.append((fn1, fn2, similarity))

    return similar_pairs


def compute_similarity_risk(fn1: Any, fn2: Any) -> float:
    """Compute risk score for similarity between two functions.

    Higher risk if:
    - Similar functions have different guards
    - Similar functions access different state (potential inconsistency)
    - One is public/external and one is internal

    Args:
        fn1: First function node
        fn2: Second function node

    Returns:
        Risk score from 0-10
    """
    base_score = 2.0

    # Different visibility levels
    vis1 = fn1.properties.get("visibility", "")
    vis2 = fn2.properties.get("visibility", "")
    if vis1 != vis2:
        base_score += 2.0
        # One public/external, one internal = higher risk
        if (vis1 in ["public", "external"] and vis2 == "internal") or \
           (vis2 in ["public", "external"] and vis1 == "internal"):
            base_score += 1.5

    # Different access control
    gate1 = fn1.properties.get("has_access_gate", False)
    gate2 = fn2.properties.get("has_access_gate", False)
    if gate1 != gate2:
        base_score += 3.0  # Significant risk if guards differ

    # Different state written
    state1 = set(fn1.properties.get("state_variables_written_names", []))
    state2 = set(fn2.properties.get("state_variables_written_names", []))
    if state1 and state2 and state1 != state2:
        base_score += 1.5

    return min(base_score, 10.0)


# Known vulnerability patterns for matching
KNOWN_VULNERABILITY_PATTERNS = [
    {
        "id": "reentrancy-classic",
        "name": "Classic Reentrancy",
        "signature_pattern": r".*X:out.*W:bal.*",  # Transfer before balance update
        "severity_score": 9.0,
        "required_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
    },
    {
        "id": "reentrancy-read-only",
        "name": "Read-Only Reentrancy",
        "signature_pattern": r".*X:call.*R:bal.*",  # External call before balance read
        "severity_score": 7.0,
        "required_ops": ["CALLS_EXTERNAL", "READS_USER_BALANCE"],
    },
    {
        "id": "unchecked-oracle",
        "name": "Unchecked Oracle Price",
        "signature_pattern": r".*R:orc.*",  # Oracle read without staleness check
        "severity_score": 7.0,
        "required_ops": ["READS_ORACLE"],
        "required_properties": {"has_staleness_check": False},
    },
    {
        "id": "missing-access-control",
        "name": "Missing Access Control",
        "signature_pattern": r".*M:crit.*",  # Critical state modification
        "severity_score": 8.0,
        "required_ops": ["MODIFIES_CRITICAL_STATE"],
        "required_properties": {"has_access_gate": False, "visibility": ["public", "external"]},
    },
    {
        "id": "division-before-multiplication",
        "name": "Division Before Multiplication",
        "signature_pattern": r".*A:div.*A:mul.*",  # Division then multiplication
        "severity_score": 5.0,
        "required_ops": ["PERFORMS_DIVISION", "PERFORMS_MULTIPLICATION"],
    },
]


def matches_pattern(fn: Any, pattern: dict) -> bool:
    """Check if a function matches a known vulnerability pattern.

    Args:
        fn: Function node
        pattern: Pattern definition dict

    Returns:
        True if function matches the pattern
    """
    import re

    # Check required operations
    ops = set(fn.properties.get("semantic_ops", []))
    required_ops = set(pattern.get("required_ops", []))
    if not required_ops.issubset(ops):
        return False

    # Check signature pattern
    sig = fn.properties.get("behavioral_signature", "")
    sig_pattern = pattern.get("signature_pattern", "")
    if sig_pattern and not re.search(sig_pattern, sig):
        return False

    # Check required properties
    for prop, expected in pattern.get("required_properties", {}).items():
        actual = fn.properties.get(prop)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False

    return True


def generate_meta_edges(graph: Any) -> list[MetaEdge]:
    """Generate meta-edges for the graph.

    Creates:
    - SIMILAR_TO edges between similar functions
    - BUGGY_PATTERN_MATCH edges for vulnerability pattern matches

    Args:
        graph: KnowledgeGraph

    Returns:
        List of MetaEdge objects
    """
    meta_edges = []
    edge_counter = 0

    # Generate SIMILAR_TO edges
    for fn1, fn2, similarity in find_similar_functions(graph):
        edge_counter += 1
        risk = compute_similarity_risk(fn1, fn2)
        meta_edges.append(MetaEdge(
            id=f"meta:similar:{edge_counter}",
            type=EdgeType.SIMILAR_TO,
            source=fn1.id,
            target=fn2.id,
            risk_score=risk,
            pattern_tags=["similar_function", "consistency_risk"] if risk > 5.0 else ["similar_function"],
            similarity_score=similarity,
        ))

    # Generate BUGGY_PATTERN_MATCH edges
    functions = [n for n in graph.nodes.values() if n.type == "Function"]
    for fn in functions:
        for pattern in KNOWN_VULNERABILITY_PATTERNS:
            if matches_pattern(fn, pattern):
                edge_counter += 1
                meta_edges.append(MetaEdge(
                    id=f"meta:pattern:{edge_counter}",
                    type=EdgeType.BUGGY_PATTERN_MATCH,
                    source=fn.id,
                    target=f"pattern:{pattern['id']}",
                    risk_score=pattern["severity_score"],
                    pattern_tags=[pattern["id"], pattern["name"].lower().replace(" ", "_")],
                    matched_pattern_id=pattern["id"],
                ))

    return meta_edges


def create_rich_edge(
    edge_id: str,
    edge_type: str,
    source: str,
    target: str,
    execution_context: Optional[str] = None,
    taint_source: Optional[str] = None,
    cfg_order: Optional[int] = None,
    guards: Optional[list[str]] = None,
    transfers_value: bool = False,
    value_amount: Optional[str] = None,
    after_external_call: bool = False,
    file: Optional[str] = None,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
) -> RichEdge:
    """Factory function to create a fully-populated RichEdge.

    This handles automatic risk scoring and pattern tag assignment.

    Args:
        edge_id: Unique edge identifier
        edge_type: Type of edge (from EdgeType)
        source: Source node ID
        target: Target node ID
        execution_context: Execution context (delegatecall, etc.)
        taint_source: Source of tainted data
        cfg_order: Position in CFG traversal
        guards: List of guards protecting this edge
        transfers_value: Whether value is transferred
        value_amount: Expression for value amount
        after_external_call: Whether this happens after an external call
        file: Source file path
        line_start: Starting line number
        line_end: Ending line number

    Returns:
        Fully configured RichEdge
    """
    is_guarded = bool(guards)
    has_taint = taint_source is not None

    # Compute risk score
    risk_score = compute_edge_risk_score(
        edge_type=edge_type,
        execution_context=execution_context,
        is_guarded=is_guarded,
        has_taint=has_taint,
        transfers_value=transfers_value,
        after_external_call=after_external_call,
    )

    # Determine pattern tags
    pattern_tags = determine_pattern_tags(
        edge_type=edge_type,
        execution_context=execution_context,
        after_external_call=after_external_call,
        taint_source=taint_source,
    )

    # Create evidence if location info provided
    evidence = []
    if file:
        evidence.append(RichEdgeEvidence(
            file=file,
            line_start=line_start,
            line_end=line_end,
        ))

    return RichEdge(
        id=edge_id,
        type=edge_type,
        source=source,
        target=target,
        risk_score=risk_score,
        pattern_tags=pattern_tags,
        execution_context=execution_context,
        taint_source=taint_source,
        cfg_order=cfg_order,
        guards_at_source=guards or [],
        transfers_value=transfers_value,
        value_amount=value_amount,
        evidence=evidence,
    )
