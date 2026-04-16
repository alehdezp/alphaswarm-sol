"""Tests for economic prompt contracts and validation.

Per 05.11-05-PLAN.md: Comprehensive validation tests for enhanced prompt contracts
covering basic economic context, causal chains, counterfactuals, and cross-protocol
awareness.

Tests:
1. Basic economic context - lens tags, provenance, expectation dates
2. Causal chain - completeness, probability, validation failures
3. Counterfactual - minimum count, scenario types, evidence refs
4. Cross-protocol - dependency notation, systemic risk mentions
5. Integration - full contract builds, validator catches all failures
"""

import pytest

from alphaswarm_sol.agents.prompts.economic_contract import (
    LensTag,
    CausalChainElement,
    CounterfactualScenario,
    ValidationResult,
    PromptValidator,
    EconomicPromptContract,
)
from alphaswarm_sol.economics.payoff import (
    AttackPayoff,
    DefensePayoff,
    PayoffMatrix,
)


# =============================================================================
# Basic Economic Context Tests
# =============================================================================


class TestLensTag:
    """Tests for LensTag enum and parsing."""

    def test_all_lens_tags_exist(self):
        """All 6 lens tags are defined."""
        assert len(LensTag.all_tags()) == 6
        assert LensTag.VALUE in LensTag.all_tags()
        assert LensTag.CONTROL in LensTag.all_tags()
        assert LensTag.INCENTIVE in LensTag.all_tags()
        assert LensTag.TRUST in LensTag.all_tags()
        assert LensTag.TIMING in LensTag.all_tags()
        assert LensTag.CONFIG in LensTag.all_tags()

    def test_from_string_case_insensitive(self):
        """LensTag.from_string handles case insensitivity."""
        assert LensTag.from_string("VALUE") == LensTag.VALUE
        assert LensTag.from_string("value") == LensTag.VALUE
        assert LensTag.from_string("Value") == LensTag.VALUE

    def test_from_string_aliases(self):
        """LensTag.from_string handles common aliases."""
        assert LensTag.from_string("economic") == LensTag.VALUE
        assert LensTag.from_string("access") == LensTag.CONTROL
        assert LensTag.from_string("profit") == LensTag.INCENTIVE
        assert LensTag.from_string("oracle") == LensTag.TRUST
        assert LensTag.from_string("delay") == LensTag.TIMING
        assert LensTag.from_string("misconfiguration") == LensTag.CONFIG


class TestLensTagValidation:
    """Tests for lens tag validation in agent outputs."""

    @pytest.fixture
    def validator(self) -> PromptValidator:
        return PromptValidator()

    def test_lens_tags_present_and_valid(self, validator: PromptValidator):
        """Valid lens tags pass validation."""
        output = {
            "lens_tags": ["value", "trust"],
            "severity": "high",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }
        result = validator.validate(output)
        assert result.valid
        assert LensTag.VALUE in result.lens_tags_found
        assert LensTag.TRUST in result.lens_tags_found

    def test_missing_lens_tags_fails_validation(self, validator: PromptValidator):
        """Missing lens tags causes validation failure."""
        output = {
            "description": "Some finding without economic lens",
            "severity": "medium",
        }
        result = validator.validate(output)
        assert not result.valid
        assert any("lens tag" in f.lower() for f in result.failures)

    def test_lens_tags_found_in_text(self, validator: PromptValidator):
        """Lens tags mentioned in text fields are detected."""
        output = {
            "description": "This is a value flow vulnerability with trust issues",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }
        result = validator.validate(output)
        assert result.valid
        assert LensTag.VALUE in result.lens_tags_found
        assert LensTag.TRUST in result.lens_tags_found


# =============================================================================
# Causal Chain Tests
# =============================================================================


class TestCausalChainElement:
    """Tests for CausalChainElement dataclass."""

    def test_valid_chain_element(self):
        """Valid chain element is created successfully."""
        elem = CausalChainElement(
            step_type="root_cause",
            description="Oracle price not validated",
            evidence_refs=["EVD-12345678"],
            probability=1.0,
            node_id="func_Vault_liquidate",
        )
        assert elem.step_type == "root_cause"
        assert elem.probability == 1.0
        assert len(elem.evidence_refs) == 1

    def test_invalid_step_type_raises(self):
        """Invalid step type raises ValueError."""
        with pytest.raises(ValueError, match="step_type must be one of"):
            CausalChainElement(
                step_type="invalid_type",
                description="Some description",
            )

    def test_invalid_probability_raises(self):
        """Probability outside 0-1 raises ValueError."""
        with pytest.raises(ValueError, match="probability must be 0.0-1.0"):
            CausalChainElement(
                step_type="exploit",
                description="Some exploit",
                probability=1.5,
            )

    def test_to_dict_and_from_dict(self):
        """Serialization roundtrip works correctly."""
        elem = CausalChainElement(
            step_type="exploit",
            description="Front-run oracle update",
            evidence_refs=["EVD-87654321"],
            probability=0.8,
        )
        data = elem.to_dict()
        restored = CausalChainElement.from_dict(data)
        assert restored.step_type == elem.step_type
        assert restored.description == elem.description
        assert restored.probability == elem.probability


