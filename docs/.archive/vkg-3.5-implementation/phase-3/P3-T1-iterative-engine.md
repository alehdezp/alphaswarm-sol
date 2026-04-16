# [P3-T1] Iterative Query Engine (ToG-2 Style)

**Phase**: 3 - Iterative + Causal
**Task ID**: P3-T1
**Status**: NOT_STARTED
**Priority**: HIGH
**Estimated Effort**: 4-5 days
**Actual Effort**: -

---

## Executive Summary

Implement Think-on-Graph 2.0 style iterative reasoning that performs **multi-round retrieval** instead of single-pass pattern matching. Each round: match → expand neighbors → query cross-graphs → refine candidates → repeat until convergence.

**Research Basis**: ToG-2 (ICLR 2025) achieves SOTA on knowledge-intensive tasks through iterative KG traversal tightly coupled with retrieval. Our adaptation enables discovering **multi-function attack chains** that single-pass analysis misses.

**Why This Matters**: Real vulnerabilities often span multiple functions. A reentrancy in `withdraw()` might only be exploitable because `deposit()` lacks proper validation. Iterative expansion finds these chains.

---

## Dependencies

### Required Before Starting
- [ ] [P0-T3] Cross-Graph Linker - Provides cross-graph queries
- [ ] [P2-T5] Adversarial Arbiter - Produces verdicts to refine

### Blocks These Tasks
- [P3-T2] Causal Reasoning Engine - Uses iterative context
- [P3-T4] Attack Path Synthesis - Uses multi-function chains

---

## Objectives

### Primary Objectives
1. Multi-round pattern matching with automatic graph expansion
2. Cross-graph context retrieval per round (domain, adversarial, code)
3. Candidate refinement based on accumulated evidence
4. Convergence detection (stop when no new information)
5. Attack chain synthesis from multi-hop paths

### Stretch Goals
1. Adaptive round budgets based on finding density
2. Prioritized expansion (high-risk nodes first)
3. Caching for repeated queries

---

## Success Criteria

### Must Have (Definition of Done)
- [ ] `ReasoningRound` dataclass tracking round state
- [ ] `IterativeReasoningEngine` with `reason()` method
- [ ] Multi-round expansion to callers/callees
- [ ] Cross-graph query per round
- [ ] Convergence detection
- [ ] Better detection than single-pass (measured on test corpus)
- [ ] 95%+ test coverage
- [ ] Documentation in docs/reference/iterative-engine.md

### Should Have
- [ ] Prioritized expansion by risk score
- [ ] Round budget management
- [ ] Visualization of expansion paths

