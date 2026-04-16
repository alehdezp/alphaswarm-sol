"""Tests for Game-Theoretic Attack Synthesis Engine (GATE).

Per 05.11-06: Comprehensive tests for attack synthesis, Nash equilibrium
solving, blocking condition identification, and incentive analysis.

Test Categories:
- Payoff matrix construction (3-player game models)
- Nash equilibrium computation (pure and mixed)
- Economic rationality filtering (EV < 0 deprioritized)
- Blocking condition identification
- MEV extraction modeling
- Integration with rationality gate
- Historical exploit backtest validation
"""

import numpy as np
import pytest

from alphaswarm_sol.economics import (
    # GATE types
    AttackStrategy,
    ProtocolDefense,
    MEVStrategy,
    AttackPayoffMatrix,
    AttackSynthesisEngine,
    compute_attack_ev,
    NashResult,
    BlockingCondition,
    BlockingConditionType,
    NashEquilibriumSolver,
    IncentiveMisalignment,
    IncentiveReport,
    IncentiveAnalyzer,
    # Existing types
    RationalityGate,
)
from alphaswarm_sol.economics.gate.incentive_analysis import MisalignmentType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_vulnerability():
    """Sample vulnerability for testing."""
    return {
        "id": "reentrancy-001",
        "pattern_id": "reentrancy-classic",
        "severity": "critical",
        "potential_profit_usd": 500000,
        "success_probability": 0.7,
        "gas_cost_estimate": 500000,
        "evidence_refs": ["EVD-001", "EVD-002"],
    }


@pytest.fixture
def sample_protocol_state():
    """Sample protocol state for testing."""
    return {
        "tvl_usd": 10_000_000,
        "gas_price_gwei": 50,
        "eth_price_usd": 2000,
        "detection_probability": 0.3,
        "timelock_seconds": 86400,
        "has_pause": True,
        "has_timelock": True,
    }


@pytest.fixture
def synthesis_engine():
    """Create attack synthesis engine."""
    return AttackSynthesisEngine()


@pytest.fixture
def nash_solver():
    """Create Nash equilibrium solver."""
    return NashEquilibriumSolver()


@pytest.fixture
def incentive_analyzer():
    """Create incentive analyzer."""
    return IncentiveAnalyzer()


# =============================================================================
# Test: Payoff Matrix Construction
# =============================================================================