class TestCausalChainValidation:
    """Tests for causal chain validation."""

    @pytest.fixture
    def validator(self) -> PromptValidator:
        return PromptValidator()

    def test_complete_causal_chain_passes(self, validator: PromptValidator):
        """Complete causal chain with root_cause, exploit, loss passes."""
        output = {
            "lens_tags": ["value"],
            "severity": "high",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }
        result = validator.validate(output)
        assert result.valid
        assert result.causal_chain_valid

    def test_incomplete_chain_missing_root_cause_fails(self, validator: PromptValidator):
        """Chain without root_cause fails for HIGH severity."""
        output = {
            "lens_tags": ["value"],
            "severity": "high",
            "causal_chain": [
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }
        result = validator.validate(output)
        assert not result.valid
        assert any("root_cause" in f for f in result.failures)

    def test_incomplete_chain_missing_loss_fails(self, validator: PromptValidator):
        """Chain without loss element fails for CRITICAL severity."""
        output = {
            "lens_tags": ["value"],
            "severity": "critical",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }
        result = validator.validate(output)
        assert not result.valid
        assert any("loss" in f for f in result.failures)

    def test_low_chain_probability_fails(self, validator: PromptValidator):
        """Chain with probability product < 0.1 fails."""
        output = {
            "lens_tags": ["value"],
            "severity": "high",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 0.2},
                {"step_type": "exploit", "description": "y", "probability": 0.2},
                {"step_type": "loss", "description": "z", "probability": 0.2},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }
        # 0.2 * 0.2 * 0.2 = 0.008 < 0.1
        result = validator.validate(output)
        assert not result.valid
        assert any("probability" in f.lower() for f in result.failures)

    def test_incomplete_chain_warning_for_medium(self, validator: PromptValidator):
        """Incomplete chain for MEDIUM severity is warning, not failure."""
        output = {
            "lens_tags": ["value"],
            "severity": "medium",
            "causal_chain": [
                {"step_type": "exploit", "description": "y", "probability": 0.8},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }
        result = validator.validate(output)
        assert result.valid  # Medium doesn't require complete chain
        assert any("chain" in w.lower() for w in result.warnings)


# =============================================================================
# Counterfactual Tests
# =============================================================================


class TestCounterfactualScenario:
    """Tests for CounterfactualScenario dataclass."""

    def test_valid_counterfactual(self):
        """Valid counterfactual is created successfully."""
        cf = CounterfactualScenario(
            scenario_type="guard_exists",
            description="What if reentrancy guard existed?",
            would_prevent=True,
            impact="Attack blocked at external call",
            evidence_refs=["EVD-12345678"],
        )
        assert cf.scenario_type == "guard_exists"
        assert cf.would_prevent is True

    def test_invalid_scenario_type_raises(self):
        """Invalid scenario type raises ValueError."""
        with pytest.raises(ValueError, match="scenario_type must be one of"):
            CounterfactualScenario(
                scenario_type="invalid_type",
                description="Some description",
                would_prevent=True,
                impact="Some impact",
            )

    def test_all_scenario_types_valid(self):
        """All documented scenario types are valid."""
        valid_types = ["guard_exists", "param_different", "role_change", "timing_change", "invariant_enforced"]
        for st in valid_types:
            cf = CounterfactualScenario(
                scenario_type=st,
                description="Test",
                would_prevent=True,
                impact="Test impact",
            )
            assert cf.scenario_type == st


class TestCounterfactualValidation:
    """Tests for counterfactual validation."""

    @pytest.fixture
    def validator(self) -> PromptValidator:
        return PromptValidator()

    def test_sufficient_counterfactuals_pass(self, validator: PromptValidator):
        """At least 2 counterfactual scenarios passes."""
        output = {
            "lens_tags": ["value"],
            "severity": "medium",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }
        result = validator.validate(output)
        assert result.valid
        assert result.counterfactual_count >= 2

    def test_insufficient_counterfactuals_warning(self, validator: PromptValidator):
        """Less than 2 counterfactuals triggers warning."""
        output = {
            "lens_tags": ["value"],
            "severity": "medium",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
            ],
        }
        result = validator.validate(output)
        assert result.valid  # Not a failure, just a warning
        assert result.counterfactual_count == 1
        assert any("counterfactual" in w.lower() for w in result.warnings)

    def test_missing_counterfactuals_recorded(self, validator: PromptValidator):
        """Missing counterfactuals are recorded correctly."""
        output = {
            "lens_tags": ["value"],
            "severity": "medium",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [],
        }
        result = validator.validate(output)
        assert result.counterfactual_count == 0
        assert any("counterfactual" in w.lower() for w in result.warnings)


