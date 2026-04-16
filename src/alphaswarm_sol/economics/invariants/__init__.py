"""Automated Invariant Mining and Synthesis (AIMS) system.

Per 05.11-CONTEXT.md: AIMS discovers protocol invariants from transaction
traces and generates require() statements that would have prevented past
exploits. Catches "machine un-auditable" bugs where code doesn't match
implicit expectations.

Components:
- InvariantMiner: Extracts invariants from transaction traces
- InvariantCandidate: Discovered invariant with confidence scoring
- InvariantSynthesizer: Generates require() statements from invariants
- Pattern Library: Trace2Inv-style pattern types

Key Features:
- Trace-based mining: Learn invariants from observed behavior
- Exploit validation: Test if invariants would prevent known exploits
- Require synthesis: Generate defensive code from invariants
- Discrepancy detection: Compare mined vs declared invariants

Usage:
    from alphaswarm_sol.economics.invariants import (
        InvariantMiner,
        InvariantCandidate,
        InvariantSynthesizer,
        RequireStatement,
        mine_from_traces,
        synthesize_require,
    )

    # Mine invariants from traces
    miner = InvariantMiner()
    candidates = miner.mine_from_traces("MyToken", traces)

    # Synthesize require() statements
    synthesizer = InvariantSynthesizer()
    for candidate in candidates.candidates:
        if candidate.confidence >= 0.9:
            require = synthesizer.synthesize_require(candidate)
            print(f"// {candidate.natural_language}")
            print(f"{require.code}")

    # Validate against known exploits
    validation = synthesizer.validate_against_exploits(
        candidate, exploit_db
    )
    print(f"Would prevent: {validation.prevented_count} exploits")
"""

from .patterns import (
    COMMON_PATTERNS,
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
    get_pattern_for_type,
)

from .miner import (
    InvariantCandidate,
    InvariantMiner,
    MiningConfig,
    MiningResult,
    mine_from_traces,
)

from .synthesis import (
    Discrepancy,
    DiscrepancyType,
    ExploitValidationResult,
    InvariantSynthesizer,
    RequireStatement,
    SynthesisConfig,
    synthesize_require,
)

__all__ = [
    # Patterns
    "InvariantPatternType",
    "InvariantPattern",
    "MappingUpperBound",
    "MappingLowerBound",
    "CallValueUpperBound",
    "StateTransitionConstraint",
    "VariableRelation",
    "SumInvariant",
    "MonotonicProperty",
    "RatioBound",
    "DifferenceBound",
    "COMMON_PATTERNS",
    "get_pattern_for_type",
    # Miner
    "InvariantCandidate",
    "InvariantMiner",
    "MiningConfig",
    "MiningResult",
    "mine_from_traces",
    # Synthesis
    "InvariantSynthesizer",
    "RequireStatement",
    "SynthesisConfig",
    "ExploitValidationResult",
    "Discrepancy",
    "DiscrepancyType",
    "synthesize_require",
]