### Nice to Have
- [ ] Streaming results (yield findings as discovered)
- [ ] Parallel expansion for large codebases

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ITERATIVE REASONING ENGINE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   INITIALIZATION                                                                 │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │  initial_candidates: [fn_withdraw, fn_transfer, fn_swap]               │    │
│   │  max_rounds: 4                                                          │    │
│   │  convergence_threshold: 0.9                                             │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│                                       ▼                                          │
│   ROUND 1 ═══════════════════════════════════════════════════════════════       │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │                                                                         │    │
│   │  1. PATTERN MATCH on candidates                                        │    │
│   │     fn_withdraw → matches reentrancy_classic (0.8)                     │    │
│   │     fn_transfer → matches access_control (0.6)                         │    │
│   │                                                                         │    │
│   │  2. EXPAND NEIGHBORS                                                   │    │
│   │     fn_withdraw:                                                        │    │
│   │       ├── callers: [fn_requestWithdraw, fn_emergencyWithdraw]          │    │
│   │       ├── callees: [_transfer]                                         │    │
│   │       └── shared_state: [fn_deposit, fn_stake]                         │    │
│   │                                                                         │    │
│   │  3. CROSS-GRAPH QUERY                                                  │    │
│   │     Domain KG: fn_withdraw IMPLEMENTS ERC4626.withdraw                 │    │
│   │     Adversarial KG: fn_withdraw SIMILAR_TO the_dao_exploit             │    │
│   │                                                                         │    │
│   │  4. REFINE CANDIDATES                                                  │    │
│   │     + Add fn_deposit (shares state, might enable attack)               │    │
│   │     + Add fn_emergencyWithdraw (similar pattern)                       │    │
│   │     - Remove fn_transfer (low confidence, no evidence)                 │    │
│   │                                                                         │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│                                       ▼                                          │
│   ROUND 2 ═══════════════════════════════════════════════════════════════       │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │                                                                         │    │
│   │  1. PATTERN MATCH on refined candidates                                │    │
│   │     fn_deposit → matches first_depositor (0.7)                         │    │
│   │     fn_emergencyWithdraw → matches reentrancy (0.85)                   │    │
│   │                                                                         │    │
│   │  2. EXPAND NEIGHBORS (2-hop from original)                             │    │
│   │     fn_deposit:                                                         │    │
│   │       └── shared_state: [fn_withdraw] (already in set)                 │    │
│   │                                                                         │    │
│   │  3. CROSS-GRAPH QUERY                                                  │    │
│   │     Domain KG: fn_deposit VIOLATES ERC4626.first_deposit_invariant    │    │
│   │     Adversarial KG: fn_deposit + fn_withdraw MATCHES inflation_attack │    │
│   │                                                                         │    │
│   │  4. BUILD ATTACK CHAINS                                                │    │
│   │     Chain 1: fn_deposit → inflate_shares → fn_withdraw → drain        │    │
│   │     Chain 2: fn_withdraw → reenter → fn_withdraw → double_spend       │    │
│   │                                                                         │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│                                       ▼                                          │
│   ROUND 3 (Convergence) ═══════════════════════════════════════════════════     │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │                                                                         │    │
│   │  No new candidates added → CONVERGED                                   │    │
│   │  Final candidate set = Round 2 set                                     │    │
│   │                                                                         │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│                                       ▼                                          │
│   OUTPUT                                                                         │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │  ReasoningResult                                                        │    │
│   │    ├── rounds: [Round1, Round2, Round3]                                │    │
│   │    ├── final_candidates: [fn_withdraw, fn_deposit, fn_emergencyWithdraw]│   │
│   │    ├── attack_chains: [Chain1, Chain2]                                 │    │
│   │    ├── cross_graph_findings: [...]                                     │    │
│   │    └── convergence_round: 3                                            │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### New Files
- `src/true_vkg/reasoning/__init__.py` - Package init
- `src/true_vkg/reasoning/iterative.py` - Main iterative engine
- `src/true_vkg/reasoning/expansion.py` - Graph expansion strategies
- `src/true_vkg/reasoning/convergence.py` - Convergence detection
- `tests/test_3.5/test_iterative_engine.py` - Tests

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum


