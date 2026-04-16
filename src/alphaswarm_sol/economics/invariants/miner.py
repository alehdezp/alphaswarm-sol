"""Automated Invariant Mining from Transaction Traces.

Per 05.11-CONTEXT.md: Trace2Inv-style invariant mining that discovers
protocol invariants from execution traces. The miner extracts patterns
from observed transaction behavior and validates them statistically.

Key features:
- Mine invariants from transaction traces
- Trace2Inv-style pattern matching
- Statistical confidence scoring
- Counterexample tracking
- Exploit prevention validation

Usage:
    from alphaswarm_sol.economics.invariants import (
        InvariantMiner,
        InvariantCandidate,
        mine_from_traces,
    )

    miner = InvariantMiner()
    candidates = miner.mine_from_traces(
        contract_name="MyToken",
        traces=transaction_traces,
    )

    for candidate in candidates:
        print(f"{candidate.expression}: confidence={candidate.confidence}")
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .patterns import (
    CallValueUpperBound,
    DifferenceBound,
    InvariantPattern,
    InvariantPatternType,
    MappingLowerBound,
    MappingUpperBound,
    MonotonicProperty,
    RatioBound,
    StateTransitionConstraint,
    SumInvariant,
    VariableRelation,
)

logger = logging.getLogger(__name__)


@dataclass
class InvariantCandidate:
    """A candidate invariant discovered from trace mining.

    Per 05.11-CONTEXT.md: Candidates include confidence scoring,
    trace validation counts, and exploit prevention data.

    Attributes:
        id: Unique identifier for this candidate
        pattern_type: Type of invariant pattern
        expression: String representation of the invariant
        pattern: The underlying InvariantPattern object
        confidence: Statistical confidence 0.0-1.0
        supporting_traces: Number of traces supporting this invariant
        counterexample_traces: Number of traces violating this invariant
        would_prevent_exploits: List of known exploit IDs this would prevent
        natural_language: Human-readable description
        source_contract: Contract where invariant was discovered
        source_function: Function(s) where invariant applies
        discovered_at: When this candidate was discovered
    """

    id: str
    pattern_type: InvariantPatternType
    expression: str
    pattern: InvariantPattern
    confidence: float = 0.5
    supporting_traces: int = 0
    counterexample_traces: int = 0
    would_prevent_exploits: List[str] = field(default_factory=list)
    natural_language: str = ""
    source_contract: str = ""
    source_function: str = ""
    discovered_at: str = ""

    def __post_init__(self) -> None:
        """Initialize timestamp if not set."""
        if not self.discovered_at:
            self.discovered_at = datetime.utcnow().isoformat() + "Z"

    @property
    def total_traces(self) -> int:
        """Total number of traces evaluated."""
        return self.supporting_traces + self.counterexample_traces

    @property
    def support_ratio(self) -> float:
        """Ratio of supporting traces to total."""
        if self.total_traces == 0:
            return 0.0
        return self.supporting_traces / self.total_traces

    @property
    def is_high_confidence(self) -> bool:
        """Whether this is a high-confidence invariant (>= 0.9)."""
        return self.confidence >= 0.9

    @property
    def has_counterexamples(self) -> bool:
        """Whether any counterexamples were found."""
        return self.counterexample_traces > 0

    def add_exploit_prevention(self, exploit_id: str) -> None:
        """Add an exploit ID that this invariant would prevent."""
        if exploit_id not in self.would_prevent_exploits:
            self.would_prevent_exploits.append(exploit_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "pattern_type": self.pattern_type.value,
            "expression": self.expression,
            "confidence": self.confidence,
            "supporting_traces": self.supporting_traces,
            "counterexample_traces": self.counterexample_traces,
            "would_prevent_exploits": self.would_prevent_exploits,
            "natural_language": self.natural_language,
            "source_contract": self.source_contract,
            "source_function": self.source_function,
            "discovered_at": self.discovered_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], pattern: InvariantPattern) -> "InvariantCandidate":
        """Create InvariantCandidate from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            pattern_type=InvariantPatternType(data.get("pattern_type", "variable_relation")),
            expression=str(data.get("expression", "")),
            pattern=pattern,
            confidence=float(data.get("confidence", 0.5)),
            supporting_traces=int(data.get("supporting_traces", 0)),
            counterexample_traces=int(data.get("counterexample_traces", 0)),
            would_prevent_exploits=list(data.get("would_prevent_exploits", [])),
            natural_language=str(data.get("natural_language", "")),
            source_contract=str(data.get("source_contract", "")),
            source_function=str(data.get("source_function", "")),
            discovered_at=str(data.get("discovered_at", "")),
        )


