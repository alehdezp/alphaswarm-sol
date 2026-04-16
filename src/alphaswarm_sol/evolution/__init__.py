"""
Novel Solution: Self-Evolving Pattern System

Uses genetic algorithms to evolve vulnerability patterns based on
performance metrics (precision, recall, F1).

This is a novel contribution beyond the VKG 3.5 specification.
"""

from alphaswarm_sol.evolution.pattern_gene import PatternGene, EvolvablePattern
from alphaswarm_sol.evolution.evolution_engine import PatternEvolutionEngine
from alphaswarm_sol.evolution.mutation_operators import (
    MutationOperator,
    ThresholdMutator,
    OperatorFlipMutator,
    ConditionAddMutator,
    ConditionRemoveMutator,
)

__all__ = [
    "PatternGene",
    "EvolvablePattern",
    "PatternEvolutionEngine",
    "MutationOperator",
    "ThresholdMutator",
    "OperatorFlipMutator",
    "ConditionAddMutator",
    "ConditionRemoveMutator",
]