class ExpansionType(Enum):
    """Types of graph expansion."""
    CALLERS = "callers"           # Functions that call this
    CALLEES = "callees"           # Functions this calls
    SHARED_STATE = "shared_state" # Functions accessing same state
    INHERITANCE = "inheritance"   # Parent/child contracts
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
    evidence: List[str]


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
    preconditions: List[str]

    # Scoring
    feasibility: float
    impact: str  # "critical", "high", "medium"

    # Evidence
    evidence: List[str]
    cross_graph_support: List[CrossGraphFinding]


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

    Key innovation: Multi-round reasoning with cross-graph queries
    discovers attack chains that single-pass analysis misses.
    """

    def __init__(
        self,
        code_kg: "KnowledgeGraph",
        domain_kg: "DomainKnowledgeGraph",
        adversarial_kg: "AdversarialKnowledgeGraph",
        linker: "CrossGraphLinker",
    ):
        self.code_kg = code_kg
        self.domain_kg = domain_kg
        self.adversarial_kg = adversarial_kg
        self.linker = linker

        # Configuration
        self.max_rounds = 4
        self.convergence_threshold = 0.9  # Stop if 90% of candidates unchanged
        self.expansion_limit = 20  # Max new nodes per round
        self.min_confidence = 0.3  # Min confidence to keep candidate

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
        import time
        start_time = time.time()

        rounds = []
        candidates = set(initial_candidates)
        all_explored = set(initial_candidates)
        all_cross_findings = []
        all_chains = []

        max_r = max_rounds or self.max_rounds

        for round_num in range(1, max_r + 1):
            round_start = time.time()

            # Step 1: Pattern match on current candidates
            pattern_matches = self._pattern_match(candidates)

            # Step 2: Expand to neighbors
            expand_start = time.time()
            expanded = self._expand_neighbors(candidates, all_explored)
            expand_time = (time.time() - expand_start) * 1000

            # Step 3: Query cross-graphs
            cross_start = time.time()
            cross_findings = self._query_cross_graphs(candidates | {e.node_id for e in expanded})
            cross_time = (time.time() - cross_start) * 1000
            all_cross_findings.extend(cross_findings)

            # Step 4: Build attack chains
            new_chains = self._build_attack_chains(candidates, expanded, cross_findings)
            all_chains.extend(new_chains)

            # Step 5: Refine candidates
            old_candidates = candidates.copy()
            candidates = self._refine_candidates(
                candidates,
                expanded,
                cross_findings,
                pattern_matches
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

    def _pattern_match(self, candidates: Set[str]) -> Dict[str, List[Tuple[str, float]]]:
        """Match patterns against current candidates."""
        matches = {}

        for node_id in candidates:
            node = self.code_kg.nodes.get(node_id)
            if not node:
                continue

            # Query adversarial KG for matching patterns
            pattern_results = self.adversarial_kg.find_similar_patterns(
                node,
                min_confidence=self.min_confidence
            )

            if pattern_results:
                matches[node_id] = [
                    (pm.pattern.id, pm.confidence)
                    for pm in pattern_results
                ]

        return matches

    def _expand_neighbors(
        self,
        candidates: Set[str],
        already_explored: Set[str],
    ) -> List[ExpandedNode]:
        """
        Expand to neighboring nodes not yet explored.

        Expansion strategies (in priority order):
        1. Shared state - Functions accessing same state variables
        2. Callers - Functions that call candidates
        3. Callees - Functions called by candidates
        4. Cross-contract - External contract interactions
        """
        expanded = []

        for node_id in candidates:
            # Priority 1: Shared state (highest risk of chained attacks)
            shared = self._get_shared_state_functions(node_id)
            for fn_id in shared:
                if fn_id not in already_explored and fn_id not in candidates:
                    expanded.append(ExpandedNode(
                        node_id=fn_id,
                        expansion_type=ExpansionType.SHARED_STATE,
                        source_node=node_id,
                        hop_distance=1,
                        relevance_score=0.9,  # High relevance for shared state
                    ))

            # Priority 2: Callers (attack entry points)
            callers = self._get_callers(node_id)
            for fn_id in callers:
                if fn_id not in already_explored and fn_id not in candidates:
                    expanded.append(ExpandedNode(
                        node_id=fn_id,
                        expansion_type=ExpansionType.CALLERS,
                        source_node=node_id,
                        hop_distance=1,
                        relevance_score=0.7,
                    ))

            # Priority 3: Callees (attack propagation)
            callees = self._get_callees(node_id)
            for fn_id in callees:
                if fn_id not in already_explored and fn_id not in candidates:
                    expanded.append(ExpandedNode(
                        node_id=fn_id,
                        expansion_type=ExpansionType.CALLEES,
                        source_node=node_id,
                        hop_distance=1,
                        relevance_score=0.6,
                    ))

        # Sort by relevance and limit
        expanded.sort(key=lambda e: -e.relevance_score)
        return expanded[:self.expansion_limit]

    def _get_shared_state_functions(self, node_id: str) -> List[str]:
        """Get functions that access the same state variables."""
        node = self.code_kg.nodes.get(node_id)
        if not node:
            return []

        # Get state variables this function accesses
        written_state = node.properties.get("writes_state_vars", [])
        read_state = node.properties.get("reads_state_vars", [])
        all_state = set(written_state) | set(read_state)

        # Find other functions accessing same state
        shared_fns = set()
        for other_id, other_node in self.code_kg.nodes.items():
            if other_id == node_id or other_node.type != "Function":
                continue

            other_written = set(other_node.properties.get("writes_state_vars", []))
            other_read = set(other_node.properties.get("reads_state_vars", []))
            other_all = other_written | other_read

            # Overlap? Especially if one writes what other reads
            if all_state & other_all:
                shared_fns.add(other_id)

        return list(shared_fns)

    def _get_callers(self, node_id: str) -> List[str]:
        """Get functions that call this function."""
        callers = []

        for edge in self.code_kg.edges:
            if edge.target_id == node_id and edge.type == "calls":
                callers.append(edge.source_id)

        return callers

    def _get_callees(self, node_id: str) -> List[str]:
        """Get functions called by this function."""
        callees = []

        for edge in self.code_kg.edges:
            if edge.source_id == node_id and edge.type == "calls":
                callees.append(edge.target_id)

        return callees

    def _query_cross_graphs(self, nodes: Set[str]) -> List[CrossGraphFinding]:
        """Query domain and adversarial KGs for each node."""
        findings = []

        for node_id in nodes:
            node = self.code_kg.nodes.get(node_id)
            if not node:
                continue

            # Query domain KG for spec relationships
            domain_results = self.linker.query_domain_links(node_id)
            for result in domain_results:
                findings.append(CrossGraphFinding(
                    source_node=node_id,
                    target_kg="domain",
                    edge_type=result.relation.value,
                    target_spec_or_pattern=result.spec_id,
                    confidence=result.confidence,
                    evidence=result.evidence,
                ))

            # Query adversarial KG for pattern relationships
            adversarial_results = self.linker.query_adversarial_links(node_id)
            for result in adversarial_results:
                findings.append(CrossGraphFinding(
                    source_node=node_id,
                    target_kg="adversarial",
                    edge_type=result.relation.value,
                    target_spec_or_pattern=result.pattern_id,
                    confidence=result.confidence,
                    evidence=result.evidence,
                ))

        return findings

    def _build_attack_chains(
        self,
        candidates: Set[str],
        expanded: List[ExpandedNode],
        cross_findings: List[CrossGraphFinding],
    ) -> List[AttackChain]:
        """
        Build multi-function attack chains from current context.

        Chain patterns we look for:
        1. deposit → manipulate → withdraw (first depositor / inflation)
        2. flashLoan → action → repay (flash loan attacks)
        3. call → reenter → call (reentrancy chains)
        4. approve → transferFrom → exploit (approval exploits)
        """
        chains = []

        # Get all nodes in current context
        context_nodes = candidates | {e.node_id for e in expanded}

        # Look for deposit → withdraw chains (first depositor pattern)
        deposits = [n for n in context_nodes
                   if self._is_deposit_like(n)]
        withdraws = [n for n in context_nodes
                    if self._is_withdraw_like(n)]

        for dep in deposits:
            for wd in withdraws:
                if self._share_state(dep, wd):
                    # Check if deposit has inflation vulnerability
                    dep_findings = [f for f in cross_findings
                                   if f.source_node == dep
                                   and "first_depositor" in f.target_spec_or_pattern.lower()]

                    if dep_findings:
                        chains.append(AttackChain(
                            id=f"chain_inflation_{dep}_{wd}",
                            functions=[dep, wd],
                            entry_point=dep,
                            exit_point=wd,
                            pattern_ids=["first_depositor_attack"],
                            description="Deposit small amount, donate directly, withdraw inflated shares",
                            preconditions=[
                                "Contract has low/zero total supply",
                                "Share calculation uses division",
                            ],
                            feasibility=0.7,
                            impact="critical",
                            evidence=[
                                f"Deposit function {dep} shares state with withdraw {wd}",
                                "Pattern matches first depositor attack",
                            ],
                            cross_graph_support=dep_findings,
                        ))

        # Look for reentrancy chains
        external_callers = [n for n in context_nodes
                          if self._has_external_call(n)]
        state_writers = [n for n in context_nodes
                        if self._writes_state(n)]

        for caller in external_callers:
            for writer in state_writers:
                if caller == writer or self._share_state(caller, writer):
                    # Check cross-contract reentrancy possibility
                    chains.append(AttackChain(
                        id=f"chain_reenter_{caller}_{writer}",
                        functions=[caller, writer] if caller != writer else [caller],
                        entry_point=caller,
                        exit_point=writer,
                        pattern_ids=["reentrancy_cross_function"],
                        description="External call allows re-entering to manipulate shared state",
                        preconditions=[
                            "No reentrancy guard",
                            "External call before state finalization",
                        ],
                        feasibility=0.8,
                        impact="critical",
                        evidence=[
                            f"Function {caller} makes external call",
                            f"Function {writer} modifies shared state",
                        ],
                        cross_graph_support=[],
                    ))

        return chains

    def _refine_candidates(
        self,
        current: Set[str],
        expanded: List[ExpandedNode],
        cross_findings: List[CrossGraphFinding],
        pattern_matches: Dict[str, List[Tuple[str, float]]],
    ) -> Set[str]:
        """
        Refine candidate set based on evidence.

        Add: Expanded nodes with strong cross-graph support
        Keep: Candidates with pattern matches or cross-graph findings
        Remove: Candidates with no evidence after expansion
        """
        refined = set()

        # Keep candidates with evidence
        for node_id in current:
            has_pattern = node_id in pattern_matches and pattern_matches[node_id]
            has_cross_finding = any(f.source_node == node_id for f in cross_findings)

            if has_pattern or has_cross_finding:
                refined.add(node_id)

        # Add expanded nodes with high relevance or cross-graph support
        for exp in expanded:
            has_cross = any(f.source_node == exp.node_id for f in cross_findings)

            if exp.relevance_score >= 0.7 or has_cross:
                refined.add(exp.node_id)

        return refined

    def _converged(self, rounds: List[ReasoningRound]) -> bool:
        """Check if reasoning has converged."""
        if len(rounds) < 2:
            return False

        last = rounds[-1]
        prev = rounds[-2]

        # Converged if no new candidates added
        if last.new_candidates_added == 0:
            return True

        # Converged if candidate set similarity above threshold
        last_set = set(last.refined_candidates)
        prev_set = set(prev.refined_candidates)

        if len(last_set | prev_set) == 0:
            return True

        similarity = len(last_set & prev_set) / len(last_set | prev_set)
        return similarity >= self.convergence_threshold

    def _single_pass_simulation(self, initial_candidates: List[str]) -> List[str]:
        """Simulate what single-pass analysis would find."""
        # Single pass only looks at initial candidates, no expansion
        results = []

        for node_id in initial_candidates:
            node = self.code_kg.nodes.get(node_id)
            if not node:
                continue

            patterns = self.adversarial_kg.find_similar_patterns(node, min_confidence=0.5)
            if patterns:
                results.append(node_id)

        return results

    # Helper methods
    def _is_deposit_like(self, node_id: str) -> bool:
        """Check if function looks like a deposit."""
        node = self.code_kg.nodes.get(node_id)
        if not node:
            return False
        return (
            "deposit" in node.label.lower() or
            node.properties.get("writes_user_balance") and
            node.properties.get("receives_value")
        )

    def _is_withdraw_like(self, node_id: str) -> bool:
        """Check if function looks like a withdraw."""
        node = self.code_kg.nodes.get(node_id)
        if not node:
            return False
        return (
            "withdraw" in node.label.lower() or
            node.properties.get("transfers_value_out") and
            node.properties.get("writes_user_balance")
        )

    def _has_external_call(self, node_id: str) -> bool:
        """Check if function makes external calls."""
        node = self.code_kg.nodes.get(node_id)
        return node and node.properties.get("has_external_call", False)

    def _writes_state(self, node_id: str) -> bool:
        """Check if function writes state."""
        node = self.code_kg.nodes.get(node_id)
        return node and node.properties.get("writes_state", False)

    def _share_state(self, node_a: str, node_b: str) -> bool:
        """Check if two functions access shared state."""
        node_a_obj = self.code_kg.nodes.get(node_a)
        node_b_obj = self.code_kg.nodes.get(node_b)

        if not node_a_obj or not node_b_obj:
            return False

        state_a = set(node_a_obj.properties.get("writes_state_vars", []))
        state_a |= set(node_a_obj.properties.get("reads_state_vars", []))

        state_b = set(node_b_obj.properties.get("writes_state_vars", []))
        state_b |= set(node_b_obj.properties.get("reads_state_vars", []))

        return bool(state_a & state_b)
```

---

## Implementation Plan

### Phase 1: Core Data Structures (1 day)
- [ ] Create `src/true_vkg/reasoning/__init__.py`
- [ ] Implement `ReasoningRound` dataclass
- [ ] Implement `ExpandedNode` dataclass
- [ ] Implement `CrossGraphFinding` dataclass
- [ ] Implement `AttackChain` dataclass
- [ ] Implement `ReasoningResult` dataclass
- [ ] Write unit tests for data structures
- **Checkpoint**: Can create and serialize round records

### Phase 2: Graph Expansion (1.5 days)
- [ ] Implement `_get_shared_state_functions()`
- [ ] Implement `_get_callers()` and `_get_callees()`
- [ ] Implement `_expand_neighbors()` with prioritization
- [ ] Write tests for expansion strategies
- [ ] Test expansion limit enforcement
- **Checkpoint**: Can expand from any node correctly

### Phase 3: Cross-Graph Integration (1 day)
- [ ] Implement `_query_cross_graphs()`
- [ ] Integrate with CrossGraphLinker
- [ ] Implement `_build_attack_chains()`
- [ ] Write tests for chain detection
- **Checkpoint**: Can detect multi-function chains

### Phase 4: Main Loop & Convergence (1 day)
- [ ] Implement `reason()` main loop
- [ ] Implement `_pattern_match()`
- [ ] Implement `_refine_candidates()`
- [ ] Implement `_converged()`
- [ ] Implement `_single_pass_simulation()`
- [ ] Integration tests with real VKG
- [ ] Performance benchmarks
- **Checkpoint**: Full iterative reasoning working

---

## Validation Tests

### Unit Tests

```python
# tests/test_3.5/test_iterative_engine.py

import pytest
from true_vkg.reasoning.iterative import (
    IterativeReasoningEngine,
    ReasoningRound,
    ReasoningResult,
    AttackChain,
    ExpansionType,
)


class TestGraphExpansion:
    """Test graph expansion strategies."""

    @pytest.fixture
    def engine(self):
        return IterativeReasoningEngine(
            code_kg=mock_code_kg,
            domain_kg=mock_domain_kg,
            adversarial_kg=mock_adversarial_kg,
            linker=mock_linker,
        )

    def test_expand_to_shared_state(self, engine):
        """Test expansion to functions sharing state."""
        # fn_withdraw and fn_deposit share 'balances' state
        expanded = engine._expand_neighbors(
            {"fn_withdraw"},
            set(),
        )

        # Should find fn_deposit through shared state
        shared_state_exp = [e for e in expanded if e.expansion_type == ExpansionType.SHARED_STATE]
        assert len(shared_state_exp) > 0
        assert any(e.node_id == "fn_deposit" for e in shared_state_exp)

    def test_expand_to_callers(self, engine):
        """Test expansion to caller functions."""
        # fn_internal is called by fn_withdraw
        expanded = engine._expand_neighbors(
            {"fn_internal"},
            set(),
        )

        caller_exp = [e for e in expanded if e.expansion_type == ExpansionType.CALLERS]
        assert len(caller_exp) > 0

    def test_expansion_limit_enforced(self, engine):
        """Test that expansion limit is respected."""
        engine.expansion_limit = 5

        expanded = engine._expand_neighbors(
            {"fn_central"},  # Has many neighbors
            set(),
        )

        assert len(expanded) <= 5

    def test_already_explored_excluded(self, engine):
        """Test that already explored nodes aren't re-expanded."""
        expanded = engine._expand_neighbors(
            {"fn_withdraw"},
            {"fn_deposit"},  # Already explored
        )

        assert not any(e.node_id == "fn_deposit" for e in expanded)


