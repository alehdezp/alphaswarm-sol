"""
Mutation Operators for Pattern Evolution.

Each operator represents a specific type of mutation that can
improve pattern performance.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Any
import random

from alphaswarm_sol.evolution.pattern_gene import PatternGene, EvolvablePattern


class MutationOperator(ABC):
    """Base class for mutation operators."""

    name: str = "base"
    description: str = "Base mutation operator"

    @abstractmethod
    def apply(self, pattern: EvolvablePattern) -> Optional[EvolvablePattern]:
        """
        Apply mutation to pattern.

        Returns:
            Mutated pattern or None if mutation not applicable.
        """
        pass

    @abstractmethod
    def is_applicable(self, pattern: EvolvablePattern) -> bool:
        """Check if this mutation can be applied."""
        pass


class ThresholdMutator(MutationOperator):
    """Adjust numeric thresholds in pattern conditions."""

    name = "threshold"
    description = "Adjust numeric threshold values (e.g., >= 0.5 → >= 0.7)"

    def __init__(self, adjustment_range: float = 0.3):
        self.adjustment_range = adjustment_range

    def is_applicable(self, pattern: EvolvablePattern) -> bool:
        """Check if pattern has numeric values."""
        for gene in pattern.genes + pattern.none_genes:
            if isinstance(gene.value, (int, float)):
                return True
        return False

    def apply(self, pattern: EvolvablePattern) -> Optional[EvolvablePattern]:
        if not self.is_applicable(pattern):
            return None

        mutant = pattern.copy()
        mutant.pattern_id = f"{pattern.pattern_id}_th"
        mutant.generation += 1
        mutant.parent_ids = [pattern.pattern_id]

        # Find numeric genes
        numeric_genes = [
            g for g in mutant.genes + mutant.none_genes
            if isinstance(g.value, (int, float))
        ]

        if not numeric_genes:
            return None

        # Mutate one
        gene = random.choice(numeric_genes)
        adjustment = random.uniform(-self.adjustment_range, self.adjustment_range)

        if isinstance(gene.value, int):
            gene.value = max(0, gene.value + int(adjustment * 10))
        else:
            gene.value = max(0.0, gene.value + adjustment)

        return mutant


class OperatorFlipMutator(MutationOperator):
    """Flip comparison operators (e.g., >= to <)."""

    name = "operator_flip"
    description = "Flip comparison operators to change condition logic"

    OPERATOR_PAIRS = {
        "==": "!=",
        "!=": "==",
        ">=": "<",
        "<": ">=",
        "<=": ">",
        ">": "<=",
        "in": "not_in",
        "not_in": "in",
    }

    def is_applicable(self, pattern: EvolvablePattern) -> bool:
        """Check if pattern has flippable operators."""
        for gene in pattern.genes + pattern.none_genes:
            if gene.operator in self.OPERATOR_PAIRS:
                return True
        return False

    def apply(self, pattern: EvolvablePattern) -> Optional[EvolvablePattern]:
        if not self.is_applicable(pattern):
            return None

        mutant = pattern.copy()
        mutant.pattern_id = f"{pattern.pattern_id}_of"
        mutant.generation += 1
        mutant.parent_ids = [pattern.pattern_id]

        # Find flippable genes
        flippable = [
            g for g in mutant.genes + mutant.none_genes
            if g.operator in self.OPERATOR_PAIRS
        ]

        if not flippable:
            return None

        # Flip one
        gene = random.choice(flippable)
        gene.operator = self.OPERATOR_PAIRS[gene.operator]

        return mutant


class ConditionAddMutator(MutationOperator):
    """Add new conditions to increase pattern specificity."""

    name = "condition_add"
    description = "Add new condition to reduce false positives"

    # Pool of common security-relevant conditions
    CONDITION_POOL = [
        PatternGene("visibility", "in", ["public", "external"]),
        PatternGene("writes_state", "==", True),
        PatternGene("makes_external_call", "==", True),
        PatternGene("has_access_gate", "==", False),
        PatternGene("has_reentrancy_guard", "==", False),
        PatternGene("modifies_balance", "==", True),
        PatternGene("reads_oracle_price", "==", True),
        PatternGene("uses_timestamp", "==", True),
        PatternGene("has_unbounded_loop", "==", True),
    ]

    def is_applicable(self, pattern: EvolvablePattern) -> bool:
        """Always applicable - can always add conditions."""
        return True

    def apply(self, pattern: EvolvablePattern) -> Optional[EvolvablePattern]:
        mutant = pattern.copy()
        mutant.pattern_id = f"{pattern.pattern_id}_ca"
        mutant.generation += 1
        mutant.parent_ids = [pattern.pattern_id]

        # Find conditions not already in pattern
        existing_props = {g.property for g in mutant.genes}
        available = [
            c for c in self.CONDITION_POOL
            if c.property not in existing_props
        ]

        if not available:
            return None

        # Add one random condition
        new_condition = random.choice(available).copy()
        new_condition.is_required = False  # Can be removed later
        mutant.genes.append(new_condition)

        return mutant


class ConditionRemoveMutator(MutationOperator):
    """Remove conditions to increase pattern sensitivity."""

    name = "condition_remove"
    description = "Remove condition to reduce false negatives"

    def is_applicable(self, pattern: EvolvablePattern) -> bool:
        """Check if pattern has removable conditions."""
        removable = [g for g in pattern.genes if not g.is_required]
        return len(removable) > 0

    def apply(self, pattern: EvolvablePattern) -> Optional[EvolvablePattern]:
        if not self.is_applicable(pattern):
            return None

        mutant = pattern.copy()
        mutant.pattern_id = f"{pattern.pattern_id}_cr"
        mutant.generation += 1
        mutant.parent_ids = [pattern.pattern_id]

        # Find removable conditions
        removable = [g for g in mutant.genes if not g.is_required]

        if not removable:
            return None

        # Remove one
        to_remove = random.choice(removable)
        mutant.genes.remove(to_remove)

        return mutant


class NoneConditionMutator(MutationOperator):
    """Move conditions between 'all' and 'none' sections."""

    name = "none_condition"
    description = "Move condition to 'none' section (exclusion)"

    def is_applicable(self, pattern: EvolvablePattern) -> bool:
        """Check if there are non-required conditions to move."""
        return len([g for g in pattern.genes if not g.is_required]) > 0

    def apply(self, pattern: EvolvablePattern) -> Optional[EvolvablePattern]:
        if not self.is_applicable(pattern):
            return None

        mutant = pattern.copy()
        mutant.pattern_id = f"{pattern.pattern_id}_nc"
        mutant.generation += 1
        mutant.parent_ids = [pattern.pattern_id]

        # Move a non-required condition to none
        movable = [g for g in mutant.genes if not g.is_required]

        if not movable:
            return None

        to_move = random.choice(movable)
        mutant.genes.remove(to_move)

        # Flip the condition logic for 'none'
        to_move.value = not to_move.value if isinstance(to_move.value, bool) else to_move.value
        mutant.none_genes.append(to_move)

        return mutant


class CompoundMutator(MutationOperator):
    """Apply multiple mutations in sequence."""

    name = "compound"
    description = "Apply 2-3 mutations in sequence"

    def __init__(self, operators: Optional[List[MutationOperator]] = None):
        self.operators = operators or [
            ThresholdMutator(),
            OperatorFlipMutator(),
            ConditionAddMutator(),
            ConditionRemoveMutator(),
        ]

    def is_applicable(self, pattern: EvolvablePattern) -> bool:
        """Check if any operator is applicable."""
        return any(op.is_applicable(pattern) for op in self.operators)

    def apply(self, pattern: EvolvablePattern) -> Optional[EvolvablePattern]:
        if not self.is_applicable(pattern):
            return None

        result = pattern
        num_mutations = random.randint(2, 3)

        for _ in range(num_mutations):
            applicable = [op for op in self.operators if op.is_applicable(result)]
            if not applicable:
                break

            operator = random.choice(applicable)
            mutated = operator.apply(result)

            if mutated:
                result = mutated

        if result == pattern:
            return None

        result.pattern_id = f"{pattern.pattern_id}_cm"
        return result
