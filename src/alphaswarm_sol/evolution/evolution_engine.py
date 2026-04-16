"""
Pattern Evolution Engine

Uses genetic algorithms to evolve vulnerability detection patterns
based on performance metrics (precision, recall, F1).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple, Any
import random
import logging
import time

from alphaswarm_sol.evolution.pattern_gene import PatternGene, EvolvablePattern
from alphaswarm_sol.evolution.mutation_operators import (
    MutationOperator,
    ThresholdMutator,
    OperatorFlipMutator,
    ConditionAddMutator,
    ConditionRemoveMutator,
    CompoundMutator,
)

logger = logging.getLogger(__name__)


@dataclass
class EvolutionConfig:
    """Configuration for pattern evolution."""

    population_size: int = 20
    max_generations: int = 50
    mutation_rate: float = 0.15
    crossover_rate: float = 0.7
    elite_size: int = 2  # Top N patterns always survive
    tournament_size: int = 3

    # Target metrics
    target_f1: float = 0.90
    min_precision: float = 0.70
    min_recall: float = 0.50

    # Fitness weights
    precision_weight: float = 0.4
    recall_weight: float = 0.4
    simplicity_weight: float = 0.2  # Prefer simpler patterns

    # Early stopping
    early_stop_generations: int = 10  # Stop if no improvement
    early_stop_threshold: float = 0.001


@dataclass
class EvolutionResult:
    """Result of pattern evolution."""

    best_pattern: EvolvablePattern
    final_fitness: float
    generations_run: int
    fitness_history: List[float] = field(default_factory=list)
    population_diversity: List[float] = field(default_factory=list)
    elapsed_time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_pattern_id": self.best_pattern.pattern_id,
            "final_fitness": self.final_fitness,
            "generations": self.generations_run,
            "metrics": self.best_pattern.calculate_metrics(),
            "elapsed_seconds": self.elapsed_time_seconds,
        }


class PatternEvolutionEngine:
    """
    Genetic algorithm engine for evolving patterns.

    Key insight: Patterns are like organisms - conditions are genes,
    and better patterns (higher F1) are more "fit" to survive.
    """

    def __init__(
        self,
        config: Optional[EvolutionConfig] = None,
        pattern_evaluator: Optional[Callable[[EvolvablePattern, Any], Dict[str, float]]] = None,
    ):
        """
        Initialize evolution engine.

        Args:
            config: Evolution configuration
            pattern_evaluator: Function that evaluates pattern on validation set
                              Returns dict with 'precision', 'recall', 'f1'
        """
        self.config = config or EvolutionConfig()
        self.pattern_evaluator = pattern_evaluator

        # Mutation operators
        self.operators: List[MutationOperator] = [
            ThresholdMutator(),
            OperatorFlipMutator(),
            ConditionAddMutator(),
            ConditionRemoveMutator(),
            CompoundMutator(),
        ]

    def evolve(
        self,
        base_pattern: EvolvablePattern,
        validation_set: Any = None,
    ) -> EvolutionResult:
        """
        Evolve a pattern to maximize fitness (F1 score).

        Args:
            base_pattern: Starting pattern to evolve from
            validation_set: Data to evaluate patterns against

        Returns:
            EvolutionResult with best pattern found
        """
        start_time = time.time()

        # Initialize population
        population = self._initialize_population(base_pattern)

        # Track evolution
        fitness_history = []
        diversity_history = []
        best_ever = None
        best_fitness = 0.0
        generations_without_improvement = 0

        for generation in range(self.config.max_generations):
            # Evaluate fitness for all patterns
            for pattern in population:
                pattern.fitness = self._calculate_fitness(pattern, validation_set)

            # Track best
            population.sort(key=lambda p: p.fitness, reverse=True)
            current_best = population[0]

            fitness_history.append(current_best.fitness)
            diversity_history.append(self._calculate_diversity(population))

            # Check for improvement
            if current_best.fitness > best_fitness + self.config.early_stop_threshold:
                best_fitness = current_best.fitness
                best_ever = current_best.copy()
                generations_without_improvement = 0
                logger.info(f"Gen {generation}: New best fitness = {best_fitness:.4f}")
            else:
                generations_without_improvement += 1

            # Early stopping
            if best_fitness >= self.config.target_f1:
                logger.info(f"Target F1 {self.config.target_f1} reached at generation {generation}")
                break

            if generations_without_improvement >= self.config.early_stop_generations:
                logger.info(f"Early stopping: No improvement for {generations_without_improvement} generations")
                break

            # Selection and reproduction
            population = self._next_generation(population)

        elapsed = time.time() - start_time

        if best_ever is None:
            best_ever = population[0]
            best_fitness = population[0].fitness

        return EvolutionResult(
            best_pattern=best_ever,
            final_fitness=best_fitness,
            generations_run=generation + 1,
            fitness_history=fitness_history,
            population_diversity=diversity_history,
            elapsed_time_seconds=elapsed,
        )

    def _initialize_population(self, base_pattern: EvolvablePattern) -> List[EvolvablePattern]:
        """Create initial population from base pattern."""
        population = [base_pattern.copy()]

        # Add mutated variants
        while len(population) < self.config.population_size:
            variant = base_pattern.mutate(self.config.mutation_rate * 2)  # More aggressive initially
            population.append(variant)

        return population

    def _calculate_fitness(
        self,
        pattern: EvolvablePattern,
        validation_set: Any,
    ) -> float:
        """
        Calculate fitness score for pattern.

        Fitness combines F1 score with pattern simplicity.
        """
        # Use external evaluator if provided
        if self.pattern_evaluator and validation_set is not None:
            metrics = self.pattern_evaluator(pattern, validation_set)
        else:
            # Use pattern's stored metrics
            metrics = pattern.calculate_metrics()

        precision = metrics.get("precision", 0.0)
        recall = metrics.get("recall", 0.0)
        f1 = metrics.get("f1", 0.0)

        # Penalize if below minimum thresholds
        if precision < self.config.min_precision:
            precision_penalty = (self.config.min_precision - precision) * 2
        else:
            precision_penalty = 0

        if recall < self.config.min_recall:
            recall_penalty = (self.config.min_recall - recall) * 2
        else:
            recall_penalty = 0

        # Calculate weighted fitness
        weighted_score = (
            precision * self.config.precision_weight +
            recall * self.config.recall_weight
        )

        # Simplicity bonus (fewer genes = simpler = better)
        num_genes = len(pattern.genes) + len(pattern.none_genes)
        simplicity = 1.0 / (1 + num_genes * 0.1)  # Decay with more genes
        weighted_score += simplicity * self.config.simplicity_weight

        # Apply penalties
        fitness = weighted_score - precision_penalty - recall_penalty

        return max(0.0, min(1.0, fitness))

    def _calculate_diversity(self, population: List[EvolvablePattern]) -> float:
        """Calculate genetic diversity in population."""
        if len(population) < 2:
            return 0.0

        # Count unique genes across population
        all_genes = set()
        for pattern in population:
            for gene in pattern.genes:
                all_genes.add((gene.property, gene.operator, str(gene.value)))

        # Diversity = unique genes / (population size * avg genes per pattern)
        avg_genes = sum(len(p.genes) for p in population) / len(population)
        if avg_genes == 0:
            return 0.0

        diversity = len(all_genes) / (len(population) * avg_genes)
        return min(1.0, diversity)

    def _next_generation(self, population: List[EvolvablePattern]) -> List[EvolvablePattern]:
        """Create next generation through selection, crossover, and mutation."""
        # Sort by fitness
        population.sort(key=lambda p: p.fitness, reverse=True)

        # Elite selection (top N always survive)
        next_gen = [p.copy() for p in population[:self.config.elite_size]]

        # Fill rest of population
        while len(next_gen) < self.config.population_size:
            # Tournament selection
            parent1 = self._tournament_select(population)
            parent2 = self._tournament_select(population)

            # Crossover
            if random.random() < self.config.crossover_rate:
                child = parent1.crossover(parent2)
            else:
                child = random.choice([parent1, parent2]).copy()

            # Mutation
            if random.random() < self.config.mutation_rate:
                child = self._apply_mutation(child)

            next_gen.append(child)

        return next_gen

    def _tournament_select(self, population: List[EvolvablePattern]) -> EvolvablePattern:
        """Select parent via tournament selection."""
        tournament = random.sample(population, min(self.config.tournament_size, len(population)))
        tournament.sort(key=lambda p: p.fitness, reverse=True)
        return tournament[0]

    def _apply_mutation(self, pattern: EvolvablePattern) -> EvolvablePattern:
        """Apply a random mutation operator."""
        # Filter applicable operators
        applicable = [op for op in self.operators if op.is_applicable(pattern)]

        if not applicable:
            return pattern.mutate(self.config.mutation_rate)

        operator = random.choice(applicable)
        mutated = operator.apply(pattern)

        return mutated if mutated else pattern.mutate(self.config.mutation_rate)

    def batch_evolve(
        self,
        patterns: List[EvolvablePattern],
        validation_set: Any = None,
    ) -> List[EvolutionResult]:
        """Evolve multiple patterns."""
        results = []
        for pattern in patterns:
            logger.info(f"Evolving pattern: {pattern.pattern_id}")
            result = self.evolve(pattern, validation_set)
            results.append(result)
        return results


class ValidationSetBuilder:
    """Helper to build validation sets for pattern evolution."""

    @staticmethod
    def from_labeled_contracts(
        vulnerable_contracts: List[Dict],
        safe_contracts: List[Dict],
    ) -> List[Tuple[Dict, bool]]:
        """
        Build validation set from labeled contracts.

        Args:
            vulnerable_contracts: List of (kg, vuln_type) for known vulnerable contracts
            safe_contracts: List of kg for known safe contracts

        Returns:
            List of (data, is_vulnerable) tuples
        """
        validation_set = []

        for contract in vulnerable_contracts:
            validation_set.append((contract, True))

        for contract in safe_contracts:
            validation_set.append((contract, False))

        return validation_set

    @staticmethod
    def from_exploit_database(
        ecosystem_learner: Any,
        vuln_type: str,
    ) -> List[Tuple[Dict, bool]]:
        """
        Build validation set from ecosystem exploit database.

        Args:
            ecosystem_learner: EcosystemLearner instance
            vuln_type: Vulnerability type to filter

        Returns:
            Validation set for that vulnerability type
        """
        validation_set = []

        # Get exploits of this type
        if hasattr(ecosystem_learner, 'exploits'):
            for exploit in ecosystem_learner.exploits.values():
                if hasattr(exploit, 'vulnerability_type'):
                    if exploit.vulnerability_type == vuln_type:
                        validation_set.append((exploit, True))

        return validation_set