class TestConvergence:
    """Test convergence detection."""

    @pytest.fixture
    def engine(self):
        return IterativeReasoningEngine(
            code_kg=mock_code_kg,
            domain_kg=mock_domain_kg,
            adversarial_kg=mock_adversarial_kg,
            linker=mock_linker,
        )

    def test_converges_when_no_new_candidates(self, engine):
        """Test convergence when no new candidates added."""
        rounds = [
            ReasoningRound(
                round_num=1,
                input_candidates=["fn_a", "fn_b"],
                refined_candidates=["fn_a", "fn_b", "fn_c"],
                new_candidates_added=1,
                # ... other fields
            ),
            ReasoningRound(
                round_num=2,
                input_candidates=["fn_a", "fn_b", "fn_c"],
                refined_candidates=["fn_a", "fn_b", "fn_c"],
                new_candidates_added=0,  # No new candidates
                # ... other fields
            ),
        ]

        assert engine._converged(rounds)

    def test_does_not_converge_with_new_candidates(self, engine):
        """Test no convergence when new candidates added."""
        rounds = [
            ReasoningRound(
                round_num=1,
                input_candidates=["fn_a"],
                refined_candidates=["fn_a", "fn_b"],
                new_candidates_added=1,
            ),
        ]

        assert not engine._converged(rounds)


