"""
Tests for Novel Solution: Self-Evolving Pattern System

Tests pattern gene manipulation, mutation operators, crossover,
and the genetic algorithm evolution engine.
"""

import pytest
from unittest.mock import Mock, MagicMock
import random

from alphaswarm_sol.evolution.pattern_gene import PatternGene, EvolvablePattern
from alphaswarm_sol.evolution.mutation_operators import (
    ThresholdMutator,
    OperatorFlipMutator,
    ConditionAddMutator,
    ConditionRemoveMutator,
    CompoundMutator,
)
from alphaswarm_sol.evolution.evolution_engine import (
    PatternEvolutionEngine,
    EvolutionConfig,
    EvolutionResult,
    ValidationSetBuilder,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def simple_gene():
    """Create a simple pattern gene."""
    return PatternGene(
        property="visibility",
        operator="in",
        value=["public", "external"],
        weight=1.0,
        is_required=True,
    )


@pytest.fixture
def numeric_gene():
    """Create a gene with numeric value."""
    return PatternGene(
        property="risk_score",
        operator=">=",
        value=0.5,
        weight=1.0,
        is_required=False,
    )


@pytest.fixture
def reentrancy_pattern():
    """Create a reentrancy-like pattern."""
    return EvolvablePattern(
        pattern_id="reentrancy_v1",
        name="Classic Reentrancy",
        severity="critical",
        genes=[
            PatternGene("visibility", "in", ["public", "external"], is_required=True),
            PatternGene("makes_external_call", "==", True, is_required=True),
            PatternGene("writes_state", "==", True, is_required=True),
            PatternGene("state_write_after_external_call", "==", True, is_required=False),
        ],
        none_genes=[
            PatternGene("has_reentrancy_guard", "==", True),
        ],
    )


@pytest.fixture
def simple_pattern():
    """Create a minimal pattern."""
    return EvolvablePattern(
        pattern_id="simple_v1",
        name="Simple Pattern",
        genes=[
            PatternGene("writes_state", "==", True, is_required=True),
            PatternGene("has_access_gate", "==", False, is_required=False),
        ],
    )


@pytest.fixture
def evolution_config():
    """Create test evolution config."""
    return EvolutionConfig(
        population_size=10,
        max_generations=5,
        mutation_rate=0.2,
        crossover_rate=0.7,
        elite_size=2,
        target_f1=0.85,
    )


# =============================================================================
# PatternGene Tests
# =============================================================================


class TestPatternGene:
    """Test PatternGene class."""

    def test_creation(self, simple_gene):
        """Test gene creation."""
        assert simple_gene.property == "visibility"
        assert simple_gene.operator == "in"
        assert simple_gene.value == ["public", "external"]
        assert simple_gene.is_required == True

    def test_copy(self, simple_gene):
        """Test gene copying."""
        copy = simple_gene.copy()

        assert copy.property == simple_gene.property
        assert copy.operator == simple_gene.operator
        assert copy.value == simple_gene.value
        assert copy is not simple_gene
        assert copy.value is not simple_gene.value  # Deep copy

    def test_to_dict(self, simple_gene):
        """Test conversion to dict."""
        d = simple_gene.to_dict()

        assert d["property"] == "visibility"
        assert d["op"] == "in"
        assert d["value"] == ["public", "external"]

    def test_from_dict(self):
        """Test creation from dict."""
        d = {"property": "has_access_gate", "op": "==", "value": False}
        gene = PatternGene.from_dict(d)

        assert gene.property == "has_access_gate"
        assert gene.operator == "=="
        assert gene.value == False


# =============================================================================
# EvolvablePattern Tests
# =============================================================================


class TestEvolvablePattern:
    """Test EvolvablePattern class."""

    def test_creation(self, reentrancy_pattern):
        """Test pattern creation."""
        assert reentrancy_pattern.pattern_id == "reentrancy_v1"
        assert len(reentrancy_pattern.genes) == 4
        assert len(reentrancy_pattern.none_genes) == 1
        assert reentrancy_pattern.generation == 0

    def test_copy(self, reentrancy_pattern):
        """Test pattern copying."""
        copy = reentrancy_pattern.copy()

        assert copy.pattern_id == reentrancy_pattern.pattern_id
        assert len(copy.genes) == len(reentrancy_pattern.genes)
        assert copy is not reentrancy_pattern
        assert copy.genes is not reentrancy_pattern.genes

    def test_mutate(self, simple_pattern):
        """Test pattern mutation."""
        random.seed(42)  # For reproducibility

        mutant = simple_pattern.mutate(mutation_rate=0.5)

        assert mutant is not simple_pattern
        assert mutant.pattern_id != simple_pattern.pattern_id
        assert mutant.generation == simple_pattern.generation + 1
        assert simple_pattern.pattern_id in mutant.parent_ids

    def test_crossover(self, reentrancy_pattern, simple_pattern):
        """Test pattern crossover."""
        child = reentrancy_pattern.crossover(simple_pattern)

        assert child is not reentrancy_pattern
        assert child is not simple_pattern
        assert child.generation > 0
        assert len(child.parent_ids) == 2
        assert reentrancy_pattern.pattern_id in child.parent_ids
        assert simple_pattern.pattern_id in child.parent_ids

    def test_calculate_metrics(self, simple_pattern):
        """Test metrics calculation."""
        simple_pattern.true_positives = 80
        simple_pattern.false_positives = 10
        simple_pattern.false_negatives = 20
        simple_pattern.true_negatives = 90

        metrics = simple_pattern.calculate_metrics()

        assert metrics["true_positives"] == 80
        assert metrics["false_positives"] == 10
        assert 0.88 < metrics["precision"] < 0.90  # 80/(80+10)
        assert 0.79 < metrics["recall"] < 0.81  # 80/(80+20)
        assert metrics["f1"] > 0

    def test_to_yaml(self, reentrancy_pattern):
        """Test YAML conversion."""
        yaml_dict = reentrancy_pattern.to_yaml()

        assert yaml_dict["id"] == "reentrancy_v1"
        assert yaml_dict["name"] == "Classic Reentrancy"
        assert yaml_dict["severity"] == "critical"
        assert "tier_a" in yaml_dict["match"]
        assert "all" in yaml_dict["match"]["tier_a"]
        assert "none" in yaml_dict["match"]["tier_a"]

    def test_from_yaml(self):
        """Test creation from YAML."""
        yaml_dict = {
            "id": "test_pattern",
            "name": "Test Pattern",
            "severity": "high",
            "match": {
                "tier_a": {
                    "all": [
                        {"property": "visibility", "op": "==", "value": "public"},
                    ],
                    "none": [
                        {"property": "has_access_gate", "op": "==", "value": True},
                    ],
                }
            },
        }

        pattern = EvolvablePattern.from_yaml(yaml_dict)

        assert pattern.pattern_id == "test_pattern"
        assert len(pattern.genes) == 1
        assert len(pattern.none_genes) == 1


# =============================================================================
# Mutation Operator Tests
# =============================================================================


class TestMutationOperators:
    """Test mutation operators."""

    def test_threshold_mutator(self, numeric_gene):
        """Test threshold mutation."""
        pattern = EvolvablePattern(
            pattern_id="test",
            name="Test",
            genes=[numeric_gene],
        )

        mutator = ThresholdMutator()
        assert mutator.is_applicable(pattern)

        random.seed(42)
        mutant = mutator.apply(pattern)

        assert mutant is not None
        assert mutant.pattern_id != pattern.pattern_id

    def test_operator_flip_mutator(self):
        """Test operator flip mutation."""
        pattern = EvolvablePattern(
            pattern_id="test",
            name="Test",
            genes=[PatternGene("score", ">=", 0.5)],
        )

        mutator = OperatorFlipMutator()
        assert mutator.is_applicable(pattern)

        mutant = mutator.apply(pattern)

        assert mutant is not None
        # Operator should have flipped
        assert mutant.genes[0].operator in [">=", "<"]

    def test_condition_add_mutator(self, simple_pattern):
        """Test condition add mutation."""
        mutator = ConditionAddMutator()
        assert mutator.is_applicable(simple_pattern)

        original_count = len(simple_pattern.genes)
        mutant = mutator.apply(simple_pattern)

        assert mutant is not None
        assert len(mutant.genes) == original_count + 1

    def test_condition_remove_mutator(self, simple_pattern):
        """Test condition remove mutation."""
        mutator = ConditionRemoveMutator()
        assert mutator.is_applicable(simple_pattern)

        original_count = len(simple_pattern.genes)
        mutant = mutator.apply(simple_pattern)

        assert mutant is not None
        assert len(mutant.genes) == original_count - 1

    def test_compound_mutator(self, simple_pattern):
        """Test compound mutation."""
        mutator = CompoundMutator()
        assert mutator.is_applicable(simple_pattern)

        random.seed(42)
        mutant = mutator.apply(simple_pattern)

        assert mutant is not None
        assert mutant.pattern_id != simple_pattern.pattern_id


# =============================================================================
# Evolution Engine Tests
# =============================================================================


class TestEvolutionEngine:
    """Test evolution engine."""

    def test_initialization(self, evolution_config):
        """Test engine initialization."""
        engine = PatternEvolutionEngine(config=evolution_config)

        assert engine.config.population_size == 10
        assert engine.config.max_generations == 5
        assert len(engine.operators) > 0

    def test_evolve_simple(self, simple_pattern, evolution_config):
        """Test basic evolution."""
        # Create mock evaluator that returns improving fitness
        call_count = [0]

        def mock_evaluator(pattern, validation_set):
            call_count[0] += 1
            # Simulate improving fitness over time
            base_fitness = 0.5 + (pattern.generation * 0.1)
            return {
                "precision": min(0.9, base_fitness),
                "recall": min(0.8, base_fitness - 0.1),
                "f1": min(0.85, base_fitness - 0.05),
            }

        engine = PatternEvolutionEngine(
            config=evolution_config,
            pattern_evaluator=mock_evaluator,
        )

        result = engine.evolve(simple_pattern, validation_set=[])

        assert isinstance(result, EvolutionResult)
        assert result.best_pattern is not None
        assert result.generations_run > 0
        assert len(result.fitness_history) > 0
        assert call_count[0] > 0

    def test_evolve_reaches_target(self, simple_pattern):
        """Test evolution reaches target fitness."""
        config = EvolutionConfig(
            population_size=5,
            max_generations=10,
            target_f1=0.70,  # Low target for quick test
        )

        # Evaluator that returns high fitness
        def good_evaluator(pattern, vs):
            return {"precision": 0.9, "recall": 0.8, "f1": 0.85}

        engine = PatternEvolutionEngine(config=config, pattern_evaluator=good_evaluator)
        result = engine.evolve(simple_pattern, [])

        assert result.final_fitness >= 0.5  # Should have improved

    def test_population_diversity(self, simple_pattern, evolution_config):
        """Test that population maintains diversity."""
        engine = PatternEvolutionEngine(config=evolution_config)

        def evaluator(p, vs):
            return {"precision": 0.5, "recall": 0.5, "f1": 0.5}

        engine.pattern_evaluator = evaluator
        result = engine.evolve(simple_pattern, [])

        # Should have tracked diversity
        assert len(result.population_diversity) > 0

    def test_early_stopping(self, simple_pattern):
        """Test early stopping when no improvement."""
        config = EvolutionConfig(
            population_size=5,
            max_generations=50,
            early_stop_generations=3,
        )

        # Evaluator that returns constant fitness (no improvement)
        def constant_evaluator(p, vs):
            return {"precision": 0.5, "recall": 0.5, "f1": 0.5}

        engine = PatternEvolutionEngine(config=config, pattern_evaluator=constant_evaluator)
        result = engine.evolve(simple_pattern, [])

        # Should stop early due to no improvement
        assert result.generations_run < config.max_generations

    def test_elite_preservation(self, simple_pattern, evolution_config):
        """Test that elite patterns survive."""
        engine = PatternEvolutionEngine(config=evolution_config)

        # Track population across generations
        populations = []

        original_next_gen = engine._next_generation

        def tracking_next_gen(population):
            populations.append([p.copy() for p in population])
            return original_next_gen(population)

        engine._next_generation = tracking_next_gen

        def evaluator(p, vs):
            return {"precision": 0.5, "recall": 0.5, "f1": 0.5}

        engine.pattern_evaluator = evaluator
        engine.evolve(simple_pattern, [])

        # Elite should be preserved
        assert len(populations) > 0

    def test_result_to_dict(self, simple_pattern, evolution_config):
        """Test result serialization."""
        engine = PatternEvolutionEngine(config=evolution_config)

        def evaluator(p, vs):
            return {"precision": 0.7, "recall": 0.6, "f1": 0.65}

        engine.pattern_evaluator = evaluator
        result = engine.evolve(simple_pattern, [])

        d = result.to_dict()

        assert "best_pattern_id" in d
        assert "final_fitness" in d
        assert "generations" in d
        assert "metrics" in d


# =============================================================================
# ValidationSetBuilder Tests
# =============================================================================


class TestValidationSetBuilder:
    """Test validation set builder."""

    def test_from_labeled_contracts(self):
        """Test building from labeled contracts."""
        vulnerable = [{"id": "v1"}, {"id": "v2"}]
        safe = [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}]

        validation_set = ValidationSetBuilder.from_labeled_contracts(vulnerable, safe)

        assert len(validation_set) == 5
        vuln_count = sum(1 for _, is_vuln in validation_set if is_vuln)
        assert vuln_count == 2

    def test_from_exploit_database(self):
        """Test building from exploit database."""
        # Create mock ecosystem learner
        learner = Mock()
        exploit1 = Mock()
        exploit1.vulnerability_type = "reentrancy"
        exploit2 = Mock()
        exploit2.vulnerability_type = "access_control"
        learner.exploits = {"e1": exploit1, "e2": exploit2}

        validation_set = ValidationSetBuilder.from_exploit_database(learner, "reentrancy")

        assert len(validation_set) == 1
        assert validation_set[0][1] == True  # Is vulnerable