# =============================================================================
# Cross-Protocol Tests
# =============================================================================


class TestCrossProtocolValidation:
    """Tests for cross-protocol awareness validation."""

    @pytest.fixture
    def validator(self) -> PromptValidator:
        return PromptValidator()

    def test_cross_protocol_dependencies_noted(self, validator: PromptValidator):
        """Explicit cross-protocol dependencies are detected."""
        output = {
            "lens_tags": ["trust"],
            "severity": "high",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
            "cross_protocol_dependencies": [
                {"protocol": "Chainlink", "dependency_type": "oracle", "criticality": 9},
            ],
        }
        result = validator.validate(output)
        assert result.valid
        assert result.cross_protocol_noted

    def test_systemic_risk_mentioned(self, validator: PromptValidator):
        """Systemic risk mention is detected."""
        output = {
            "lens_tags": ["value"],
            "severity": "high",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
            "systemic_risk_mentioned": True,
        }
        result = validator.validate(output)
        assert result.valid
        assert result.cross_protocol_noted

    def test_cross_protocol_in_text(self, validator: PromptValidator):
        """Cross-protocol keywords in text are detected."""
        output = {
            "lens_tags": ["value"],
            "severity": "medium",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
            "description": "This could cascade to other protocols",
        }
        result = validator.validate(output)
        assert result.cross_protocol_noted

    def test_missing_cross_protocol_is_warning(self, validator: PromptValidator):
        """Missing cross-protocol awareness is a warning, not failure."""
        output = {
            "lens_tags": ["value"],
            "severity": "medium",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }
        result = validator.validate(output)
        assert result.valid  # Not a failure
        assert any("cross-protocol" in w.lower() for w in result.warnings)


# =============================================================================
# Integration Tests
# =============================================================================


class TestEconomicPromptContract:
    """Tests for EconomicPromptContract builder."""

    def test_for_attacker_creates_correct_contract(self):
        """for_attacker creates contract with VALUE, INCENTIVE lenses."""
        attack_payoff = AttackPayoff(
            expected_profit_usd=100000,
            gas_cost_usd=500,
            mev_risk=0.3,
            success_probability=0.7,
        )
        defense_payoff = DefensePayoff(
            detection_probability=0.5,
            mitigation_cost_usd=50000,
        )
        matrix = PayoffMatrix(
            scenario="oracle_manipulation",
            attacker_payoff=attack_payoff,
            defender_payoff=defense_payoff,
            tvl_at_risk_usd=50000000,
        )

        contract = EconomicPromptContract.for_attacker(
            dossier_summary="AMM with $50M TVL",
            passport_snippet="Vault.sol handles ETH custody",
            policy_diff="Expected: onlyOwner, Actual: none",
            attack_ev=matrix,
        )

        assert contract.role == "attacker"
        assert LensTag.VALUE in contract.required_lens_tags
        assert LensTag.INCENTIVE in contract.required_lens_tags
        assert contract.require_causal_chain
        assert contract.require_counterfactuals
        assert contract.attack_ev is not None

    def test_for_defender_creates_correct_contract(self):
        """for_defender creates contract with CONTROL, CONFIG lenses."""
        contract = EconomicPromptContract.for_defender(
            dossier_summary="Lending protocol with governance",
            passport_snippet="Pool.sol handles deposits",
            policy_diff="Expected: 24h timelock, Actual: none",
        )

        assert contract.role == "defender"
        assert LensTag.CONTROL in contract.required_lens_tags
        assert LensTag.CONFIG in contract.required_lens_tags
        assert not contract.require_causal_chain  # Defender doesn't build chains
        assert contract.require_counterfactuals

    def test_for_verifier_creates_correct_contract(self):
        """for_verifier creates contract with chain validation requirement."""
        contract = EconomicPromptContract.for_verifier(
            dossier_summary="DEX with flash loans",
            passport_snippet="Router.sol handles swaps",
        )

        assert contract.role == "verifier"
        assert len(contract.required_lens_tags) == 0  # Verifier validates, doesn't generate
        assert contract.require_causal_chain  # Must validate chains
        assert contract.require_counterfactuals

    def test_build_includes_all_sections(self):
        """build() includes context, requirements, attack EV, and cross-protocol."""
        attack_payoff = AttackPayoff(expected_profit_usd=100000, success_probability=0.7)
        defense_payoff = DefensePayoff(detection_probability=0.5)
        matrix = PayoffMatrix(
            scenario="test",
            attacker_payoff=attack_payoff,
            defender_payoff=defense_payoff,
            tvl_at_risk_usd=1000000,
        )

        contract = EconomicPromptContract(
            role="attacker",
            dossier_summary="Test dossier",
            passport_snippet="Test passport",
            policy_diff="Expected: A, Actual: B",
            attack_ev=matrix,
            cross_protocol_deps=["Chainlink", "Uniswap"],
        )

        prompt = contract.build()

        # All sections present
        assert "Economic Context" in prompt
        assert "Protocol Dossier" in prompt
        assert "Contract Passport" in prompt
        assert "Policy Diff" in prompt
        assert "Output Requirements" in prompt
        assert "Lens Tags" in prompt
        assert "Causal Chain" in prompt
        assert "Counterfactual" in prompt
        assert "Attack Economics" in prompt
        assert "Cross-Protocol Dependencies" in prompt
        assert "Chainlink" in prompt
        assert "Uniswap" in prompt