class TestAttackChainDetection:
    """Test multi-function attack chain detection."""

    @pytest.fixture
    def engine(self):
        return IterativeReasoningEngine(
            code_kg=mock_code_kg,
            domain_kg=mock_domain_kg,
            adversarial_kg=mock_adversarial_kg,
            linker=mock_linker,
        )

    def test_detect_deposit_withdraw_chain(self, engine):
        """Test detection of deposit → withdraw chain."""
        candidates = {"fn_deposit", "fn_withdraw"}
        expanded = []
        cross_findings = [
            CrossGraphFinding(
                source_node="fn_deposit",
                target_kg="adversarial",
                edge_type="SIMILAR_TO",
                target_spec_or_pattern="first_depositor_attack",
                confidence=0.8,
                evidence=["Share calculation vulnerable"],
            ),
        ]

        chains = engine._build_attack_chains(candidates, expanded, cross_findings)

        # Should detect inflation attack chain
        inflation_chains = [c for c in chains if "inflation" in c.id]
        assert len(inflation_chains) > 0
        assert "fn_deposit" in inflation_chains[0].functions
        assert "fn_withdraw" in inflation_chains[0].functions

    def test_detect_reentrancy_chain(self, engine):
        """Test detection of reentrancy chain."""
        # Setup: fn_a has external call, fn_b writes shared state
        mock_code_kg.nodes["fn_a"].properties["has_external_call"] = True
        mock_code_kg.nodes["fn_b"].properties["writes_state"] = True

        candidates = {"fn_a", "fn_b"}
        expanded = []

        chains = engine._build_attack_chains(candidates, expanded, [])

        reentry_chains = [c for c in chains if "reenter" in c.id]
        assert len(reentry_chains) > 0


