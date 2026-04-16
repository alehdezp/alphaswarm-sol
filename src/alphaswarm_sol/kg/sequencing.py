"""Operation Sequencing for True VKG (Phases 2 and 5.9).

This module provides CFG-ordered operation sequencing to enable pattern
detection based on operation ordering, like detecting reentrancy via:
- External call BEFORE state write (vulnerable)
- State write BEFORE external call (safe CEI)

Key concepts:
- OrderedOperation: Operation with CFG position and metadata
- Operation Ordering: Pairs of (before, after) operations for pattern matching
- Behavioral Signature: Compact string encoding of operation sequence

Phase 5.9 Enhancements:
- Path-qualified ordering using dominance analysis
- Interprocedural ordering summaries for modifiers and internal calls
- compute_path_qualified_ordering() for dominance-aware ordering
- Backward compatibility: old API returns boolean, new API returns PathQualifiedOrdering
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from alphaswarm_sol.kg.operations import (
    SemanticOperation,
    OperationOccurrence,
    OP_CODES,
    derive_all_operations,
    compute_behavioral_signature,
    compute_ordering_pairs,
)

# Phase 5.9: Dominance-based ordering imports
from alphaswarm_sol.kg.dominance import (
    DominanceAnalyzer,
    OrderingRelation,
    PathQualifiedOrdering,
    ModifierSummary,
    ModifierChainSummary,
    InternalCallSummary,
    create_analyzer_for_function,
    compute_modifier_summary,
    compute_modifier_chain_dominance,
    compute_internal_call_summary,
    extract_cfg_nodes,
)


@dataclass
class OrderedOperation:
    """An operation with full CFG ordering context.

    Extends OperationOccurrence with additional sequencing metadata.
    """
    operation: str  # Operation name (e.g., "TRANSFERS_VALUE_OUT")
    cfg_order: int  # Position in CFG traversal (0-indexed)
    node_id: int    # CFG node identifier
    line_number: int  # Source line number
    detail: Optional[str] = None  # Additional context


def extract_operation_sequence(fn: Any) -> List[OrderedOperation]:
    """Extract ordered operations from a function using CFG traversal.

    This function traverses the CFG and extracts all semantic operations
    in execution order, enabling pattern detection based on sequencing.

    Args:
        fn: A Slither Function object

    Returns:
        List of OrderedOperation objects, sorted by CFG order
    """
    # Use Phase 1 detector to get all operations
    occurrences = derive_all_operations(fn)

    # Convert to OrderedOperation with node IDs
    operations: List[OrderedOperation] = []
    for occ in occurrences:
        operations.append(OrderedOperation(
            operation=occ.operation.name,
            cfg_order=occ.cfg_order,
            node_id=occ.cfg_order,  # Use cfg_order as node_id when real ID unavailable
            line_number=occ.line_number,
            detail=occ.detail,
        ))

    # Sort by CFG order
    operations.sort(key=lambda x: x.cfg_order)
    return operations


def get_operation_sequence_data(fn: Any) -> List[Dict[str, Any]]:
    """Get operation sequence as serializable data.

    Args:
        fn: A Slither Function object

    Returns:
        List of dicts with op, order, line, detail keys
    """
    operations = extract_operation_sequence(fn)
    return [
        {
            "op": op.operation,
            "order": op.cfg_order,
            "line": op.line_number,
            "detail": op.detail,
        }
        for op in operations
    ]


def get_ordering_pairs(fn: Any) -> List[Tuple[str, str]]:
    """Get all operation ordering pairs for a function.

    For each pair of operations (A, B) where A happens before B in the CFG,
    returns (A.name, B.name). This enables pattern matching like:

        sequence_order:
          before: CALLS_EXTERNAL
          after: WRITES_USER_BALANCE

    Args:
        fn: A Slither Function object

    Returns:
        List of (before_op_name, after_op_name) tuples
    """
    occurrences = derive_all_operations(fn)
    return compute_ordering_pairs(occurrences)


def has_ordering(
    fn: Any,
    before: str,
    after: str,
) -> bool:
    """Check if an operation occurs before another in the CFG.

    Args:
        fn: A Slither Function object
        before: Operation name that should come first
        after: Operation name that should come after

    Returns:
        True if 'before' operation occurs before 'after' operation
    """
    pairs = get_ordering_pairs(fn)
    return (before, after) in pairs


def detect_vulnerable_reentrancy_pattern(fn: Any) -> bool:
    """Detect vulnerable reentrancy pattern: external call before state write.

    This is a convenience function for the classic reentrancy pattern where
    an external call happens before a balance write.

    Args:
        fn: A Slither Function object

    Returns:
        True if vulnerable pattern detected
    """
    pairs = get_ordering_pairs(fn)

    # Check for external call before balance write
    external_ops = {"CALLS_EXTERNAL", "CALLS_UNTRUSTED", "TRANSFERS_VALUE_OUT"}
    balance_write_ops = {"WRITES_USER_BALANCE"}

    for before, after in pairs:
        if before in external_ops and after in balance_write_ops:
            return True

    return False


def detect_cei_pattern(fn: Any) -> bool:
    """Detect safe CEI pattern: state write before external call.

    Checks-Effects-Interactions pattern where state changes
    happen before any external calls.

    Args:
        fn: A Slither Function object

    Returns:
        True if CEI pattern detected (state writes before external calls)
    """
    operations = extract_operation_sequence(fn)

    # Get positions of external calls and state writes
    external_positions: List[int] = []
    write_positions: List[int] = []

    external_ops = {"CALLS_EXTERNAL", "CALLS_UNTRUSTED", "TRANSFERS_VALUE_OUT"}
    write_ops = {"WRITES_USER_BALANCE", "MODIFIES_CRITICAL_STATE"}

    for op in operations:
        if op.operation in external_ops:
            external_positions.append(op.cfg_order)
        if op.operation in write_ops:
            write_positions.append(op.cfg_order)

    # CEI: all writes should happen before all external calls
    if not external_positions or not write_positions:
        return True  # No external calls or no writes = safe

    max_write = max(write_positions)
    min_external = min(external_positions)

    return max_write < min_external


def compute_signature_from_fn(fn: Any) -> str:
    """Compute behavioral signature directly from a function.

    Args:
        fn: A Slither Function object

    Returns:
        Behavioral signature string (e.g., "R:bal->W:bal->X:out")
    """
    occurrences = derive_all_operations(fn)
    return compute_behavioral_signature(occurrences)


# =============================================================================
# Phase 5.9: Dominance-Based Ordering
# =============================================================================


def compute_path_qualified_ordering(
    op_a: OperationOccurrence,
    op_b: OperationOccurrence,
    fn: Any,
    modifier_summaries: Optional[ModifierChainSummary] = None,
    internal_call_summaries: Optional[Dict[str, InternalCallSummary]] = None,
) -> PathQualifiedOrdering:
    """Compute path-qualified ordering between two operations using dominance analysis.

    This is the Phase 5.9 replacement for naive CFG ordering. It returns a
    PathQualifiedOrdering that indicates whether op_a is:
    - ALWAYS_BEFORE op_b (dominates)
    - SOMETIMES_BEFORE op_b (reachable but not dominating)
    - NEVER_BEFORE op_b (no path from a to b)
    - UNKNOWN (analysis incomplete)

    Args:
        op_a: First operation occurrence
        op_b: Second operation occurrence
        fn: Slither Function object containing the operations
        modifier_summaries: Optional precomputed modifier chain summaries
        internal_call_summaries: Optional cache of internal call summaries

    Returns:
        PathQualifiedOrdering with relation, confidence, and reason

    Example:
        >>> ordering = compute_path_qualified_ordering(external_call_op, write_op, fn)
        >>> if ordering.relation == OrderingRelation.ALWAYS_BEFORE:
        ...     print("External call always precedes write - vulnerable!")
    """
    # Create dominance analyzer for the function
    analyzer = create_analyzer_for_function(fn)
    if analyzer is None:
        return PathQualifiedOrdering(
            relation=OrderingRelation.UNKNOWN,
            confidence=0.0,
            reason="Could not create dominance analyzer for function",
        )

    # Check for modifier effects if not provided
    if modifier_summaries is None:
        modifiers = getattr(fn, "modifiers", []) or []
        if modifiers:
            modifier_summaries = compute_modifier_chain_dominance(modifiers)

    # If we have modifier summaries with external modifiers, we may need to emit UNKNOWN
    if modifier_summaries and modifier_summaries.any_external:
        # Check if ops involve modifier entry/exit operations
        a_in_modifier_entry = op_a.operation.name in modifier_summaries.combined_entry_ops
        b_in_modifier_exit = op_b.operation.name in modifier_summaries.combined_exit_ops

        if a_in_modifier_entry or b_in_modifier_exit:
            return PathQualifiedOrdering(
                relation=OrderingRelation.UNKNOWN,
                confidence=0.5,
                reason="External modifier body affects ordering",
            )

    # Compute dominance-based ordering
    node_a = op_a.cfg_order
    node_b = op_b.cfg_order

    ordering = analyzer.compute_ordering(node_a, node_b)

    # Enhance with evidence
    if ordering.evidence is None:
        evidence = {
            "op_a": {
                "name": op_a.operation.name,
                "cfg_order": op_a.cfg_order,
                "line": op_a.line_number,
            },
            "op_b": {
                "name": op_b.operation.name,
                "cfg_order": op_b.cfg_order,
                "line": op_b.line_number,
            },
        }
        return PathQualifiedOrdering(
            relation=ordering.relation,
            confidence=ordering.confidence,
            reason=ordering.reason,
            evidence=evidence,
        )

    return ordering


def compute_path_qualified_ordering_by_name(
    op_a_name: str,
    op_b_name: str,
    fn: Any,
) -> PathQualifiedOrdering:
    """Compute path-qualified ordering between operation types by name.

    This is a convenience function that finds the first occurrence of each
    operation type and computes their ordering.

    Args:
        op_a_name: Name of first operation (e.g., "CALLS_EXTERNAL")
        op_b_name: Name of second operation (e.g., "WRITES_USER_BALANCE")
        fn: Slither Function object

    Returns:
        PathQualifiedOrdering

    Note:
        If multiple occurrences exist, uses the first of each.
        For precise ordering with multiple occurrences, use compute_path_qualified_ordering().
    """
    occurrences = derive_all_operations(fn)

    op_a: Optional[OperationOccurrence] = None
    op_b: Optional[OperationOccurrence] = None

    for occ in occurrences:
        if op_a is None and occ.operation.name == op_a_name:
            op_a = occ
        if op_b is None and occ.operation.name == op_b_name:
            op_b = occ
        if op_a is not None and op_b is not None:
            break

    if op_a is None:
        return PathQualifiedOrdering(
            relation=OrderingRelation.UNKNOWN,
            confidence=0.0,
            reason=f"Operation {op_a_name} not found in function",
        )

    if op_b is None:
        return PathQualifiedOrdering(
            relation=OrderingRelation.UNKNOWN,
            confidence=0.0,
            reason=f"Operation {op_b_name} not found in function",
        )

    return compute_path_qualified_ordering(op_a, op_b, fn)


def get_all_path_qualified_orderings(
    fn: Any,
) -> List[Tuple[str, str, PathQualifiedOrdering]]:
    """Get all path-qualified ordering relationships in a function.

    This is the Phase 5.9 replacement for get_ordering_pairs() that includes
    full path qualification (ALWAYS/SOMETIMES/NEVER/UNKNOWN).

    Args:
        fn: Slither Function object

    Returns:
        List of (op_a_name, op_b_name, PathQualifiedOrdering) tuples

    Example:
        >>> orderings = get_all_path_qualified_orderings(fn)
        >>> for a, b, ordering in orderings:
        ...     if ordering.relation == OrderingRelation.ALWAYS_BEFORE:
        ...         print(f"{a} always before {b}")
    """
    occurrences = derive_all_operations(fn)
    if len(occurrences) < 2:
        return []

    # Create analyzer once
    analyzer = create_analyzer_for_function(fn)
    if analyzer is None:
        # Fall back to CFG order with UNKNOWN relation
        return [
            (
                occurrences[i].operation.name,
                occurrences[j].operation.name,
                PathQualifiedOrdering(
                    relation=OrderingRelation.UNKNOWN,
                    confidence=0.0,
                    reason="Could not create dominance analyzer",
                ),
            )
            for i in range(len(occurrences))
            for j in range(i + 1, len(occurrences))
        ]

    # Compute all orderings
    results: List[Tuple[str, str, PathQualifiedOrdering]] = []
    sorted_ops = sorted(occurrences, key=lambda x: x.cfg_order)

    for i, op_a in enumerate(sorted_ops):
        for op_b in sorted_ops[i + 1:]:
            ordering = analyzer.compute_ordering(op_a.cfg_order, op_b.cfg_order)
            results.append((op_a.operation.name, op_b.operation.name, ordering))

    return results


def has_path_qualified_ordering(
    fn: Any,
    before: str,
    after: str,
    relation: OrderingRelation = OrderingRelation.ALWAYS_BEFORE,
) -> bool:
    """Check if a specific path-qualified ordering exists.

    This is an enhanced version of has_ordering() that checks for specific
    ordering relations (ALWAYS_BEFORE, SOMETIMES_BEFORE, etc.).

    Args:
        fn: Slither Function object
        before: Operation name that should come first
        after: Operation name that should come after
        relation: Required ordering relation (default: ALWAYS_BEFORE)

    Returns:
        True if the specified ordering relation exists
    """
    ordering = compute_path_qualified_ordering_by_name(before, after, fn)
    return ordering.relation == relation


def detect_vulnerable_reentrancy_pattern_qualified(fn: Any) -> Tuple[bool, PathQualifiedOrdering]:
    """Detect vulnerable reentrancy with path qualification.

    Enhanced version of detect_vulnerable_reentrancy_pattern() that returns
    both the detection result and the dominance-based ordering.

    Args:
        fn: Slither Function object

    Returns:
        Tuple of (is_vulnerable, ordering)
        - is_vulnerable: True if external call ALWAYS_BEFORE or SOMETIMES_BEFORE write
        - ordering: The PathQualifiedOrdering result
    """
    external_ops = {"CALLS_EXTERNAL", "CALLS_UNTRUSTED", "TRANSFERS_VALUE_OUT"}
    balance_write_ops = {"WRITES_USER_BALANCE"}

    occurrences = derive_all_operations(fn)

    # Find external call and balance write
    external_op: Optional[OperationOccurrence] = None
    write_op: Optional[OperationOccurrence] = None

    for occ in occurrences:
        if external_op is None and occ.operation.name in external_ops:
            external_op = occ
        if write_op is None and occ.operation.name in balance_write_ops:
            write_op = occ

    if external_op is None or write_op is None:
        return False, PathQualifiedOrdering(
            relation=OrderingRelation.UNKNOWN,
            confidence=0.0,
            reason="Required operations not found",
        )

    ordering = compute_path_qualified_ordering(external_op, write_op, fn)

    # Vulnerable if external call is ALWAYS or SOMETIMES before write
    is_vulnerable = ordering.relation in (
        OrderingRelation.ALWAYS_BEFORE,
        OrderingRelation.SOMETIMES_BEFORE,
    )

    return is_vulnerable, ordering


def detect_cei_pattern_qualified(fn: Any) -> Tuple[bool, PathQualifiedOrdering]:
    """Detect CEI pattern with path qualification.

    Enhanced version of detect_cei_pattern() that uses dominance analysis.
    A function follows CEI if writes ALWAYS happen before external calls.

    Args:
        fn: Slither Function object

    Returns:
        Tuple of (follows_cei, ordering)
        - follows_cei: True if write ALWAYS_BEFORE external call
        - ordering: The PathQualifiedOrdering result
    """
    external_ops = {"CALLS_EXTERNAL", "CALLS_UNTRUSTED", "TRANSFERS_VALUE_OUT"}
    write_ops = {"WRITES_USER_BALANCE", "MODIFIES_CRITICAL_STATE"}

    occurrences = derive_all_operations(fn)

    # Find write and external call
    write_op: Optional[OperationOccurrence] = None
    external_op: Optional[OperationOccurrence] = None

    for occ in occurrences:
        if write_op is None and occ.operation.name in write_ops:
            write_op = occ
        if external_op is None and occ.operation.name in external_ops:
            external_op = occ

    if write_op is None or external_op is None:
        # No writes or no external calls = safe
        return True, PathQualifiedOrdering(
            relation=OrderingRelation.UNKNOWN,
            confidence=1.0,
            reason="Required operations not found - safe by default",
        )

    ordering = compute_path_qualified_ordering(write_op, external_op, fn)

    # CEI requires write ALWAYS before external call
    follows_cei = ordering.relation == OrderingRelation.ALWAYS_BEFORE

    return follows_cei, ordering


def get_interprocedural_ordering_context(fn: Any) -> Dict[str, Any]:
    """Get interprocedural ordering context including modifiers and internal calls.

    This function builds a comprehensive ordering context for a function,
    including modifier chain summaries and internal call summaries.

    Args:
        fn: Slither Function object

    Returns:
        Dictionary with:
        - modifier_chain: ModifierChainSummary if modifiers present
        - internal_calls: Dict of function name -> InternalCallSummary
        - has_external_modifiers: Whether any modifier body is unavailable
        - dominance_intact: Whether full dominance chain can be computed
    """
    result: Dict[str, Any] = {
        "modifier_chain": None,
        "internal_calls": {},
        "has_external_modifiers": False,
        "dominance_intact": True,
    }

    # Process modifiers
    modifiers = getattr(fn, "modifiers", []) or []
    if modifiers:
        chain = compute_modifier_chain_dominance(modifiers)
        result["modifier_chain"] = chain.to_dict()
        result["has_external_modifiers"] = chain.any_external
        if chain.any_external:
            result["dominance_intact"] = False

    # Process internal calls
    internal_calls_attr = getattr(fn, "internal_calls", []) or []
    for call in internal_calls_attr:
        callee = getattr(call, "function", None)
        if callee is None:
            continue

        callee_name = getattr(callee, "name", "") or "unknown"
        summary = compute_internal_call_summary(callee)
        result["internal_calls"][callee_name] = summary.to_dict()

        if not summary.summary_available:
            result["dominance_intact"] = False

    return result


# Re-export key types and functions for convenience
__all__ = [
    # Original Phase 2 exports
    "OrderedOperation",
    "extract_operation_sequence",
    "get_operation_sequence_data",
    "get_ordering_pairs",
    "has_ordering",
    "detect_vulnerable_reentrancy_pattern",
    "detect_cei_pattern",
    "compute_signature_from_fn",
    # Re-exports from operations
    "SemanticOperation",
    "OperationOccurrence",
    "OP_CODES",
    "derive_all_operations",
    "compute_behavioral_signature",
    "compute_ordering_pairs",
    # Phase 5.9: Dominance-based ordering
    "DominanceAnalyzer",
    "OrderingRelation",
    "PathQualifiedOrdering",
    "ModifierSummary",
    "ModifierChainSummary",
    "InternalCallSummary",
    "compute_path_qualified_ordering",
    "compute_path_qualified_ordering_by_name",
    "get_all_path_qualified_orderings",
    "has_path_qualified_ordering",
    "detect_vulnerable_reentrancy_pattern_qualified",
    "detect_cei_pattern_qualified",
    "get_interprocedural_ordering_context",
]
