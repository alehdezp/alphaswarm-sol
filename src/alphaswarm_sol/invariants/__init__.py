"""
Formal Invariant Synthesis

Automatically discovers and verifies contract invariants - properties
that must ALWAYS hold. Uses static analysis to infer invariants and
formal methods to verify them.

Key Components:
- InvariantType: Categories of invariants (balance, ownership, state)
- Invariant: A formal property that must hold
- InvariantMiner: Discovers invariants from code patterns
- InvariantVerifier: Verifies invariants hold
- InvariantGenerator: Generates Solidity assertions
"""

from .types import (
    InvariantType,
    InvariantStrength,
    Invariant,
    InvariantViolation,
    VerificationResult,
)

from .miner import (
    InvariantMiner,
    MiningConfig,
    MiningResult,
    PatternTemplate,
)

from .verifier import (
    InvariantVerifier,
    VerifierConfig,
    ProofResult,
    CounterExample,
)

from .generator import (
    InvariantGenerator,
    GeneratorConfig,
    AssertionCode,
    InvariantSpec,
)

from .synthesizer import (
    InvariantSynthesizer,
    SynthesisConfig,
    SynthesisResult,
)

__all__ = [
    # Types
    "InvariantType",
    "InvariantStrength",
    "Invariant",
    "InvariantViolation",
    "VerificationResult",
    # Miner
    "InvariantMiner",
    "MiningConfig",
    "MiningResult",
    "PatternTemplate",
    # Verifier
    "InvariantVerifier",
    "VerifierConfig",
    "ProofResult",
    "CounterExample",
    # Generator
    "InvariantGenerator",
    "GeneratorConfig",
    "AssertionCode",
    "InvariantSpec",
    # Synthesizer
    "InvariantSynthesizer",
    "SynthesisConfig",
    "SynthesisResult",
]