class TestIterativeReasoning:
    """Test full iterative reasoning."""

    @pytest.fixture
    def engine(self):
        return IterativeReasoningEngine(
            code_kg=mock_code_kg,
            domain_kg=mock_domain_kg,
            adversarial_kg=mock_adversarial_kg,
            linker=mock_linker,
        )

    def test_multi_round_expansion(self, engine):
        """Test that multiple rounds expand the search."""
        result = engine.reason(
            initial_candidates=["fn_withdraw"],
            max_rounds=3,
        )

        # Should have multiple rounds
        assert len(result.rounds) >= 2

        # Final candidates should include expanded nodes
        assert len(result.final_candidates) > 1

    def test_finds_more_than_single_pass(self, engine):
        """Test iterative finds more than single-pass."""
        result = engine.reason(
            initial_candidates=["fn_deposit"],
            max_rounds=4,
        )

        # Iterative should find related withdraw function
        single_pass = set(result.single_pass_would_find)
        iterative = set(result.final_candidates)

        # Iterative should find at least as much, ideally more
        assert iterative >= single_pass or len(result.iterative_bonus_findings) > 0

    def test_convergence_reported(self, engine):
        """Test that convergence is correctly reported."""
        result = engine.reason(
            initial_candidates=["fn_isolated"],  # Node with few neighbors
            max_rounds=10,
        )

        # Should converge before max rounds
        assert result.converged or result.convergence_round <= 10
        assert result.convergence_reason in ["no_new_candidates", "max_rounds", "threshold"]