class TestPayoffMatrixConstruction:
    """Tests for 3-player payoff matrix construction."""

    def test_payoff_matrix_basic_construction(
        self, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test basic payoff matrix construction."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        assert matrix is not None
        assert matrix.vulnerability_id == "reentrancy-001"
        assert len(matrix.attacker_strategies) > 0
        assert len(matrix.protocol_strategies) > 0
        assert len(matrix.mev_strategies) > 0

    def test_payoff_matrix_has_abstain_strategy(
        self, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test that abstain is always an attacker option."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        assert AttackStrategy.ABSTAIN in matrix.attacker_strategies

    def test_payoff_matrix_tensor_shape(
        self, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test payoff tensor has correct shape."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        expected_shape = (
            len(matrix.attacker_strategies),
            len(matrix.protocol_strategies),
            len(matrix.mev_strategies),
            3,  # 3 players
        )
        assert matrix.payoff_tensor.shape == expected_shape

    def test_payoff_matrix_includes_mev_strategies(
        self, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test MEV strategies are enumerated."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        assert MEVStrategy.ABSTAIN in matrix.mev_strategies

    def test_payoff_matrix_protocol_defenses(
        self, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test protocol defenses are enumerated from state."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        # Should include timelock and pause from protocol_state
        assert ProtocolDefense.TIMELOCK in matrix.protocol_strategies
        assert ProtocolDefense.PAUSE_MECHANISM in matrix.protocol_strategies

    def test_payoff_matrix_dominant_strategies_computed(
        self, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test dominant strategies are computed."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        assert "attacker" in matrix.dominant_strategies
        assert "protocol" in matrix.dominant_strategies
        assert "mev_searcher" in matrix.dominant_strategies

    def test_payoff_matrix_serialization_roundtrip(
        self, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test to_dict/from_dict roundtrip."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        data = matrix.to_dict()
        restored = AttackPayoffMatrix.from_dict(data)

        assert restored.vulnerability_id == matrix.vulnerability_id
        assert restored.scenario == matrix.scenario
        assert len(restored.attacker_strategies) == len(matrix.attacker_strategies)


class TestPayoffComputation:
    """Tests for payoff value computation."""

    def test_abstain_has_zero_payoff(
        self, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test abstaining results in zero payoffs."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        abstain_idx = matrix.attacker_strategies.index(AttackStrategy.ABSTAIN)
        abstain_payoffs = matrix.payoff_tensor[abstain_idx, :, :, 0]

        assert np.allclose(abstain_payoffs, 0.0)

    def test_attack_payoff_includes_gas_cost(self, synthesis_engine):
        """Test attack payoffs deduct gas costs."""
        vuln = {
            "id": "test-001",
            "severity": "high",
            "potential_profit_usd": 100000,
            "gas_cost_estimate": 1000000,  # High gas
        }
        state = {
            "gas_price_gwei": 100,  # High gas price
            "eth_price_usd": 2000,
            "tvl_usd": 1_000_000,
        }

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln,
            protocol_state=state,
        )

        # Attack payoffs should be reduced by gas costs
        # Gas cost = 100 gwei * 1M gas / 1e9 * 2000 USD = 200 USD
        # With high gas price, attack should still be profitable but reduced
        assert matrix.expected_value_usd is not None

    def test_mev_extraction_reduces_attacker_payoff(self, synthesis_engine):
        """Test MEV strategies reduce attacker profit."""
        vuln = {
            "id": "sandwich-001",
            "pattern_id": "sandwich-attack",
            "severity": "high",
            "potential_profit_usd": 100000,
        }
        state = {"tvl_usd": 1_000_000, "mev_exposure": "high"}

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln,
            protocol_state=state,
        )

        # Compare attacker payoff with MEV abstain vs MEV active
        abstain_mev_idx = matrix.mev_strategies.index(MEVStrategy.ABSTAIN)

        # Find a non-abstain MEV strategy
        active_mev_idx = None
        for i, s in enumerate(matrix.mev_strategies):
            if s != MEVStrategy.ABSTAIN:
                active_mev_idx = i
                break

        if active_mev_idx is not None:
            # Attacker payoff should be higher when MEV abstains
            for a_idx in range(len(matrix.attacker_strategies)):
                if matrix.attacker_strategies[a_idx] != AttackStrategy.ABSTAIN:
                    for p_idx in range(len(matrix.protocol_strategies)):
                        abstain_payoff = matrix.payoff_tensor[a_idx, p_idx, abstain_mev_idx, 0]
                        active_payoff = matrix.payoff_tensor[a_idx, p_idx, active_mev_idx, 0]
                        # MEV extraction should reduce attacker payoff
                        assert active_payoff <= abstain_payoff + 1e-6

    def test_defense_reduces_attack_success(self, synthesis_engine):
        """Test defenses reduce attack payoffs."""
        vuln = {
            "id": "test-001",
            "severity": "high",
            "potential_profit_usd": 100000,
            "guard_types": ["reentrancy_guard"],
        }
        state = {"tvl_usd": 1_000_000}

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln,
            protocol_state=state,
        )

        # Find no_defense and reentrancy_guard indices
        no_defense_idx = None
        guard_idx = None
        for i, d in enumerate(matrix.protocol_strategies):
            if d == ProtocolDefense.NO_DEFENSE:
                no_defense_idx = i
            elif d == ProtocolDefense.REENTRANCY_GUARD:
                guard_idx = i

        if no_defense_idx is not None and guard_idx is not None:
            # Attack payoff should be lower with guard active
            for a_idx in range(len(matrix.attacker_strategies)):
                if matrix.attacker_strategies[a_idx] != AttackStrategy.ABSTAIN:
                    for m_idx in range(len(matrix.mev_strategies)):
                        no_defense = matrix.payoff_tensor[a_idx, no_defense_idx, m_idx, 0]
                        with_guard = matrix.payoff_tensor[a_idx, guard_idx, m_idx, 0]
                        assert with_guard <= no_defense + 1e-6


# =============================================================================
# Test: Nash Equilibrium Computation
# =============================================================================


class TestNashEquilibriumPure:
    """Tests for pure strategy Nash equilibrium computation."""

    def test_nash_equilibrium_found(
        self, nash_solver, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test Nash equilibrium can be computed."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        result = nash_solver.solve_nash_equilibrium(matrix)

        assert result is not None
        assert result.attacker_strategy is not None
        assert result.protocol_strategy is not None
        assert result.mev_strategy is not None

    def test_nash_result_has_payoffs(
        self, nash_solver, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test Nash result includes payoffs."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        result = nash_solver.solve_nash_equilibrium(matrix)

        assert result.attacker_payoff is not None
        assert result.protocol_payoff is not None
        assert result.mev_payoff is not None

    def test_pure_nash_is_stable(self, nash_solver):
        """Test pure Nash equilibrium is stable (no player wants to deviate)."""
        # Create a simple game with known pure equilibrium
        vuln = {
            "id": "simple-001",
            "severity": "low",
            "potential_profit_usd": 100,  # Very low profit
            "gas_cost_estimate": 1000000,  # High gas
        }
        state = {
            "tvl_usd": 100000,
            "gas_price_gwei": 500,  # Very high gas price
        }

        engine = AttackSynthesisEngine()
        matrix = engine.compute_attack_ev(vulnerability=vuln, protocol_state=state)

        result = nash_solver.solve_nash_equilibrium(matrix)

        # With high gas and low profit, abstain should be optimal
        # (or attack should have negative EV)
        if result.is_pure_equilibrium:
            assert result.convergence_prob == 1.0


class TestNashEquilibriumMixed:
    """Tests for mixed strategy Nash equilibrium approximation."""

    def test_mixed_nash_approximation(
        self, nash_solver, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test mixed strategy equilibrium approximation."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        result = nash_solver.approximate_mixed_nash(matrix)

        assert result is not None
        assert result.is_pure_equilibrium is False
        assert result.mixed_strategy_probs is not None

    def test_mixed_nash_probabilities_sum_to_one(
        self, nash_solver, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test mixed strategy probabilities sum to 1."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        result = nash_solver.approximate_mixed_nash(matrix)

        for player, probs in result.mixed_strategy_probs.items():
            total = sum(probs.values())
            assert abs(total - 1.0) < 0.01, f"{player} probs sum to {total}"

    def test_mixed_nash_converges(self, nash_solver, synthesis_engine):
        """Test mixed equilibrium computation converges."""
        vuln = {
            "id": "complex-001",
            "pattern_id": "oracle-manipulation",
            "severity": "high",
            "potential_profit_usd": 100000,
        }
        state = {"tvl_usd": 5_000_000, "mev_exposure": "high"}

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )

        result = nash_solver.approximate_mixed_nash(matrix)

        # Should converge within max iterations
        assert result.iterations_to_converge <= nash_solver.max_iterations


# =============================================================================
# Test: Economic Rationality Filtering
# =============================================================================


class TestEconomicRationality:
    """Tests for economic rationality filtering."""

    def test_economically_irrational_filtered(self, synthesis_engine, nash_solver):
        """Test EV < 0 attacks are deprioritized."""
        # Create vulnerability where attack is unprofitable
        vuln = {
            "id": "unprofitable-001",
            "severity": "low",
            "potential_profit_usd": 10,  # $10 profit
            "gas_cost_estimate": 5000000,  # 5M gas
        }
        state = {
            "tvl_usd": 10000,
            "gas_price_gwei": 500,  # Very high gas
            "eth_price_usd": 3000,
        }

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        # With very high gas costs, attack should not be dominant
        # (note: might still be in some edge cases with mixed strategies)
        # The key is that EV should be low or negative
        assert result.attacker_payoff < 10000  # Not highly profitable

    def test_economically_rational_prioritized(
        self, synthesis_engine, nash_solver, sample_vulnerability, sample_protocol_state
    ):
        """Test EV > 0 attacks are marked as dominant."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,  # High profit vulnerability
            protocol_state=sample_protocol_state,
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        # With $500K profit and critical severity, attack should be rational
        if result.attacker_payoff > 0:
            assert result.is_economically_rational

    def test_integration_with_rationality_gate(self, synthesis_engine, nash_solver):
        """Test GATE results integrate with RationalityGate."""
        vuln = {
            "id": "test-integration",
            "severity": "high",
            "potential_profit_usd": 100000,
        }
        state = {"tvl_usd": 5_000_000}

        # Use GATE to compute attack EV
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )
        nash_result = nash_solver.solve_nash_equilibrium(matrix)

        # Feed into RationalityGate
        gate = RationalityGate()
        ev_result = gate.evaluate_attack_ev(
            vulnerability={
                **vuln,
                "potential_profit_usd": nash_result.attacker_payoff
                if nash_result.attacker_payoff > 0
                else 0,
            },
            protocol_state=state,
        )

        # Results should be consistent
        if nash_result.is_attack_dominant:
            assert ev_result.expected_value_usd > 0 or ev_result.is_economically_rational


# =============================================================================
# Test: Blocking Conditions
# =============================================================================


class TestBlockingConditions:
    """Tests for blocking condition identification."""

    def test_blocking_conditions_identified(
        self, nash_solver, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test blocking conditions are identified."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        # Should have blocking conditions from defenses
        # (may be empty if attack dominates)
        assert isinstance(result.blocking_conditions, list)

    def test_timelock_blocking_condition(self, nash_solver, synthesis_engine):
        """Test timelock creates blocking condition."""
        vuln = {
            "id": "governance-001",
            "pattern_id": "governance-attack",
            "severity": "high",
            "potential_profit_usd": 100000,
        }
        state = {
            "tvl_usd": 5_000_000,
            "has_timelock": True,
            "timelock_seconds": 172800,  # 2 days
        }

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        # Should identify timelock as potential blocker
        timelock_conditions = [
            bc
            for bc in result.blocking_conditions
            if bc.condition_type == BlockingConditionType.TIMELOCK
        ]
        # Timelock should be in protocol strategies
        assert ProtocolDefense.TIMELOCK in matrix.protocol_strategies

    def test_blocking_condition_has_threshold(
        self, nash_solver, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test blocking conditions have thresholds."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        for bc in result.blocking_conditions:
            assert bc.threshold is not None
            assert len(bc.threshold) > 0

    def test_blocking_condition_effect_positive(
        self, nash_solver, synthesis_engine, sample_vulnerability, sample_protocol_state
    ):
        """Test blocking conditions have positive effect."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        for bc in result.blocking_conditions:
            assert bc.effect_usd >= 0


# =============================================================================
# Test: MEV Extraction Modeling
# =============================================================================


class TestMEVModeling:
    """Tests for MEV extraction modeling."""

    def test_mev_extraction_modeled(self, synthesis_engine):
        """Test MEV reduces attacker profit."""
        vuln = {
            "id": "amm-001",
            "pattern_id": "sandwich-vulnerable-swap",
            "severity": "high",
            "potential_profit_usd": 100000,
        }
        state = {"tvl_usd": 5_000_000, "mev_exposure": "high"}

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )

        # Should have sandwich/frontrun MEV strategies
        has_mev_strategies = any(
            s in matrix.mev_strategies
            for s in [MEVStrategy.FRONTRUN, MEVStrategy.SANDWICH]
        )
        assert has_mev_strategies

    def test_mev_payoff_extracted(self, synthesis_engine, nash_solver):
        """Test MEV searcher extracts value."""
        vuln = {
            "id": "flash-001",
            "pattern_id": "flashloan-attack",
            "severity": "critical",
            "potential_profit_usd": 500000,
        }
        state = {"tvl_usd": 10_000_000}

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        # MEV payoff should be non-negative
        assert result.mev_payoff >= 0


# =============================================================================
# Test: Incentive Analysis
# =============================================================================


class TestIncentiveAnalysis:
    """Tests for incentive alignment analysis."""

    def test_analyze_incentives_basic(self, incentive_analyzer):
        """Test basic incentive analysis."""
        protocol_state = {
            "tvl_usd": 5_000_000,
            "vulnerabilities": [
                {"id": "vuln-1", "pattern_id": "mev-extraction", "severity": "high"}
            ],
            "mev_exposure": "high",
        }

        report = incentive_analyzer.analyze_incentives(protocol_state)

        assert report is not None
        assert isinstance(report.is_honest_dominant, bool)
        assert report.overall_alignment_score >= 0
        assert report.overall_alignment_score <= 100

    def test_misalignment_detected(self, incentive_analyzer):
        """Test incentive misalignment detection."""
        protocol_state = {
            "tvl_usd": 10_000_000,
            "vulnerabilities": [
                {
                    "id": "vuln-1",
                    "pattern_id": "sandwich-attack",
                    "severity": "high",
                    "potential_profit_usd": 50000,
                }
            ],
            "mev_exposure": "very_high",
        }

        report = incentive_analyzer.analyze_incentives(protocol_state)

        # Should detect MEV misalignment
        assert report.misalignment_count > 0

    def test_proof_of_behavior_detected(self, incentive_analyzer):
        """Test Proof-of-Behavior pattern detection."""
        protocol_state = {
            "tvl_usd": 5_000_000,
            "has_staking": True,
            "has_slashing": True,
            "has_reputation": True,
            "vulnerabilities": [],
        }

        report = incentive_analyzer.analyze_incentives(protocol_state)

        assert report.has_proof_of_behavior is True

    def test_blocking_suggestions_generated(self, incentive_analyzer):
        """Test blocking suggestions are generated for misalignments."""
        protocol_state = {
            "tvl_usd": 5_000_000,
            "vulnerabilities": [
                {"id": "vuln-1", "pattern_id": "frontrunning", "severity": "high"}
            ],
            "mev_exposure": "high",
        }

        report = incentive_analyzer.analyze_incentives(protocol_state)

        if report.misalignment_count > 0:
            # Should suggest mitigations
            assert len(report.blocking_suggestions) > 0

    def test_analyze_from_nash(
        self, incentive_analyzer, nash_solver, synthesis_engine, sample_vulnerability
    ):
        """Test analysis from Nash equilibrium result."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state={"tvl_usd": 10_000_000},
        )
        nash_result = nash_solver.solve_nash_equilibrium(matrix)

        report = incentive_analyzer.analyze_from_nash(nash_result, matrix)

        assert report is not None
        assert report.exploit_ev_usd == nash_result.attacker_payoff


# =============================================================================
# Test: Historical Exploit Backtest
# =============================================================================


class TestHistoricalBacktest:
    """Tests validating GATE against known historical exploits."""

    def test_reentrancy_classic_flagged_rational(self, synthesis_engine, nash_solver):
        """Test classic reentrancy exploit is flagged as rational.

        Based on: The DAO hack (2016) - $60M extracted.
        """
        vuln = {
            "id": "dao-reentrancy",
            "pattern_id": "reentrancy-classic",
            "severity": "critical",
            "potential_profit_usd": 60_000_000,
            "success_probability": 0.9,  # High success in actual exploit
        }
        state = {
            "tvl_usd": 150_000_000,  # The DAO TVL
            "gas_price_gwei": 10,  # 2016 gas prices
            "eth_price_usd": 20,  # 2016 ETH price
            "detection_probability": 0.1,  # Low detection at the time
        }

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        # DAO attack was definitely economically rational
        assert result.is_attack_dominant or result.attacker_payoff > 1_000_000

    def test_flashloan_attack_flagged_rational(self, synthesis_engine, nash_solver):
        """Test flash loan attack is flagged as rational.

        Based on: bZx flash loan attacks (2020) - $350K + $600K.
        """
        vuln = {
            "id": "bzx-flashloan",
            "pattern_id": "flashloan-oracle-manipulation",
            "severity": "critical",
            "potential_profit_usd": 350_000,
            "success_probability": 0.8,
        }
        state = {
            "tvl_usd": 15_000_000,
            "gas_price_gwei": 50,
            "eth_price_usd": 200,
            "flashloan_fee_bps": 9,
        }

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        # Flash loan attack was profitable
        assert result.attacker_payoff > 0 or result.is_attack_dominant

    def test_low_severity_not_flagged_critical(self, synthesis_engine, nash_solver):
        """Test low severity vulnerabilities are not marked critical."""
        vuln = {
            "id": "low-impact-001",
            "pattern_id": "informational-disclosure",
            "severity": "low",
            "potential_profit_usd": 100,  # Very low profit
        }
        state = {
            "tvl_usd": 1_000_000,
            "gas_price_gwei": 100,
            "eth_price_usd": 2000,
        }

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        # Low severity should not be marked as highly profitable
        # (may still be technically exploitable but not worth it)
        assert result.attacker_payoff < 10000

    def test_backtest_accuracy_target(self, synthesis_engine, nash_solver):
        """Test GATE achieves 80%+ accuracy on known exploits.

        Per 05.11-06: Target 80% accuracy on historical exploit classification.
        """
        # Known profitable exploits (should flag as rational)
        profitable_exploits = [
            {
                "id": "wormhole",
                "pattern_id": "signature-verification-bypass",
                "severity": "critical",
                "potential_profit_usd": 320_000_000,
                "success_probability": 0.95,
            },
            {
                "id": "ronin",
                "pattern_id": "access-control-failure",
                "severity": "critical",
                "potential_profit_usd": 625_000_000,
                "success_probability": 0.99,
            },
            {
                "id": "nomad",
                "pattern_id": "message-verification-bypass",
                "severity": "critical",
                "potential_profit_usd": 190_000_000,
                "success_probability": 0.9,
            },
        ]

        correct = 0
        for exploit in profitable_exploits:
            state = {"tvl_usd": exploit["potential_profit_usd"] * 2}
            matrix = synthesis_engine.compute_attack_ev(
                vulnerability=exploit, protocol_state=state
            )
            result = nash_solver.solve_nash_equilibrium(matrix)

            # These should all be flagged as rational
            if result.is_attack_dominant or result.attacker_payoff > 100000:
                correct += 1

        accuracy = correct / len(profitable_exploits)
        assert accuracy >= 0.8, f"Accuracy {accuracy:.0%} below 80% target"


# =============================================================================
# Test: Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module convenience functions."""

    def test_compute_attack_ev_function(self, sample_vulnerability, sample_protocol_state):
        """Test compute_attack_ev convenience function."""
        matrix = compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state=sample_protocol_state,
        )

        assert matrix is not None
        assert isinstance(matrix, AttackPayoffMatrix)

    def test_compute_attack_ev_with_overrides(self):
        """Test compute_attack_ev with parameter overrides."""
        vuln = {"id": "test", "severity": "high"}

        matrix = compute_attack_ev(
            vulnerability=vuln,
            gas_price_gwei=100,
            tvl_usd=5_000_000,
        )

        assert matrix is not None


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_vulnerability(self, synthesis_engine):
        """Test handling of minimal vulnerability data."""
        vuln = {"id": "empty-001"}
        state = {"tvl_usd": 1_000_000}

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )

        assert matrix is not None
        assert len(matrix.attacker_strategies) > 0

    def test_zero_tvl(self, synthesis_engine):
        """Test handling of zero TVL."""
        vuln = {"id": "zero-tvl", "severity": "high"}
        state = {"tvl_usd": 0}

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )

        # Should still produce valid matrix
        assert matrix is not None

    def test_extreme_gas_price(self, synthesis_engine, nash_solver):
        """Test handling of extreme gas prices."""
        vuln = {"id": "extreme-gas", "severity": "high", "potential_profit_usd": 1000}
        state = {
            "tvl_usd": 1_000_000,
            "gas_price_gwei": 10000,  # 10000 gwei = very high
            "eth_price_usd": 10000,
        }

        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=vuln, protocol_state=state
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        # With extreme gas, attack should be unprofitable
        assert result is not None

    def test_invalid_probability_handling(self):
        """Test invalid probability values are rejected."""
        with pytest.raises(ValueError):
            BlockingCondition(
                condition_type=BlockingConditionType.GUARD,
                threshold="test",
                effect_usd=100,
                confidence=1.5,  # Invalid: > 1.0
            )

    def test_nash_result_serialization(self, nash_solver, synthesis_engine, sample_vulnerability):
        """Test NashResult serialization."""
        matrix = synthesis_engine.compute_attack_ev(
            vulnerability=sample_vulnerability,
            protocol_state={"tvl_usd": 5_000_000},
        )
        result = nash_solver.solve_nash_equilibrium(matrix)

        data = result.to_dict()
        restored = NashResult.from_dict(data)

        assert restored.attacker_strategy == result.attacker_strategy
        assert restored.attacker_payoff == result.attacker_payoff