@dataclass
class MiningConfig:
    """Configuration for invariant mining.

    Attributes:
        min_trace_coverage: Minimum trace coverage for acceptance (default 0.9)
        counterexample_tolerance: Maximum counterexample ratio (default 0.0)
        min_confidence: Minimum confidence threshold (default 0.7)
        confidence_decay_rate: Rate at which confidence decays for edge cases
        max_candidates: Maximum number of candidates to return
        enabled_pattern_types: Pattern types to mine (empty = all)
    """

    min_trace_coverage: float = 0.9
    counterexample_tolerance: float = 0.0
    min_confidence: float = 0.7
    confidence_decay_rate: float = 0.1
    max_candidates: int = 100
    enabled_pattern_types: Set[InvariantPatternType] = field(default_factory=set)


@dataclass
class MiningResult:
    """Result of invariant mining operation.

    Attributes:
        contract: Contract name
        candidates: List of discovered candidates
        traces_analyzed: Number of traces analyzed
        patterns_checked: Number of pattern templates checked
        mining_time_ms: Time spent mining (ms)
    """

    contract: str
    candidates: List[InvariantCandidate]
    traces_analyzed: int = 0
    patterns_checked: int = 0
    mining_time_ms: int = 0

    @property
    def high_confidence_candidates(self) -> List[InvariantCandidate]:
        """Get candidates with confidence >= 0.9."""
        return [c for c in self.candidates if c.is_high_confidence]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "contract": self.contract,
            "candidates_found": len(self.candidates),
            "high_confidence": len(self.high_confidence_candidates),
            "traces_analyzed": self.traces_analyzed,
            "patterns_checked": self.patterns_checked,
            "mining_time_ms": self.mining_time_ms,
        }