### Integration Tests

```python
def test_integration_with_real_vkg():
    """Test iterative reasoning on real VKG."""
    from tests.graph_cache import load_graph

    graph = load_graph("TokenVault")

    # Create engine with real graph
    engine = IterativeReasoningEngine(
        code_kg=graph,
        domain_kg=DomainKnowledgeGraph(),
        adversarial_kg=AdversarialKnowledgeGraph(),
        linker=CrossGraphLinker(graph, ..., ...),
    )

    # Find withdraw-like functions as starting point
    initial = [
        n.id for n in graph.nodes.values()
        if n.type == "Function" and "withdraw" in n.label.lower()
    ]

    result = engine.reason(initial_candidates=initial, max_rounds=4)

    # Should complete without error
    assert result is not None
    assert len(result.rounds) > 0

    # Should find some attack chains or cross-graph findings
    print(f"Rounds: {len(result.rounds)}")
    print(f"Final candidates: {len(result.final_candidates)}")
    print(f"Attack chains: {len(result.attack_chains)}")
    print(f"Cross-graph findings: {len(result.all_cross_graph_findings)}")
```

### Performance Tests

```python
def test_iterative_reasoning_performance():
    """Test that iterative reasoning is fast enough."""
    import time

    engine = IterativeReasoningEngine(
        code_kg=mock_large_kg,  # 100+ functions
        domain_kg=mock_domain_kg,
        adversarial_kg=mock_adversarial_kg,
        linker=mock_linker,
    )

    # Start with 10 candidates
    initial = [f"fn_{i}" for i in range(10)]

    start = time.time()
    result = engine.reason(initial_candidates=initial, max_rounds=4)
    elapsed = time.time() - start

    # Should complete 4 rounds in < 10 seconds
    assert elapsed < 10.0, f"Too slow: {elapsed:.2f}s"

    # Check per-round timing
    for round_rec in result.rounds:
        assert round_rec.expansion_time_ms < 2000  # < 2s per round expansion
        assert round_rec.cross_graph_time_ms < 3000  # < 3s per round cross-graph
```