class TestValidatorIntegration:
    """Integration tests for full validation flow."""

    @pytest.fixture
    def validator(self) -> PromptValidator:
        return PromptValidator()

    def test_fully_valid_output(self, validator: PromptValidator):
        """Complete valid output passes all checks."""
        output = {
            "id": "FIND-001",
            "description": "Oracle price manipulation with value flow impact",
            "severity": "critical",
            "lens_tags": [LensTag.VALUE, LensTag.TRUST],
            "causal_chain": [
                CausalChainElement(
                    step_type="root_cause",
                    description="No staleness check on oracle",
                    evidence_refs=["EVD-001"],
                    probability=1.0,
                ),
                CausalChainElement(
                    step_type="exploit",
                    description="Front-run oracle update",
                    probability=0.8,
                ),
                CausalChainElement(
                    step_type="loss",
                    description="$500k extracted",
                    probability=1.0,
                ),
            ],
            "counterfactuals": [
                CounterfactualScenario(
                    scenario_type="guard_exists",
                    description="Staleness check present",
                    would_prevent=True,
                    impact="Attack blocked",
                ),
                CounterfactualScenario(
                    scenario_type="param_different",
                    description="Heartbeat 10min",
                    would_prevent=False,
                    impact="Window reduced",
                ),
            ],
            "cross_protocol_dependencies": [
                {"protocol": "Chainlink", "dependency_type": "oracle", "criticality": 9},
            ],
            "assumptions": [
                {
                    "description": "Oracle updates within 1 hour",
                    "source_date": "2025-01-15",
                    "source_id": "chainlink-docs",
                },
            ],
        }

        result = validator.validate(output)
        assert result.valid
        assert result.causal_chain_valid
        assert result.counterfactual_count >= 2
        assert result.cross_protocol_noted
        assert len(result.failures) == 0

    def test_multiple_failures_reported(self, validator: PromptValidator):
        """All failures are collected and reported."""
        output = {
            "severity": "critical",
            # Missing: lens_tags, causal_chain, counterfactuals
            "assumptions": [
                {"description": "Some assumption without date"},  # Missing source_date
            ],
        }

        result = validator.validate(output)
        assert not result.valid
        # Should report multiple failures
        assert len(result.failures) >= 2  # lens tags + causal chain + provenance

    def test_validation_result_to_dict(self, validator: PromptValidator):
        """ValidationResult serializes correctly."""
        output = {
            "lens_tags": ["value"],
            "severity": "medium",
            "causal_chain": [
                {"step_type": "root_cause", "description": "x", "probability": 1.0},
                {"step_type": "exploit", "description": "y", "probability": 0.8},
                {"step_type": "loss", "description": "z", "probability": 1.0},
            ],
            "counterfactuals": [
                {"scenario_type": "guard_exists", "description": "a", "would_prevent": True, "impact": "b"},
                {"scenario_type": "param_different", "description": "c", "would_prevent": False, "impact": "d"},
            ],
        }

        result = validator.validate(output)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "valid" in result_dict
        assert "failures" in result_dict
        assert "warnings" in result_dict
        assert "lens_tags_found" in result_dict
        assert "causal_chain_valid" in result_dict
        assert "counterfactual_count" in result_dict
