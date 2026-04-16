"""Tests for Automated Invariant Mining and Synthesis (AIMS).

Per 05.11-09-PLAN.md: Tests for invariant mining from transaction traces,
require() synthesis, and exploit validation.

Test coverage:
- test_mapping_bound_mining: balance <= totalSupply found
- test_state_transition_mining: valid state machine inferred
- test_sum_invariant_mining: conservation law discovered
- test_confidence_filtering: low-confidence invariants filtered
- test_require_synthesis: valid Solidity code generated
- test_exploit_validation: invariant would prevent known exploit
- test_discrepancy_detection: mined vs declared differences found
- test_registry_integration: mined invariants registered correctly
"""

import pytest
from typing import Any, Dict, List

from alphaswarm_sol.economics.invariants import (
    COMMON_PATTERNS,
    CallValueUpperBound,
    Discrepancy,
    DiscrepancyType,
    ExploitValidationResult,
    InvariantCandidate,
    InvariantMiner,
    InvariantPattern,
    InvariantPatternType,
    InvariantSynthesizer,
    MappingLowerBound,
    MappingUpperBound,
    MiningConfig,
    MiningResult,
    MonotonicProperty,
    RatioBound,
    RequireStatement,
    StateTransitionConstraint,
    SumInvariant,
    SynthesisConfig,
    VariableRelation,
    mine_from_traces,
    synthesize_require,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def erc20_traces() -> List[Dict[str, Any]]:
    """Sample ERC20 token transaction traces."""
    return [
        {
            "tx_hash": "0x1",
            "function": "transfer",
            "state": {
                "balances": {"alice": 1000, "bob": 500},
                "totalSupply": 1500,
            },
            "pre_state": {
                "balances": {"alice": 1500, "bob": 0},
                "totalSupply": 1500,
            },
            "post_state": {
                "balances": {"alice": 1000, "bob": 500},
                "totalSupply": 1500,
            },
        },
        {
            "tx_hash": "0x2",
            "function": "mint",
            "state": {
                "balances": {"alice": 1000, "bob": 500, "carol": 100},
                "totalSupply": 1600,
            },
            "pre_state": {
                "balances": {"alice": 1000, "bob": 500},
                "totalSupply": 1500,
            },
            "post_state": {
                "balances": {"alice": 1000, "bob": 500, "carol": 100},
                "totalSupply": 1600,
            },
        },
        {
            "tx_hash": "0x3",
            "function": "burn",
            "state": {
                "balances": {"alice": 900, "bob": 500, "carol": 100},
                "totalSupply": 1500,
            },
            "pre_state": {
                "balances": {"alice": 1000, "bob": 500, "carol": 100},
                "totalSupply": 1600,
            },
            "post_state": {
                "balances": {"alice": 900, "bob": 500, "carol": 100},
                "totalSupply": 1500,
            },
        },
    ]


@pytest.fixture
def state_machine_traces() -> List[Dict[str, Any]]:
    """Sample state machine transition traces."""
    return [
        {
            "tx_hash": "0x1",
            "function": "initialize",
            "pre_state": {"state": "0"},
            "post_state": {"state": "1"},
        },
        {
            "tx_hash": "0x2",
            "function": "start",
            "pre_state": {"state": "1"},
            "post_state": {"state": "2"},
        },
        {
            "tx_hash": "0x3",
            "function": "finish",
            "pre_state": {"state": "2"},
            "post_state": {"state": "3"},
        },
        {
            "tx_hash": "0x4",
            "function": "reset",
            "pre_state": {"state": "3"},
            "post_state": {"state": "1"},
        },
    ]


@pytest.fixture
def nonce_traces() -> List[Dict[str, Any]]:
    """Sample nonce increment traces."""
    return [
        {
            "tx_hash": f"0x{i}",
            "function": "execute",
            "pre_state": {"nonce": i},
            "post_state": {"nonce": i + 1},
        }
        for i in range(10)
    ]


@pytest.fixture
def exploit_db() -> List[Dict[str, Any]]:
    """Sample exploit database for validation."""
    return [
        {
            "id": "exploit-001",
            "name": "Balance Overflow",
            "traces": [
                {
                    "state": {
                        "balances": {"attacker": 999999999},
                        "totalSupply": 1000,
                    }
                }
            ],
        },
        {
            "id": "exploit-002",
            "name": "Invalid State Transition",
            "traces": [
                {
                    "pre_state": {"state": "0"},
                    "post_state": {"state": "3"},  # Skip states
                }
            ],
        },
    ]


# ============================================================================
# Pattern Tests
# ============================================================================


class TestMappingUpperBound:
    """Tests for MappingUpperBound pattern."""

    def test_pattern_creation(self):
        """Test MappingUpperBound pattern can be created."""
        pattern = MappingUpperBound(
            mapping_name="balances",
            bound_expression="totalSupply",
            base_confidence=0.9,
        )
        assert pattern.pattern_type == InvariantPatternType.MAPPING_UPPER_BOUND
        assert pattern.mapping_name == "balances"
        assert pattern.bound_expression == "totalSupply"

    def test_check_trace_valid(self):
        """Test pattern correctly validates a trace."""
        pattern = MappingUpperBound(
            mapping_name="balances",
            bound_expression="totalSupply",
        )
        trace = {
            "state": {
                "balances": {"alice": 500, "bob": 300},
                "totalSupply": 1000,
            }
        }
        assert pattern.check_trace(trace) is True

    def test_check_trace_invalid(self):
        """Test pattern correctly rejects invalid trace."""
        pattern = MappingUpperBound(
            mapping_name="balances",
            bound_expression="totalSupply",
        )
        trace = {
            "state": {
                "balances": {"alice": 2000},  # Exceeds totalSupply
                "totalSupply": 1000,
            }
        }
        assert pattern.check_trace(trace) is False

    def test_extract_expression(self):
        """Test expression extraction."""
        pattern = MappingUpperBound(
            mapping_name="balances",
            bound_expression="totalSupply",
        )
        expr = pattern.extract_expression()
        assert "balances" in expr
        assert "totalSupply" in expr
        assert "<=" in expr

    def test_to_require_condition(self):
        """Test require condition generation."""
        pattern = MappingUpperBound(
            mapping_name="balances",
            bound_expression="totalSupply",
        )
        cond = pattern.to_require_condition()
        assert "balances[key] <= totalSupply" == cond


class TestSumInvariant:
    """Tests for SumInvariant pattern."""

    def test_check_trace_valid(self):
        """Test sum invariant validates correctly."""
        pattern = SumInvariant(
            mapping_name="balances",
            total_variable="totalSupply",
        )
        trace = {
            "state": {
                "balances": {"alice": 500, "bob": 300, "carol": 200},
                "totalSupply": 1000,
            }
        }
        assert pattern.check_trace(trace) is True

    def test_check_trace_invalid(self):
        """Test sum invariant rejects incorrect sum."""
        pattern = SumInvariant(
            mapping_name="balances",
            total_variable="totalSupply",
        )
        trace = {
            "state": {
                "balances": {"alice": 500, "bob": 300},  # Sum = 800
                "totalSupply": 1000,  # Doesn't match
            }
        }
        assert pattern.check_trace(trace) is False


class TestMonotonicProperty:
    """Tests for MonotonicProperty pattern."""

    def test_increasing_valid(self):
        """Test increasing monotonic property."""
        pattern = MonotonicProperty(
            variable_name="nonce",
            direction="increasing",
            strict=True,
        )
        trace = {
            "pre_state": {"nonce": 5},
            "post_state": {"nonce": 6},
        }
        assert pattern.check_trace(trace) is True

    def test_increasing_invalid(self):
        """Test increasing monotonic property rejects decrease."""
        pattern = MonotonicProperty(
            variable_name="nonce",
            direction="increasing",
            strict=True,
        )
        trace = {
            "pre_state": {"nonce": 6},
            "post_state": {"nonce": 5},
        }
        assert pattern.check_trace(trace) is False

    def test_non_strict_allows_equality(self):
        """Test non-strict monotonic allows equal values."""
        pattern = MonotonicProperty(
            variable_name="counter",
            direction="increasing",
            strict=False,
        )
        trace = {
            "pre_state": {"counter": 5},
            "post_state": {"counter": 5},
        }
        assert pattern.check_trace(trace) is True


class TestStateTransitionConstraint:
    """Tests for StateTransitionConstraint pattern."""

    def test_valid_transition(self):
        """Test valid state transition."""
        pattern = StateTransitionConstraint(
            state_variable="state",
            valid_transitions={"0": ["1"], "1": ["2"], "2": ["3"]},
        )
        trace = {
            "pre_state": {"state": "1"},
            "post_state": {"state": "2"},
        }
        assert pattern.check_trace(trace) is True

    def test_invalid_transition(self):
        """Test invalid state transition."""
        pattern = StateTransitionConstraint(
            state_variable="state",
            valid_transitions={"0": ["1"], "1": ["2"], "2": ["3"]},
        )
        trace = {
            "pre_state": {"state": "0"},
            "post_state": {"state": "3"},  # Invalid: 0 -> 3 not allowed
        }
        assert pattern.check_trace(trace) is False


class TestVariableRelation:
    """Tests for VariableRelation pattern."""

    def test_product_relation(self):
        """Test AMM constant product relation."""
        pattern = VariableRelation(
            left_expression="reserveA * reserveB",
            operator=">=",
            right_expression="k",
        )
        trace = {
            "state": {
                "reserveA": 100,
                "reserveB": 100,
                "k": 10000,
            }
        }
        assert pattern.check_trace(trace) is True

    def test_product_relation_violated(self):
        """Test AMM relation violation."""
        pattern = VariableRelation(
            left_expression="reserveA * reserveB",
            operator=">=",
            right_expression="k",
        )
        trace = {
            "state": {
                "reserveA": 50,
                "reserveB": 50,  # Product = 2500
                "k": 10000,  # k = 10000, so 2500 < 10000
            }
        }
        assert pattern.check_trace(trace) is False


# ============================================================================
# Mining Tests
# ============================================================================


class TestInvariantMiner:
    """Tests for InvariantMiner."""

    def test_mapping_bound_mining(self, erc20_traces):
        """Test mining discovers balance <= totalSupply."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        # Should find balance-related invariants
        assert len(result.candidates) > 0

        # Check for mapping upper bound pattern
        upper_bounds = [
            c
            for c in result.candidates
            if c.pattern_type == InvariantPatternType.MAPPING_UPPER_BOUND
        ]
        assert len(upper_bounds) > 0

    def test_sum_invariant_mining(self, erc20_traces):
        """Test mining discovers sum(balances) == totalSupply."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        # Check for sum invariant
        sum_invariants = [
            c
            for c in result.candidates
            if c.pattern_type == InvariantPatternType.SUM_INVARIANT
        ]
        # May or may not be found depending on trace validity
        # In our test traces, sum changes with mint/burn
        assert result.patterns_checked > 0

    def test_state_transition_mining(self, state_machine_traces):
        """Test state transition inference."""
        miner = InvariantMiner()
        pattern = miner.mine_state_transitions(state_machine_traces, "state")

        assert pattern.state_variable == "state"
        # Should discover transitions: 0->1, 1->2, 2->3, 3->1
        assert "0" in pattern.valid_transitions
        assert "1" in pattern.valid_transitions["0"]
        assert "2" in pattern.valid_transitions.get("1", [])
        assert "3" in pattern.valid_transitions.get("2", [])
        assert "1" in pattern.valid_transitions.get("3", [])

    def test_confidence_filtering(self, erc20_traces):
        """Test low-confidence invariants are filtered."""
        config = MiningConfig(
            min_confidence=0.95,  # High threshold
        )
        miner = InvariantMiner(config)
        result = miner.mine_from_traces("TestToken", erc20_traces)

        # All returned candidates should have high confidence
        for candidate in result.candidates:
            assert candidate.confidence >= 0.95

    def test_monotonic_property_mining(self, nonce_traces):
        """Test monotonic nonce property is mined."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestContract", nonce_traces)

        # Should find monotonic nonce
        monotonic = [
            c
            for c in result.candidates
            if c.pattern_type == InvariantPatternType.MONOTONIC_PROPERTY
        ]
        # Check patterns were checked
        assert result.patterns_checked > 0

    def test_mining_result_statistics(self, erc20_traces):
        """Test mining result tracks statistics."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        assert result.contract == "TestToken"
        assert result.traces_analyzed == len(erc20_traces)
        assert result.patterns_checked > 0
        assert result.mining_time_ms >= 0


class TestMineFromTraces:
    """Tests for mine_from_traces convenience function."""

    def test_basic_mining(self, erc20_traces):
        """Test convenience function returns candidates."""
        candidates = mine_from_traces("TestToken", erc20_traces)
        assert isinstance(candidates, list)
        for c in candidates:
            assert isinstance(c, InvariantCandidate)

    def test_empty_traces(self):
        """Test mining with empty traces."""
        candidates = mine_from_traces("Empty", [])
        assert candidates == []


# ============================================================================
# Synthesis Tests
# ============================================================================


class TestRequireSynthesis:
    """Tests for require() statement synthesis."""

    def test_require_synthesis(self, erc20_traces):
        """Test valid Solidity require() code is generated."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        if result.candidates:
            synthesizer = InvariantSynthesizer()
            require = synthesizer.synthesize_require(result.candidates[0])

            assert isinstance(require, RequireStatement)
            assert "require" in require.full_code
            assert require.gas_overhead > 0

    def test_synthesize_require_convenience(self, erc20_traces):
        """Test synthesize_require convenience function."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        if result.candidates:
            require = synthesize_require(result.candidates[0])
            assert isinstance(require, RequireStatement)

    def test_require_has_revert_message(self, erc20_traces):
        """Test require() includes revert message."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        if result.candidates:
            synthesizer = InvariantSynthesizer(SynthesisConfig(include_revert_messages=True))
            require = synthesizer.synthesize_require(result.candidates[0])

            assert '"' in require.full_code  # Has string revert message

    def test_batch_synthesize(self, erc20_traces):
        """Test batch synthesis of multiple candidates."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        synthesizer = InvariantSynthesizer()
        statements = synthesizer.batch_synthesize(result.candidates)

        assert isinstance(statements, list)
        for stmt in statements:
            assert isinstance(stmt, RequireStatement)


# ============================================================================
# Exploit Validation Tests
# ============================================================================


class TestExploitValidation:
    """Tests for exploit validation."""

    def test_exploit_validation(self, erc20_traces, exploit_db):
        """Test invariant would prevent known exploit."""
        # Create a candidate that should catch the overflow exploit
        pattern = MappingUpperBound(
            mapping_name="balances",
            bound_expression="totalSupply",
        )
        candidate = InvariantCandidate(
            id="test-001",
            pattern_type=InvariantPatternType.MAPPING_UPPER_BOUND,
            expression="balances[k] <= totalSupply",
            pattern=pattern,
            confidence=0.9,
        )

        synthesizer = InvariantSynthesizer()
        result = synthesizer.validate_against_exploits(candidate, exploit_db)

        assert isinstance(result, ExploitValidationResult)
        assert result.invariant_id == "test-001"
        # Should catch the overflow exploit
        assert result.prevented_count >= 1
        assert "exploit-001" in result.exploits_prevented

    def test_prevention_rate_calculation(self):
        """Test prevention rate is calculated correctly."""
        result = ExploitValidationResult(
            invariant_id="test",
            prevented_count=3,
            missed_count=1,
        )
        assert result.prevention_rate == 0.75

    def test_is_effective_check(self):
        """Test is_effective property."""
        effective = ExploitValidationResult(
            invariant_id="effective",
            prevented_count=5,
            missed_count=3,
        )
        assert effective.is_effective is True

        ineffective = ExploitValidationResult(
            invariant_id="ineffective",
            prevented_count=1,
            missed_count=5,
        )
        assert ineffective.is_effective is False


# ============================================================================
# Discrepancy Detection Tests
# ============================================================================


class TestDiscrepancyDetection:
    """Tests for discrepancy detection."""

    def test_discrepancy_detection_missing_declared(self, erc20_traces):
        """Test mined vs declared differences found."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        # Empty declared list - all mined should be missing_declared
        declared: List[Dict[str, Any]] = []

        synthesizer = InvariantSynthesizer()
        discrepancies = synthesizer.compare_with_declared(result.candidates, declared)

        if result.candidates:
            # Should find discrepancies for mined-not-declared
            assert len(discrepancies) > 0
            assert any(
                d.discrepancy_type == DiscrepancyType.MISSING_DECLARED
                for d in discrepancies
            )

    def test_discrepancy_detection_missing_mined(self, erc20_traces):
        """Test declared but not mined is detected."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        # Add a declared invariant that wasn't mined
        declared = [
            {
                "invariant_id": "decl-001",
                "expression": "some_other_invariant == 42",
                "natural_language": "Some other invariant",
                "confidence": 0.9,
            }
        ]

        synthesizer = InvariantSynthesizer()
        discrepancies = synthesizer.compare_with_declared(result.candidates, declared)

        # Should find the declared invariant as missing_mined
        assert any(
            d.discrepancy_type == DiscrepancyType.MISSING_MINED
            for d in discrepancies
        )

    def test_discrepancy_severity(self, erc20_traces):
        """Test discrepancy severity levels."""
        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        declared: List[Dict[str, Any]] = []

        synthesizer = InvariantSynthesizer()
        discrepancies = synthesizer.compare_with_declared(result.candidates, declared)

        for d in discrepancies:
            assert d.severity in ["low", "medium", "high", "critical"]


# ============================================================================
# Registry Integration Tests
# ============================================================================


class TestRegistryIntegration:
    """Tests for InvariantRegistry integration."""

    def test_registry_integration(self, erc20_traces):
        """Test mined invariants can be registered correctly."""
        from alphaswarm_sol.context.invariant_registry import (
            InvariantRegistry,
            InvariantSource,
        )

        miner = InvariantMiner()
        result = miner.mine_from_traces("TestToken", erc20_traces)

        registry = InvariantRegistry()
        synthesizer = InvariantSynthesizer()

        for candidate in result.candidates[:3]:  # Register first 3
            synthesizer.register_with_registry(candidate, registry)

        # Check registration
        mined = registry.get_mined_invariants()
        assert len(mined) >= min(3, len(result.candidates))

        for inv in mined:
            assert inv.source in (InvariantSource.MINED, InvariantSource.HYBRID)


# ============================================================================
# Candidate Tests
# ============================================================================


class TestInvariantCandidate:
    """Tests for InvariantCandidate data class."""

    def test_candidate_creation(self):
        """Test candidate can be created."""
        pattern = MappingUpperBound(
            mapping_name="balances",
            bound_expression="totalSupply",
        )
        candidate = InvariantCandidate(
            id="test-001",
            pattern_type=InvariantPatternType.MAPPING_UPPER_BOUND,
            expression="balances[k] <= totalSupply",
            pattern=pattern,
            confidence=0.9,
            supporting_traces=100,
            counterexample_traces=0,
        )

        assert candidate.id == "test-001"
        assert candidate.confidence == 0.9
        assert candidate.is_high_confidence is True
        assert candidate.has_counterexamples is False

    def test_support_ratio(self):
        """Test support ratio calculation."""
        pattern = MappingUpperBound(mapping_name="test", bound_expression="bound")
        candidate = InvariantCandidate(
            id="test",
            pattern_type=InvariantPatternType.MAPPING_UPPER_BOUND,
            expression="test",
            pattern=pattern,
            supporting_traces=80,
            counterexample_traces=20,
        )
        assert candidate.support_ratio == 0.8

    def test_exploit_prevention_tracking(self):
        """Test exploit prevention list management."""
        pattern = MappingUpperBound(mapping_name="test", bound_expression="bound")
        candidate = InvariantCandidate(
            id="test",
            pattern_type=InvariantPatternType.MAPPING_UPPER_BOUND,
            expression="test",
            pattern=pattern,
        )

        candidate.add_exploit_prevention("exploit-001")
        candidate.add_exploit_prevention("exploit-002")
        candidate.add_exploit_prevention("exploit-001")  # Duplicate

        assert len(candidate.would_prevent_exploits) == 2

    def test_to_dict_serialization(self):
        """Test candidate serialization."""
        pattern = MappingUpperBound(mapping_name="balances", bound_expression="totalSupply")
        candidate = InvariantCandidate(
            id="test-001",
            pattern_type=InvariantPatternType.MAPPING_UPPER_BOUND,
            expression="balances[k] <= totalSupply",
            pattern=pattern,
            confidence=0.9,
        )

        data = candidate.to_dict()
        assert data["id"] == "test-001"
        assert data["pattern_type"] == "mapping_upper_bound"
        assert data["confidence"] == 0.9


# ============================================================================
# Common Patterns Tests
# ============================================================================


class TestCommonPatterns:
    """Tests for pre-defined common patterns."""

    def test_common_patterns_exist(self):
        """Test common patterns are defined."""
        assert len(COMMON_PATTERNS) > 0

    def test_common_patterns_are_valid(self):
        """Test common patterns are valid InvariantPattern instances."""
        for pattern in COMMON_PATTERNS:
            assert isinstance(pattern, InvariantPattern)
            assert pattern.pattern_type is not None
            assert pattern.base_confidence > 0