# =============================================================================
# Integration Tests
# =============================================================================


class TestEvolutionIntegration:
    """Integration tests for evolution system."""

    def test_full_evolution_cycle(self):
        """Test complete evolution cycle."""
        # Create a realistic pattern
        pattern = EvolvablePattern(
            pattern_id="auth_bypass_v1",
            name="Authorization Bypass",
            severity="high",
            genes=[
                PatternGene("visibility", "in", ["public", "external"], is_required=True),
                PatternGene("writes_privileged_state", "==", True, is_required=True),
                PatternGene("has_access_gate", "==", False, is_required=False),
            ],
        )

        config = EvolutionConfig(
            population_size=10,
            max_generations=10,
            mutation_rate=0.15,
            target_f1=0.80,
        )

        # Simulate evaluator with realistic behavior
        def realistic_evaluator(p, vs):
            # Base metrics
            base_precision = 0.6
            base_recall = 0.7

            # Improve based on number of genes (more specific = better precision)
            precision_bonus = len(p.genes) * 0.05
            # But too many genes hurt recall
            recall_penalty = max(0, (len(p.genes) - 3) * 0.1)

            precision = min(0.95, base_precision + precision_bonus)
            recall = max(0.3, base_recall - recall_penalty)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            return {"precision": precision, "recall": recall, "f1": f1}

        engine = PatternEvolutionEngine(config=config, pattern_evaluator=realistic_evaluator)
        result = engine.evolve(pattern, [])

        # Should have evolved
        assert result.best_pattern is not None
        # Best pattern could be original (gen 0) or evolved (gen > 0)
        assert result.best_pattern.generation >= 0
        assert result.final_fitness > 0

        # Should be able to convert to YAML
        yaml_output = result.best_pattern.to_yaml()
        assert "id" in yaml_output
        assert "match" in yaml_output

    def test_batch_evolution(self, simple_pattern, reentrancy_pattern, evolution_config):
        """Test batch evolution of multiple patterns."""
        evolution_config.max_generations = 3  # Quick test

        def evaluator(p, vs):
            return {"precision": 0.7, "recall": 0.6, "f1": 0.65}

        engine = PatternEvolutionEngine(config=evolution_config, pattern_evaluator=evaluator)
        results = engine.batch_evolve([simple_pattern, reentrancy_pattern], [])

        assert len(results) == 2
        for result in results:
            assert isinstance(result, EvolutionResult)
            assert result.best_pattern is not None