class InvariantMiner:
    """Trace2Inv-style invariant miner for transaction traces.

    Per 05.11-CONTEXT.md: Mines invariants from execution traces using
    pattern matching and statistical validation.

    The miner:
    1. Extracts state patterns from traces
    2. Generates candidate invariants from templates
    3. Validates candidates against all traces
    4. Computes statistical confidence
    5. Filters by confidence threshold

    Usage:
        miner = InvariantMiner()
        result = miner.mine_from_traces("MyToken", traces)

        for candidate in result.candidates:
            if candidate.confidence >= 0.9:
                print(f"High confidence: {candidate.expression}")
    """

    def __init__(self, config: Optional[MiningConfig] = None) -> None:
        """Initialize the miner.

        Args:
            config: Mining configuration
        """
        self.config = config or MiningConfig()
        self._candidate_counter = 0

    def _generate_candidate_id(self, prefix: str = "INV") -> str:
        """Generate unique candidate ID."""
        self._candidate_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{prefix}-{timestamp}-{self._candidate_counter:04d}"

    def mine_from_traces(
        self,
        contract_name: str,
        traces: List[Dict[str, Any]],
        state_vars: Optional[List[Dict[str, Any]]] = None,
    ) -> MiningResult:
        """Mine invariants from transaction traces.

        Args:
            contract_name: Name of the contract
            traces: List of execution traces with state snapshots
            state_vars: Optional state variable metadata

        Returns:
            MiningResult with discovered candidates
        """
        start_time = datetime.now()
        candidates: List[InvariantCandidate] = []
        patterns_checked = 0

        if not traces:
            return MiningResult(
                contract=contract_name,
                candidates=[],
                traces_analyzed=0,
                patterns_checked=0,
            )

        # Extract state variable names from traces
        state_vars_found = self._extract_state_variables(traces)

        # Generate candidate patterns from state analysis
        pattern_templates = self._generate_pattern_templates(state_vars_found, state_vars)
        patterns_checked = len(pattern_templates)

        # Validate each pattern against all traces
        for pattern in pattern_templates:
            if self.config.enabled_pattern_types and pattern.pattern_type not in self.config.enabled_pattern_types:
                continue

            supporting = 0
            counterexamples = 0

            for trace in traces:
                if pattern.check_trace(trace):
                    supporting += 1
                else:
                    counterexamples += 1

            # Calculate confidence
            confidence = self._calculate_confidence(
                supporting, counterexamples, pattern.base_confidence
            )

            # Check if pattern meets thresholds
            total = supporting + counterexamples
            if total > 0:
                coverage = supporting / total
                counter_ratio = counterexamples / total

                if coverage >= self.config.min_trace_coverage and counter_ratio <= self.config.counterexample_tolerance:
                    if confidence >= self.config.min_confidence:
                        candidate = InvariantCandidate(
                            id=self._generate_candidate_id(),
                            pattern_type=pattern.pattern_type,
                            expression=pattern.extract_expression(),
                            pattern=pattern,
                            confidence=confidence,
                            supporting_traces=supporting,
                            counterexample_traces=counterexamples,
                            natural_language=pattern.description,
                            source_contract=contract_name,
                        )
                        candidates.append(candidate)

            if len(candidates) >= self.config.max_candidates:
                break

        # Sort by confidence descending
        candidates.sort(key=lambda c: c.confidence, reverse=True)

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return MiningResult(
            contract=contract_name,
            candidates=candidates,
            traces_analyzed=len(traces),
            patterns_checked=patterns_checked,
            mining_time_ms=elapsed_ms,
        )

    def _extract_state_variables(self, traces: List[Dict[str, Any]]) -> Set[str]:
        """Extract state variable names from traces."""
        variables = set()

        for trace in traces:
            state = trace.get("state", {})
            pre_state = trace.get("pre_state", {})
            post_state = trace.get("post_state", {})

            for s in [state, pre_state, post_state]:
                for key in s.keys():
                    variables.add(key)

        return variables

    def _generate_pattern_templates(
        self,
        state_vars: Set[str],
        state_var_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> List[InvariantPattern]:
        """Generate pattern templates from state variables."""
        patterns: List[InvariantPattern] = []

        # Build metadata lookup
        metadata: Dict[str, Dict[str, Any]] = {}
        if state_var_metadata:
            for var in state_var_metadata:
                name = var.get("name", "")
                if name:
                    metadata[name] = var

        # Generate mapping patterns for balance-like variables
        balance_vars = [v for v in state_vars if "balance" in v.lower()]
        supply_vars = [v for v in state_vars if "supply" in v.lower() or "total" in v.lower()]

        for bal_var in balance_vars:
            # Mapping lower bound (non-negative)
            patterns.append(
                MappingLowerBound(
                    mapping_name=bal_var,
                    bound_value=0,
                    base_confidence=0.95,
                )
            )

            # Mapping upper bound with supply variables
            for supply_var in supply_vars:
                patterns.append(
                    MappingUpperBound(
                        mapping_name=bal_var,
                        bound_expression=supply_var,
                        base_confidence=0.85,
                    )
                )

        # Generate sum invariants
        for bal_var in balance_vars:
            for supply_var in supply_vars:
                patterns.append(
                    SumInvariant(
                        mapping_name=bal_var,
                        total_variable=supply_var,
                        base_confidence=0.8,
                    )
                )

        # Generate monotonic patterns for nonce/counter variables
        monotonic_hints = ["nonce", "counter", "id", "index", "timestamp", "block"]
        for var in state_vars:
            if any(hint in var.lower() for hint in monotonic_hints):
                patterns.append(
                    MonotonicProperty(
                        variable_name=var,
                        direction="increasing",
                        strict=True,
                        base_confidence=0.85,
                    )
                )

        # Generate state transition patterns for enum-like variables
        state_hints = ["state", "status", "phase", "stage"]
        for var in state_vars:
            if any(hint in var.lower() for hint in state_hints):
                # We can't know valid transitions without more context,
                # but we can flag the variable for analysis
                patterns.append(
                    StateTransitionConstraint(
                        state_variable=var,
                        valid_transitions={},  # Will be inferred from traces
                        base_confidence=0.6,
                    )
                )

        # Generate variable relation patterns for reserve variables (AMM)
        reserve_vars = [v for v in state_vars if "reserve" in v.lower()]
        if len(reserve_vars) >= 2:
            patterns.append(
                VariableRelation(
                    left_expression=f"{reserve_vars[0]} * {reserve_vars[1]}",
                    operator=">=",
                    right_expression="k",
                    base_confidence=0.7,
                )
            )

        # Generate ratio bounds for utilization/collateral
        ratio_hints = [("utilization", "supply"), ("borrowed", "collateral"), ("debt", "collateral")]
        for num_hint, denom_hint in ratio_hints:
            num_vars = [v for v in state_vars if num_hint in v.lower()]
            denom_vars = [v for v in state_vars if denom_hint in v.lower()]
            for num in num_vars:
                for denom in denom_vars:
                    patterns.append(
                        RatioBound(
                            numerator=num,
                            denominator=denom,
                            max_ratio=1.0,
                            min_ratio=0.0,
                            base_confidence=0.7,
                        )
                    )

        return patterns

    def _calculate_confidence(
        self,
        supporting: int,
        counterexamples: int,
        base_confidence: float,
    ) -> float:
        """Calculate confidence score for a candidate.

        Confidence is based on:
        - Base confidence from pattern type
        - Support ratio (supporting / total)
        - Decay for counterexamples
        """
        total = supporting + counterexamples
        if total == 0:
            return base_confidence * 0.5  # Low confidence for no data

        support_ratio = supporting / total

        # Start with base confidence adjusted by support
        confidence = base_confidence * support_ratio

        # Apply decay for counterexamples
        if counterexamples > 0:
            decay = self.config.confidence_decay_rate * counterexamples
            confidence *= max(0.0, 1.0 - decay)

        # Boost for high sample size
        if total >= 100:
            confidence = min(confidence * 1.1, 1.0)

        return round(confidence, 4)

    def mine_state_transitions(
        self,
        traces: List[Dict[str, Any]],
        state_variable: str,
    ) -> StateTransitionConstraint:
        """Mine valid state transitions from traces.

        Analyzes traces to discover the valid state machine.

        Args:
            traces: Execution traces with pre/post state
            state_variable: Name of the state variable

        Returns:
            StateTransitionConstraint with inferred transitions
        """
        transitions: Dict[str, Set[str]] = {}

        for trace in traces:
            pre = trace.get("pre_state", {})
            post = trace.get("post_state", trace.get("state", {}))

            old_state = str(pre.get(state_variable, ""))
            new_state = str(post.get(state_variable, ""))

            if old_state and new_state and old_state != new_state:
                if old_state not in transitions:
                    transitions[old_state] = set()
                transitions[old_state].add(new_state)

        return StateTransitionConstraint(
            state_variable=state_variable,
            valid_transitions={k: list(v) for k, v in transitions.items()},
        )


def mine_from_traces(
    contract_name: str,
    traces: List[Dict[str, Any]],
    config: Optional[MiningConfig] = None,
) -> List[InvariantCandidate]:
    """Convenience function to mine invariants from traces.

    Args:
        contract_name: Name of the contract
        traces: List of execution traces
        config: Optional mining configuration

    Returns:
        List of InvariantCandidate objects
    """
    miner = InvariantMiner(config)
    result = miner.mine_from_traces(contract_name, traces)
    return result.candidates


# Export all types
__all__ = [
    "InvariantCandidate",
    "MiningConfig",
    "MiningResult",
    "InvariantMiner",
    "mine_from_traces",
]