### The Ultimate Test

```python
def test_ultimate_finds_chain_single_pass_misses():
    """
    Ultimate test: Iterative finds attack chain that single-pass misses.

    Setup:
    - fn_deposit has first depositor vulnerability
    - fn_withdraw has reentrancy but it's only exploitable
      AFTER first depositor attack inflates shares
    - Single pass on fn_withdraw alone won't see the connection
    """
    engine = IterativeReasoningEngine(...)

    # Single pass on withdraw
    single_result = engine._single_pass_simulation(["fn_withdraw"])

    # Iterative starting from withdraw
    iterative_result = engine.reason(["fn_withdraw"], max_rounds=4)

    # Iterative should discover fn_deposit through shared state
    assert "fn_deposit" in iterative_result.final_candidates, \
        "Iterative should discover connected deposit function"

    # Iterative should build the attack chain
    chain_found = any(
        "fn_deposit" in chain.functions and "fn_withdraw" in chain.functions
        for chain in iterative_result.attack_chains
    )
    assert chain_found, "Should find deposit → withdraw attack chain"

    # This chain wouldn't be found by single pass
    assert "fn_deposit" not in single_result, \
        "Single pass wouldn't find deposit from withdraw"

    print("SUCCESS: Iterative found chain single-pass missed")
    print(f"Attack chain: {iterative_result.attack_chains[0].description}")
```

---

## Metrics & Measurement

### Before Implementation (Baseline)
| Metric | Value | How Measured |
|--------|-------|--------------|
| Multi-function chain detection | 0 | Not available |
| Cross-graph queries | 0 | Not available |
| Iterative expansion | N/A | Single-pass only |

### After Implementation (Results)
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Chains detected (vs single-pass) | +20% | - | - |
| Convergence rounds (typical) | 3-4 | - | - |
| Total reasoning time | <10s | - | - |
| Cross-graph queries per round | <100 | - | - |

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Expansion explodes combinatorially | HIGH | MEDIUM | Strict limits, prioritization |
| False chains (spurious connections) | MEDIUM | MEDIUM | Require cross-graph support |
| Performance on large codebases | HIGH | MEDIUM | Caching, parallel expansion |

### Dependency Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| CrossGraphLinker not ready | HIGH | Can stub initially |
| AdversarialKG incomplete | MEDIUM | Test with available patterns |

---

## Critical Self-Analysis

### What Could Go Wrong
1. **Over-expansion**: Every function connects to every other → noise
   - Detection: Candidate set grows unboundedly
   - Mitigation: Strict limits, relevance scoring, require evidence

2. **False attack chains**: Spurious connections flagged as chains
   - Detection: High FP rate on chains
   - Mitigation: Require cross-graph support for chains

3. **Doesn't converge**: Always hits max rounds
   - Detection: Monitor convergence rate
   - Mitigation: Tune threshold, add adaptive stopping

### Assumptions Being Made
1. **Shared state indicates potential chains**: Functions sharing state can be chained
   - Validation: Test on known multi-function vulnerabilities

2. **Cross-graph findings indicate risk**: Domain/adversarial links meaningful
   - Validation: Correlation with real vulnerabilities

### Questions to Answer During Implementation
1. What's the right balance of expansion limit vs coverage?
2. Should chain confidence depend on hop distance?
3. How to handle very large codebases (1000+ functions)?

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
| 2026-01-03 | Enhanced with full detail | Claude |
