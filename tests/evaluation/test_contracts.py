"""Tests for 3.1c-06 evaluation contracts and contract loader.

Verifies:
- All contracts load without error and validate against hardened JSON schema
- 51 total contracts exist (10 original + 41 new)
- Core tier contracts have ground_truth_rubric and active_dimensions
- Schema hardening: evaluation_config required with 4 sub-fields
- Dimension registry exists with 27+ dimensions
- Debrief-mode validator rejects incompatible combinations
- Process/Outcome boundary: zero detection-outcome violations
- Contract loader API works correctly
- Templates load and generate correctly
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from alphaswarm_sol.testing.evaluation.contract_loader import (
    _validate_debrief_mode_compatibility,
    _validate_stub_reasoning,
    generate_from_template,
    list_contracts,
    list_templates,
    load_contract,
    load_template,
    validate_contract,
    validate_mapping_completeness,
)

CONTRACTS_DIR = (
    Path(__file__).parents[2]
    / "src"
    / "alphaswarm_sol"
    / "testing"
    / "evaluation"
    / "contracts"
)


# ---------------------------------------------------------------------------
# Core contracts
# ---------------------------------------------------------------------------

CORE_CONTRACTS = [
    "agent-vrs-attacker",
    "agent-vrs-defender",
    "agent-vrs-verifier",
    "agent-vrs-secure-reviewer",
    "skill-vrs-audit",
    "skill-vrs-verify",
    "skill-vrs-investigate",
    "skill-vrs-debate",
    "orchestrator-full-audit",
    "skill-vrs-tool-slither",
]


class TestCoreContracts:
    """All 10 Core contracts must load and be valid."""

    @pytest.mark.parametrize("workflow_id", CORE_CONTRACTS)
    def test_contract_loads(self, workflow_id: str):
        contract = load_contract(workflow_id)
        assert contract["workflow_id"] == workflow_id

    @pytest.mark.parametrize("workflow_id", CORE_CONTRACTS)
    def test_contract_has_required_fields(self, workflow_id: str):
        contract = load_contract(workflow_id)
        assert "category" in contract
        assert "grader_type" in contract
        assert "rule_refs" in contract
        assert len(contract["rule_refs"]) > 0
        assert "capability_checks" in contract
        assert len(contract["capability_checks"]) > 0

    @pytest.mark.parametrize("workflow_id", CORE_CONTRACTS)
    def test_contract_validates_against_schema(self, workflow_id: str):
        contract = load_contract(workflow_id)
        errors = validate_contract(contract)
        assert errors == [], f"Validation errors for {workflow_id}: {errors}"

    @pytest.mark.parametrize("workflow_id", CORE_CONTRACTS)
    def test_capability_checks_have_required_fields(self, workflow_id: str):
        contract = load_contract(workflow_id)
        for check in contract["capability_checks"]:
            assert "id" in check, f"Missing id in check for {workflow_id}"
            assert "description" in check
            assert "expected_behavior" in check
            assert "grader_type" in check
            assert check["grader_type"] in ("code", "model")


class TestContractCategories:
    """Verify correct categories assigned."""

    def test_agent_contracts(self):
        for wf_id in ["agent-vrs-attacker", "agent-vrs-defender",
                       "agent-vrs-verifier", "agent-vrs-secure-reviewer"]:
            contract = load_contract(wf_id)
            assert contract["category"] == "agent"

    def test_orchestrator_contracts(self):
        for wf_id in ["skill-vrs-audit", "skill-vrs-verify",
                       "skill-vrs-debate", "orchestrator-full-audit"]:
            contract = load_contract(wf_id)
            assert contract["category"] == "orchestrator"


# ---------------------------------------------------------------------------
# Contract loader API
# ---------------------------------------------------------------------------


class TestContractLoaderAPI:
    def test_list_contracts(self):
        contracts = list_contracts()
        assert len(contracts) >= 10
        assert "agent-vrs-attacker" in contracts

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            load_contract("nonexistent-workflow")

    def test_list_excludes_underscore_files(self):
        contracts = list_contracts()
        for c in contracts:
            assert not c.startswith("_")


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


TEMPLATES = ["investigation", "tool", "orchestration", "support"]


class TestTemplates:
    def test_list_templates(self):
        templates = list_templates()
        assert len(templates) >= 4
        for t in TEMPLATES:
            assert t in templates

    @pytest.mark.parametrize("template_name", TEMPLATES)
    def test_template_loads(self, template_name: str):
        template = load_template(template_name)
        assert "_template" in template
        assert "capability_checks" in template

    def test_load_nonexistent_template(self):
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent")


class TestGenerateFromTemplate:
    def test_basic_generation(self):
        contract = generate_from_template("support", "skill-vrs-health-check")
        assert contract["workflow_id"] == "skill-vrs-health-check"
        assert "_template" not in contract  # Template metadata removed
        assert "capability_checks" in contract

    def test_override_fields(self):
        contract = generate_from_template(
            "tool",
            "skill-vrs-tool-aderyn",
            overrides={"grader_type": "code"},
        )
        assert contract["grader_type"] == "code"

    def test_extend_lists(self):
        contract = generate_from_template(
            "investigation",
            "agent-custom",
            overrides={
                "reasoning_dimensions": ["custom_dimension"],
            },
        )
        # Should extend, not replace
        assert "graph_utilization" in contract["reasoning_dimensions"]
        assert "custom_dimension" in contract["reasoning_dimensions"]

    def test_generated_contract_validates(self):
        contract = generate_from_template("support", "skill-vrs-health-check")
        errors = validate_contract(contract)
        assert errors == [], f"Validation errors: {errors}"


# ---------------------------------------------------------------------------
# Validation edge cases
# ---------------------------------------------------------------------------


class TestValidation:
    def test_missing_workflow_id(self):
        contract = {"category": "agent", "rule_refs": ["X"], "capability_checks": [
            {"id": "a", "description": "b", "expected_behavior": "c", "grader_type": "code"}
        ], "grader_type": "code", "evaluation_config": {"run_gvs": False, "run_reasoning": False, "debrief": False, "depth": "shallow"}, "hooks": ["Stop"], "status": "stub"}
        errors = validate_contract(contract)
        assert len(errors) > 0

    def test_empty_rule_refs(self):
        contract = {
            "workflow_id": "test",
            "category": "agent",
            "rule_refs": [],
            "capability_checks": [
                {"id": "a", "description": "b", "expected_behavior": "c", "grader_type": "code"}
            ],
            "grader_type": "code",
            "evaluation_config": {"run_gvs": False, "run_reasoning": False, "debrief": False, "depth": "shallow"},
            "hooks": ["Stop"],
            "status": "stub",
        }
        errors = validate_contract(contract)
        assert len(errors) > 0  # minItems: 1

    def test_invalid_category(self):
        contract = {
            "workflow_id": "test",
            "category": "invalid",
            "rule_refs": ["X"],
            "capability_checks": [
                {"id": "a", "description": "b", "expected_behavior": "c", "grader_type": "code"}
            ],
            "grader_type": "code",
            "evaluation_config": {"run_gvs": False, "run_reasoning": False, "debrief": False, "depth": "shallow"},
            "hooks": ["Stop"],
            "status": "stub",
        }
        errors = validate_contract(contract)
        assert len(errors) > 0

    def test_missing_evaluation_config_rejected(self):
        """Schema hardening: evaluation_config is required."""
        contract = {
            "workflow_id": "test",
            "category": "agent",
            "rule_refs": ["X"],
            "capability_checks": [
                {"id": "a", "description": "b", "expected_behavior": "c", "grader_type": "code"}
            ],
            "grader_type": "code",
            "hooks": ["Stop"],
            "status": "stub",
        }
        errors = validate_contract(contract)
        assert len(errors) > 0
        assert any("evaluation_config" in e for e in errors)

    def test_empty_evaluation_config_rejected(self):
        """Schema hardening: evaluation_config must have 4 required sub-fields."""
        contract = {
            "workflow_id": "test",
            "category": "agent",
            "rule_refs": ["X"],
            "capability_checks": [
                {"id": "a", "description": "b", "expected_behavior": "c", "grader_type": "code"}
            ],
            "grader_type": "code",
            "evaluation_config": {},
            "hooks": ["Stop"],
            "status": "stub",
        }
        errors = validate_contract(contract)
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Debrief-mode validator (P11-ADV-4-01)
# ---------------------------------------------------------------------------


class TestDebriefModeValidator:
    def test_standard_tier_debrief_true_rejected(self):
        contract = {
            "workflow_id": "test",
            "evaluation_config": {"debrief": True},
            "metadata": {"tier": "standard"},
        }
        errors = _validate_debrief_mode_compatibility(contract)
        assert len(errors) == 1
        assert "Standard-tier" in errors[0]

    def test_headless_debrief_true_rejected(self):
        contract = {
            "workflow_id": "test",
            "evaluation_config": {"debrief": True, "run_mode": "headless"},
        }
        errors = _validate_debrief_mode_compatibility(contract)
        assert len(errors) == 1
        assert "headless" in errors[0]

    def test_core_tier_debrief_true_allowed(self):
        contract = {
            "workflow_id": "test",
            "evaluation_config": {"debrief": True},
            "metadata": {"tier": "core"},
        }
        errors = _validate_debrief_mode_compatibility(contract)
        assert errors == []

    def test_debrief_false_always_ok(self):
        contract = {
            "workflow_id": "test",
            "evaluation_config": {"debrief": False},
            "metadata": {"tier": "standard"},
        }
        errors = _validate_debrief_mode_compatibility(contract)
        assert errors == []


# ---------------------------------------------------------------------------
# Stub reasoning validator (P15-IMP-03)
# ---------------------------------------------------------------------------


class TestStubReasoningValidator:
    def test_run_reasoning_true_empty_dims_rejected(self):
        contract = {
            "workflow_id": "test",
            "evaluation_config": {"run_reasoning": True},
            "reasoning_dimensions": [],
        }
        errors = _validate_stub_reasoning(contract)
        assert len(errors) == 1

    def test_run_reasoning_false_empty_dims_ok(self):
        contract = {
            "workflow_id": "test",
            "evaluation_config": {"run_reasoning": False},
            "reasoning_dimensions": [],
        }
        errors = _validate_stub_reasoning(contract)
        assert errors == []

    def test_run_reasoning_true_with_dims_ok(self):
        contract = {
            "workflow_id": "test",
            "evaluation_config": {"run_reasoning": True},
            "reasoning_dimensions": ["graph_utilization"],
        }
        errors = _validate_stub_reasoning(contract)
        assert errors == []


# ---------------------------------------------------------------------------
# Dimension registry
# ---------------------------------------------------------------------------


class TestDimensionRegistry:
    @pytest.fixture(scope="class")
    def registry(self):
        path = CONTRACTS_DIR / "dimension_registry.yaml"
        assert path.exists(), "dimension_registry.yaml must exist"
        with open(path) as f:
            return yaml.safe_load(f)

    def test_has_27_plus_dimensions(self, registry):
        dims = registry.get("dimensions", [])
        assert len(dims) >= 27, f"Expected 27+ dimensions, got {len(dims)}"

    def test_dimensions_have_required_fields(self, registry):
        for dim in registry["dimensions"]:
            assert "name" in dim, f"Missing name in dimension: {dim}"
            assert "description" in dim, f"Missing description for {dim.get('name', '?')}"
            assert "has_handler" in dim, f"Missing has_handler for {dim['name']}"
            assert isinstance(dim["has_handler"], bool)

    def test_canonical_move_types(self, registry):
        expected = {
            "HYPOTHESIS_FORMATION", "QUERY_FORMULATION", "RESULT_INTERPRETATION",
            "EVIDENCE_INTEGRATION", "CONTRADICTION_HANDLING", "CONCLUSION_SYNTHESIS",
            "SELF_CRITIQUE",
        }
        actual = set(registry.get("canonical_move_types", []))
        assert actual == expected

    def test_known_dimensions_present(self, registry):
        names = {d["name"] for d in registry["dimensions"]}
        required = {
            "graph_utilization", "evidence_quality", "tool_selection",
            "coordination_quality", "evidence_flow", "finding_quality",
            "completeness", "error_handling", "arbitration_quality",
            "consensus_quality",
        }
        missing = required - names
        assert not missing, f"Missing dimensions: {missing}"


# ---------------------------------------------------------------------------
# Contract count and tiering (Plan 06 deliverables)
# ---------------------------------------------------------------------------


class TestContractCount:
    def test_at_least_51_contracts(self):
        contracts = list_contracts()
        assert len(contracts) >= 51, f"Expected 51+ contracts, got {len(contracts)}"

    def test_original_10_still_present(self):
        contracts = set(list_contracts())
        originals = {
            "agent-vrs-attacker", "agent-vrs-defender", "agent-vrs-verifier",
            "agent-vrs-secure-reviewer", "orchestrator-full-audit", "skill-vrs-audit",
            "skill-vrs-debate", "skill-vrs-investigate", "skill-vrs-tool-slither",
            "skill-vrs-verify",
        }
        missing = originals - contracts
        assert not missing, f"Missing original contracts: {missing}"


class TestAllContractsValidate:
    """Every contract file must validate against the hardened schema."""

    def test_all_contracts_schema_valid(self):
        contracts = list_contracts()
        failures = []
        for wf_id in contracts:
            contract = load_contract(wf_id)
            errors = validate_contract(contract)
            if errors:
                failures.append(f"{wf_id}: {errors}")
        assert not failures, f"Validation failures:\n" + "\n".join(failures)


class TestCoreTierContracts:
    """Core contracts must have ground_truth_rubric and active_dimensions."""

    def test_core_contracts_have_rubric(self):
        contracts = list_contracts()
        for wf_id in contracts:
            contract = load_contract(wf_id)
            tier = contract.get("metadata", {}).get("tier", "")
            if tier == "core":
                rubric = contract.get("ground_truth_rubric", "")
                assert rubric, f"Core contract {wf_id} missing ground_truth_rubric"

    def test_core_contracts_have_active_dimensions(self):
        contracts = list_contracts()
        for wf_id in contracts:
            contract = load_contract(wf_id)
            tier = contract.get("metadata", {}).get("tier", "")
            if tier == "core":
                dims = contract.get("active_dimensions", [])
                assert len(dims) >= 8, (
                    f"Core contract {wf_id} has {len(dims)} active_dimensions, need 8-12"
                )


class TestProcessOutcomeBoundary:
    """Zero detection-outcome violations across all contracts."""

    PROHIBITED_FIELDS = {"findings_count", "vulnerabilities_found"}
    OUTCOME_PHRASES = ["find ", "detect ", "identify the vulnerability"]

    def test_no_detection_outcome_capability_checks(self):
        """No capability check uses findings_count or vulnerabilities_found."""
        contracts = list_contracts()
        violations = []
        for wf_id in contracts:
            contract = load_contract(wf_id)
            for check in contract.get("capability_checks", []):
                check_id = check.get("id", "")
                expected = check.get("expected_behavior", "")
                if check_id in self.PROHIBITED_FIELDS:
                    violations.append(f"{wf_id}: check id '{check_id}'")
                for field_name in self.PROHIBITED_FIELDS:
                    if field_name in expected:
                        violations.append(
                            f"{wf_id}: expected_behavior references '{field_name}'"
                        )
        assert not violations, (
            "Detection-outcome violations in capability checks:\n"
            + "\n".join(violations)
        )

    def test_no_detection_outcome_in_rubric(self):
        """Rubric text must not contain detection-outcome phrases."""
        contracts = list_contracts()
        violations = []
        for wf_id in contracts:
            contract = load_contract(wf_id)
            rubric = contract.get("ground_truth_rubric", "")
            if not rubric:
                continue
            rubric_lower = rubric.lower()
            for phrase in self.OUTCOME_PHRASES:
                if phrase in rubric_lower:
                    violations.append(f"{wf_id}: rubric contains '{phrase.strip()}'")
        assert not violations, (
            "Detection-outcome phrases in rubric text:\n"
            + "\n".join(violations)
        )
