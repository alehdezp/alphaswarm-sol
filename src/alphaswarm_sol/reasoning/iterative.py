"""
P3-T1: Iterative Reasoning Engine (MVP)

ToG-2 style iterative retrieval for vulnerability detection.
Multi-round reasoning discovers attack chains that single-pass analysis misses.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.kg.graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class ExpansionType(Enum):
    """Types of graph expansion."""

    CALLERS = "callers"  # Functions that call this
    CALLEES = "callees"  # Functions this calls
    SHARED_STATE = "shared_state"  # Functions accessing same state
    INHERITANCE = "inheritance"  # Parent/child contracts
    CROSS_CONTRACT = "cross_contract"  # External contract calls


@dataclass
class ExpandedNode:
    """A node discovered through expansion."""

    node_id: str
    expansion_type: ExpansionType
    source_node: str  # Which candidate led to this
    hop_distance: int  # Distance from original candidates
    relevance_score: float  # How relevant to the analysis


@dataclass
class CrossGraphFinding:
    """A finding from cross-graph query."""

    source_node: str
    target_kg: str  # "domain", "adversarial"
    edge_type: str  # "IMPLEMENTS", "VIOLATES", "SIMILAR_TO"
    target_spec_or_pattern: str
    confidence: float
    evidence: List[str] = field(default_factory=list)


@dataclass
class AttackChain:
    """A multi-function attack sequence."""

    id: str
    functions: List[str]  # Ordered function sequence
    entry_point: str
    exit_point: str

    # Attack details
    pattern_ids: List[str]  # Patterns involved
    description: str

    # Scoring
    feasibility: float
    impact: str  # "critical", "high", "medium"

    # Fields with defaults must come last
    preconditions: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    cross_graph_support: List[CrossGraphFinding] = field(default_factory=list)


@dataclass
class ReasoningRound:
    """One round of iterative reasoning."""

    round_num: int

    # Input to this round
    input_candidates: List[str]

    # Pattern matching results
    pattern_matches: Dict[str, List[Tuple[str, float]]]  # node_id -> [(pattern_id, confidence)]

    # Expansion results
    expanded_nodes: List[ExpandedNode]

    # Cross-graph results
    cross_graph_findings: List[CrossGraphFinding]

    # Output of this round
    refined_candidates: List[str]
    attack_chains_discovered: List[AttackChain]

    # Metrics
    new_candidates_added: int
    candidates_removed: int
    expansion_time_ms: float
    cross_graph_time_ms: float


@dataclass
class ReasoningResult:
    """Complete result of iterative reasoning."""

    rounds: List[ReasoningRound]

    # Final outputs
    final_candidates: List[str]
    attack_chains: List[AttackChain]
    all_cross_graph_findings: List[CrossGraphFinding]

    # Convergence info
    converged: bool
    convergence_round: int
    convergence_reason: str  # "no_new_candidates", "max_rounds", "threshold"

    # Metrics
    total_time_ms: float
    total_nodes_explored: int
    total_cross_graph_queries: int

    # Comparison with single-pass
    single_pass_would_find: List[str]  # What single-pass would catch
    iterative_bonus_findings: List[str]  # What only iterative found


class IterativeReasoningEngine:
    """
    ToG-2 style iterative retrieval for vulnerability detection.

    Key innovation: Multi-round reasoning with graph expansion
    discovers attack chains that single-pass analysis misses.

    MVP Scope:
    - Multi-round expansion (callers, callees, shared state)
    - Convergence detection
    - Attack chain discovery
    - Comparison with single-pass baseline
    """

    def __init__(
        self,
        code_kg: "KnowledgeGraph",
        max_rounds: int = 4,
        convergence_threshold: float = 0.9,
        expansion_limit: int = 20,
        min_confidence: float = 0.3,
    ):
        """
        Initialize iterative reasoning engine.

        Args:
            code_kg: Knowledge graph to analyze
            max_rounds: Maximum reasoning rounds
            convergence_threshold: Stop if this % of candidates unchanged
            expansion_limit: Max new nodes per round
            min_confidence: Min confidence to keep candidate
        """
        self.code_kg = code_kg
        self.max_rounds = max_rounds
        self.convergence_threshold = convergence_threshold
        self.expansion_limit = expansion_limit
        self.min_confidence = min_confidence
        self.logger = logging.getLogger(__name__)

    def reason(
        self,
        initial_candidates: List[str],
        max_rounds: Optional[int] = None,
    ) -> ReasoningResult:
        """
        Iterative reasoning to find vulnerabilities.

        Args:
            initial_candidates: Starting function node IDs
            max_rounds: Override default max rounds

        Returns:
            ReasoningResult with all rounds, findings, and chains
        """
        start_time = time.time()

        rounds = []
        candidates = set(initial_candidates)
        all_explored = set(initial_candidates)
        all_cross_findings: List[CrossGraphFinding] = []
        all_chains: List[AttackChain] = []

        max_r = max_rounds or self.max_rounds

        for round_num in range(1, max_r + 1):
            self.logger.info(f"Round {round_num}: {len(candidates)} candidates")

            # Step 1: Pattern match on current candidates
            pattern_matches = self._pattern_match(candidates)

            # Step 2: Expand to neighbors
            expand_start = time.time()
            expanded = self._expand_neighbors(candidates, all_explored)
            expand_time = (time.time() - expand_start) * 1000

            # Step 3: Query cross-graphs (MVP: placeholder)
            cross_start = time.time()
            cross_findings = self._query_cross_graphs(candidates, expanded)
            cross_time = (time.time() - cross_start) * 1000
            all_cross_findings.extend(cross_findings)

            # Step 4: Build attack chains
            new_chains = self._build_attack_chains(candidates, expanded, pattern_matches)
            all_chains.extend(new_chains)

            # Step 5: Refine candidates
            old_candidates = candidates.copy()
            candidates = self._refine_candidates(
                candidates,
                expanded,
                cross_findings,
                pattern_matches,
            )

            # Track exploration
            all_explored.update(e.node_id for e in expanded)

            # Build round record
            new_count = len(candidates - old_candidates)
            removed_count = len(old_candidates - candidates)

            round_record = ReasoningRound(
                round_num=round_num,
                input_candidates=list(old_candidates),
                pattern_matches=pattern_matches,
                expanded_nodes=expanded,
                cross_graph_findings=cross_findings,
                refined_candidates=list(candidates),
                attack_chains_discovered=new_chains,
                new_candidates_added=new_count,
                candidates_removed=removed_count,
                expansion_time_ms=expand_time,
                cross_graph_time_ms=cross_time,
            )
            rounds.append(round_record)

            # Check convergence
            if self._converged(rounds):
                convergence_reason = "no_new_candidates"
                break
        else:
            convergence_reason = "max_rounds"

        total_time = (time.time() - start_time) * 1000

        # Compare with single-pass
        single_pass = self._single_pass_simulation(initial_candidates)
        iterative_bonus = list(candidates - set(single_pass))

        return ReasoningResult(
            rounds=rounds,
            final_candidates=list(candidates),
            attack_chains=all_chains,
            all_cross_graph_findings=all_cross_findings,
            converged=convergence_reason != "max_rounds",
            convergence_round=len(rounds),
            convergence_reason=convergence_reason,
            total_time_ms=total_time,
            total_nodes_explored=len(all_explored),
            total_cross_graph_queries=len(all_cross_findings),
            single_pass_would_find=single_pass,
            iterative_bonus_findings=iterative_bonus,
        )

    def _pattern_match(
        self, candidates: Set[str]
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Match patterns against current candidates.

        MVP: Uses node properties to detect vulnerability patterns.
        """
        matches = {}

        for node_id in candidates:
            node = self.code_kg.nodes.get(node_id)
            if not node or node.type.value != "function":
                continue

            props = node.properties
            node_matches = []

            # Reentrancy detection
            if props.get("state_write_after_external_call"):
                if not props.get("has_reentrancy_guard"):
                    node_matches.append(("reentrancy_classic", 0.85))

            # Access control
            if props.get("writes_privileged_state"):
                if not props.get("has_access_gate"):
                    node_matches.append(("weak_access_control", 0.80))

            # DoS unbounded loop
            if props.get("has_unbounded_loop"):
                if props.get("external_calls_in_loop"):
                    node_matches.append(("dos_unbounded_loop", 0.75))

            # MEV missing slippage
            if props.get("swap_like"):
                if props.get("risk_missing_slippage_parameter"):
                    node_matches.append(("mev_missing_slippage", 0.70))

            if node_matches:
                matches[node_id] = node_matches

        return matches

    def _expand_neighbors(
        self,
        candidates: Set[str],
        already_explored: Set[str],
    ) -> List[ExpandedNode]:
        """
        Expand to neighboring nodes not yet explored.

        Priority order:
        1. Shared state (highest risk)
        2. Callers (entry points)
        3. Callees (propagation)
        """
        expanded = []

        for node_id in candidates:
            node = self.code_kg.nodes.get(node_id)
            if not node:
                continue

            # Priority 1: Shared state
            shared = self._get_shared_state_functions(node_id)
            for fn_id in shared:
                if fn_id not in already_explored and fn_id not in candidates:
                    expanded.append(
                        ExpandedNode(
                            node_id=fn_id,
                            expansion_type=ExpansionType.SHARED_STATE,
                            source_node=node_id,
                            hop_distance=1,
                            relevance_score=0.9,
                        )
                    )

            # Priority 2: Callers
            callers = self._get_callers(node_id)
            for fn_id in callers:
                if fn_id not in already_explored and fn_id not in candidates:
                    expanded.append(
                        ExpandedNode(
                            node_id=fn_id,
                            expansion_type=ExpansionType.CALLERS,
                            source_node=node_id,
                            hop_distance=1,
                            relevance_score=0.7,
                        )
                    )

            # Priority 3: Callees
            callees = self._get_callees(node_id)
            for fn_id in callees:
                if fn_id not in already_explored and fn_id not in candidates:
                    expanded.append(
                        ExpandedNode(
                            node_id=fn_id,
                            expansion_type=ExpansionType.CALLEES,
                            source_node=node_id,
                            hop_distance=1,
                            relevance_score=0.6,
                        )
                    )

        # Sort by relevance and limit
        expanded.sort(key=lambda e: -e.relevance_score)
        return expanded[: self.expansion_limit]

    def _get_shared_state_functions(self, node_id: str) -> List[str]:
        """Get functions that access the same state variables."""
        node = self.code_kg.nodes.get(node_id)
        if not node:
            return []

        # Get state variables this function accesses
        written_state = set(node.properties.get("writes_state_vars", []))
        read_state = set(node.properties.get("reads_state_vars", []))
        all_state = written_state | read_state

        if not all_state:
            return []

        # Find other functions accessing same state
        shared_funcs = []
        for other_id, other_node in self.code_kg.nodes.items():
            if other_id == node_id or other_node.type.value != "function":
                continue

            other_written = set(other_node.properties.get("writes_state_vars", []))
            other_read = set(other_node.properties.get("reads_state_vars", []))
            other_state = other_written | other_read

            # Check for overlap
            if all_state & other_state:
                shared_funcs.append(other_id)

        return shared_funcs

    def _get_callers(self, node_id: str) -> List[str]:
        """Get functions that call this function."""
        callers = []

        for edge in self.code_kg.edges.values():
            if edge.target == node_id and edge.type.value == "calls":
                if edge.source not in callers:
                    callers.append(edge.source)

        return callers

    def _get_callees(self, node_id: str) -> List[str]:
        """Get functions called by this function."""
        callees = []

        for edge in self.code_kg.edges.values():
            if edge.source == node_id and edge.type.value == "calls":
                if edge.target not in callees:
                    callees.append(edge.target)

        return callees

    def _query_cross_graphs(
        self,
        candidates: Set[str],
        expanded: List[ExpandedNode],
    ) -> List[CrossGraphFinding]:
        """
        Query cross-graphs for additional context.

        MVP: Placeholder - returns empty list.
        Full implementation would query domain/adversarial KGs.
        """
        # MVP: Return empty - cross-KG integration is future work
        return []

    def _build_attack_chains(
        self,
        candidates: Set[str],
        expanded: List[ExpandedNode],
        pattern_matches: Dict[str, List[Tuple[str, float]]],
    ) -> List[AttackChain]:
        """
        Build multi-function attack chains.

        Identifies sequences of functions that together enable an attack.
        """
        chains = []

        # Find reentrancy chains (entry → vulnerable → reentry)
        for node_id in candidates:
            if node_id not in pattern_matches:
                continue

            matches = pattern_matches[node_id]
            has_reentrancy = any(p_id == "reentrancy_classic" for p_id, _ in matches)

            if has_reentrancy:
                # Find callers as entry points
                callers = [
                    e.node_id
                    for e in expanded
                    if e.source_node == node_id
                    and e.expansion_type == ExpansionType.CALLERS
                ]

                for caller_id in callers:
                    chain = AttackChain(
                        id=f"chain_{len(chains)+1}",
                        functions=[caller_id, node_id, caller_id],  # Reentry pattern
                        entry_point=caller_id,
                        exit_point=caller_id,
                        pattern_ids=["reentrancy_classic"],
                        description=f"Reentrancy attack: {caller_id} → {node_id} → {caller_id}",
                        feasibility=0.8,
                        impact="critical",
                        evidence=[
                            f"{node_id} has state write after external call",
                            f"{caller_id} can trigger the vulnerable function",
                        ],
                    )
                    chains.append(chain)

        return chains

    def _refine_candidates(
        self,
        current_candidates: Set[str],
        expanded: List[ExpandedNode],
        cross_findings: List[CrossGraphFinding],
        pattern_matches: Dict[str, List[Tuple[str, float]]],
    ) -> Set[str]:
        """
        Refine candidate set based on evidence.

        Add high-relevance expanded nodes.
        Remove low-confidence candidates.
        """
        refined = current_candidates.copy()

        # Add high-relevance expanded nodes
        for exp_node in expanded:
            if exp_node.relevance_score >= 0.7:
                refined.add(exp_node.node_id)

        # Keep only candidates with pattern matches or high relevance
        to_keep = set()
        for candidate in refined:
            # Keep if has pattern match
            if candidate in pattern_matches:
                to_keep.add(candidate)
                continue

            # Keep if expanded from high-confidence match
            source_match = any(
                e.source_node in pattern_matches
                for e in expanded
                if e.node_id == candidate and e.relevance_score >= 0.7
            )
            if source_match:
                to_keep.add(candidate)

        return to_keep if to_keep else refined  # Fallback to refined if nothing kept

    def _converged(self, rounds: List[ReasoningRound]) -> bool:
        """
        Check if reasoning has converged.

        Convergence criteria:
        - No new candidates added in last round
        - Candidate set unchanged from previous round
        """
        if len(rounds) < 2:
            return False

        last_round = rounds[-1]

        # No new candidates added
        if last_round.new_candidates_added == 0:
            return True

        # Candidate set size stable
        if len(rounds) >= 2:
            prev_size = len(rounds[-2].refined_candidates)
            curr_size = len(last_round.refined_candidates)
            if prev_size == curr_size and last_round.new_candidates_added == 0:
                return True

        return False

    def _single_pass_simulation(self, initial_candidates: List[str]) -> List[str]:
        """
        Simulate what single-pass analysis would find.

        Single-pass = pattern match on initial candidates only.
        """
        single_pass = []

        for node_id in initial_candidates:
            node = self.code_kg.nodes.get(node_id)
            if not node or node.type.value != "function":
                continue

            props = node.properties

            # Check for obvious vulnerabilities
            if (
                props.get("state_write_after_external_call")
                and not props.get("has_reentrancy_guard")
            ) or (
                props.get("writes_privileged_state")
                and not props.get("has_access_gate")
            ):
                single_pass.append(node_id)

        return single_pass
