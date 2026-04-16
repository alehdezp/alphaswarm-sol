"""Tests for evaluation contract schema, sample contracts, and assertion helpers.

Validates:
1. Schema self-validation (JSON Schema Draft 7)
2. All 3 sample contracts pass schema validation
3. Invalid contracts are rejected by schema
4. assert_matches_contract pass and fail cases
5. assert_reasoning_dimensions_covered pass and fail cases
6. Existing assertion categories still work (non-regression)
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tests.workflow_harness.lib.assertions import (
    assert_findings_cite_graph_nodes,
    assert_findings_have_locations,
    assert_matches_contract,
    assert_reasoning_dimensions_covered,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / ".vrs" / "testing" / "schemas" / "evaluation_contract.schema.json"
SAMPLES_DIR = ROOT / ".vrs" / "testing" / "contracts" / "samples"

SAMPLE_FILES = [
    "skill-audit.json",
    "agent-attacker.json",
    "orchestrator-debate.json",
]

# Stable rule IDs from 3.1-04
VALID_RULE_IDS = {
    "EXEC-INTEGRITY", "TRANSCRIPT-AUTH", "METRICS-REALISM",
    "GROUND-TRUTH", "REPORT-INTEGRITY", "DURATION-BOUNDS",
    "EVIDENCE-CHAIN", "GATE-INTEGRITY", "ISOLATION",
    "SESSION-NAMING", "ARTIFACT-PROD", "ARTIFACT-DEP",
    "WAVE-GATE", "TIER-C-GATING", "INFRA-USAGE",
}


@pytest.fixture()
def schema() -> dict:
    """Load the evaluation contract schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture(params=SAMPLE_FILES)
def sample_contract(request: pytest.FixtureRequest) -> dict:
    """Load a sample evaluation contract (parametrized over all 3 samples)."""
    with open(SAMPLES_DIR / request.param) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Schema self-validation
# ---------------------------------------------------------------------------


class TestSchemaValidity:
    """Verify the schema itself is valid JSON Schema Draft 7."""

    def test_schema_is_valid_draft7(self, schema: dict) -> None:
        jsonschema.Draft7Validator.check_schema(schema)

    def test_schema_has_required_fields(self, schema: dict) -> None:
        required = set(schema.get("required", []))
        expected = {"workflow_id", "category", "rule_refs", "capability_checks", "grader_type"}
        assert expected.issubset(required), (
            f"Schema missing required fields: {expected - required}"
        )

    def test_schema_has_category_enum(self, schema: dict) -> None:
        cat_enum = schema["properties"]["category"]["enum"]
        assert set(cat_enum) == {"skill", "agent", "orchestrator"}


# ---------------------------------------------------------------------------
# 2. Sample contracts validate against schema
# ---------------------------------------------------------------------------


class TestSampleContracts:
    """All 3 sample contracts must validate against the schema."""

    def test_contract_validates(self, schema: dict, sample_contract: dict) -> None:
        jsonschema.validate(sample_contract, schema)

    def test_contract_has_min_3_checks(self, sample_contract: dict) -> None:
        checks = sample_contract["capability_checks"]
        assert len(checks) >= 3, (
            f"Contract '{sample_contract['workflow_id']}' has only {len(checks)} "
            f"capability_checks (minimum: 3)"
        )

    def test_checks_have_all_subfields(self, sample_contract: dict) -> None:
        required_subfields = {"id", "description", "expected_behavior", "grader_type"}
        for check in sample_contract["capability_checks"]:
            missing = required_subfields - set(check.keys())
            assert not missing, (
                f"Check '{check.get('id', '?')}' missing subfields: {missing}"
            )

    def test_rule_refs_are_valid(self, sample_contract: dict) -> None:
        for ref in sample_contract["rule_refs"]:
            assert ref in VALID_RULE_IDS, (
                f"rule_ref '{ref}' in '{sample_contract['workflow_id']}' "
                f"is not a valid rule ID from 3.1-04"
            )


# ---------------------------------------------------------------------------
# 3. Invalid contracts are rejected
# ---------------------------------------------------------------------------


class TestInvalidContracts:
    """Schema must reject malformed contracts."""

    def test_missing_workflow_id(self, schema: dict) -> None:
        invalid = {
            "category": "skill",
            "rule_refs": ["EXEC-INTEGRITY"],
            "capability_checks": [
                {"id": "x", "description": "x", "expected_behavior": "x", "grader_type": "code"}
            ],
            "grader_type": "code",
        }
        with pytest.raises(jsonschema.ValidationError, match="workflow_id"):
            jsonschema.validate(invalid, schema)

    def test_empty_capability_checks(self, schema: dict) -> None:
        invalid = {
            "workflow_id": "test",
            "category": "skill",
            "rule_refs": ["EXEC-INTEGRITY"],
            "capability_checks": [],
            "grader_type": "code",
        }
        with pytest.raises(jsonschema.ValidationError, match="minItems"):
            jsonschema.validate(invalid, schema)

    def test_invalid_grader_type(self, schema: dict) -> None:
        invalid = {
            "workflow_id": "test",
            "category": "skill",
            "rule_refs": ["EXEC-INTEGRITY"],
            "capability_checks": [
                {"id": "x", "description": "x", "expected_behavior": "x", "grader_type": "code"}
            ],
            "grader_type": "invalid_grader",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid, schema)

    def test_invalid_category(self, schema: dict) -> None:
        invalid = {
            "workflow_id": "test",
            "category": "invalid_category",
            "rule_refs": ["EXEC-INTEGRITY"],
            "capability_checks": [
                {"id": "x", "description": "x", "expected_behavior": "x", "grader_type": "code"}
            ],
            "grader_type": "code",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid, schema)

    def test_empty_rule_refs(self, schema: dict) -> None:
        invalid = {
            "workflow_id": "test",
            "category": "skill",
            "rule_refs": [],
            "capability_checks": [
                {"id": "x", "description": "x", "expected_behavior": "x", "grader_type": "code"}
            ],
            "grader_type": "code",
        }
        with pytest.raises(jsonschema.ValidationError, match="minItems"):
            jsonschema.validate(invalid, schema)

    def test_lowercase_rule_ref_rejected(self, schema: dict) -> None:
        invalid = {
            "workflow_id": "test",
            "category": "skill",
            "rule_refs": ["exec-integrity"],
            "capability_checks": [
                {"id": "x", "description": "x", "expected_behavior": "x", "grader_type": "code"}
            ],
            "grader_type": "code",
        }
        with pytest.raises(jsonschema.ValidationError, match="pattern"):
            jsonschema.validate(invalid, schema)

    def test_missing_check_subfield(self, schema: dict) -> None:
        invalid = {
            "workflow_id": "test",
            "category": "skill",
            "rule_refs": ["EXEC-INTEGRITY"],
            "capability_checks": [
                {"id": "x", "description": "x"}  # missing expected_behavior and grader_type
            ],
            "grader_type": "code",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid, schema)


# ---------------------------------------------------------------------------
# 4. assert_matches_contract
# ---------------------------------------------------------------------------


class TestAssertMatchesContract:
    """Test the contract-aware assertion helper."""

    @pytest.fixture()
    def audit_contract(self) -> dict:
        with open(SAMPLES_DIR / "skill-audit.json") as f:
            return json.load(f)

    def test_pass_case(self, audit_contract: dict) -> None:
        """Result with all required evidence passes."""
        result = {
            "transcript": "ran build-kg, found issues",
            "evidence_nodes": ["node-1", "node-2"],
            "code_locations": ["/contracts/Vault.sol:42"],
            "findings": [{"id": "finding-1", "pattern": "vm-001"}],
        }
        # Should not raise
        assert_matches_contract(result, audit_contract)

    def test_fail_missing_evidence(self, audit_contract: dict) -> None:
        """Result missing evidence for code-graded check raises AssertionError."""
        result = {
            "transcript": "ran build-kg",
            # missing evidence_nodes, code_locations
        }
        with pytest.raises(AssertionError, match="produces-evidence-findings"):
            assert_matches_contract(result, audit_contract)

    def test_model_graded_checks_skipped(self, audit_contract: dict) -> None:
        """Model-graded checks don't cause failures."""
        # Provide evidence for code-graded checks only
        result = {
            "transcript": "ran build-kg, analyzed contract",
            "evidence_nodes": ["node-1"],
            "code_locations": ["/contracts/Vault.sol:42"],
        }
        # Should not raise even though model-graded check can't be verified
        assert_matches_contract(result, audit_contract)

    def test_empty_contract_checks_raises(self) -> None:
        """Contract with no capability_checks raises."""
        contract = {
            "workflow_id": "test",
            "capability_checks": [],
        }
        with pytest.raises(AssertionError, match="no capability_checks"):
            assert_matches_contract({}, contract)

    def test_attacker_contract_pass(self) -> None:
        """Agent-attacker contract passes with proper evidence."""
        with open(SAMPLES_DIR / "agent-attacker.json") as f:
            contract = json.load(f)
        result = {
            "transcript": "queried BSKG for access control patterns",
            "attack_vectors": [{"id": "v1", "graph_node_ids": ["n1"]}],
            "exploit_path": [{"step": 1, "function": "withdraw"}],
            "graph_node_ids": ["n1", "n2"],
        }
        assert_matches_contract(result, contract)


# ---------------------------------------------------------------------------
# 5. assert_reasoning_dimensions_covered
# ---------------------------------------------------------------------------


class TestAssertReasoningDimensionsCovered:
    """Test the reasoning dimension coverage helper."""

    @pytest.fixture()
    def audit_contract(self) -> dict:
        with open(SAMPLES_DIR / "skill-audit.json") as f:
            return json.load(f)

    def test_pass_case(self, audit_contract: dict) -> None:
        """Transcript mentioning all dimension keywords passes."""
        transcript = (
            "First, I ran build-kg to build the knowledge graph. "
            "The BSKG query returned 5 nodes with evidence. "
            "I matched against vulndoc patterns for reentrancy detection."
        )
        assert_reasoning_dimensions_covered(transcript, audit_contract)

    def test_fail_missing_dimension(self, audit_contract: dict) -> None:
        """Transcript missing a dimension raises with dimension name."""
        transcript = "I only discussed random topics with no security content."
        with pytest.raises(AssertionError, match="graph_utilization"):
            assert_reasoning_dimensions_covered(transcript, audit_contract)

    def test_unknown_dimension_checks_name(self) -> None:
        """Unknown dimensions fall back to checking dimension name in transcript."""
        contract = {"reasoning_dimensions": ["custom_analysis"]}
        transcript = "We performed custom analysis of the contract."
        assert_reasoning_dimensions_covered(transcript, contract)

    def test_unknown_dimension_fails(self) -> None:
        """Unknown dimension not in transcript raises."""
        contract = {"reasoning_dimensions": ["quantum_entanglement"]}
        transcript = "Just a normal security review."
        with pytest.raises(AssertionError, match="quantum_entanglement"):
            assert_reasoning_dimensions_covered(transcript, contract)

    def test_empty_dimensions_passes(self) -> None:
        """Contract with no reasoning_dimensions passes (nothing to check)."""
        contract: dict = {"reasoning_dimensions": []}
        assert_reasoning_dimensions_covered("anything", contract)

    def test_debate_contract_pass(self) -> None:
        """Orchestrator-debate dimensions pass with relevant transcript."""
        with open(SAMPLES_DIR / "orchestrator-debate.json") as f:
            contract = json.load(f)
        transcript = (
            "The verifier examined evidence from both sides. "
            "The attacker presented an adversarial counterargument. "
            "After debate, the team reached consensus with a confirmed verdict."
        )
        assert_reasoning_dimensions_covered(transcript, contract)


# ---------------------------------------------------------------------------
# 6. Existing assertion categories still work (non-regression)
# ---------------------------------------------------------------------------


class TestExistingAssertionsNonRegression:
    """Verify existing assertion categories are unaffected by additions."""

    def test_findings_have_locations(self) -> None:
        """Category 4: assert_findings_have_locations still works."""
        findings = [
            {"location": "/contracts/Vault.sol:42", "severity": "high"},
            {"location": "/contracts/Token.sol:10", "severity": "medium"},
        ]
        assert_findings_have_locations(findings)

    def test_findings_have_locations_fails(self) -> None:
        """Category 4: assert_findings_have_locations still fails correctly."""
        findings = [{"severity": "high"}]  # missing location
        with pytest.raises(AssertionError, match="Finding 0 has no location"):
            assert_findings_have_locations(findings)

    def test_findings_cite_graph_nodes(self) -> None:
        """Category 4: assert_findings_cite_graph_nodes still works."""
        findings = [{"graph_nodes": ["node-1"], "location": "/contracts/Vault.sol"}]
        assert_findings_cite_graph_nodes(findings)

    def test_findings_cite_graph_nodes_fails(self) -> None:
        """Category 4: assert_findings_cite_graph_nodes still fails correctly."""
        findings = [{"location": "/contracts/Vault.sol"}]  # no graph refs
        with pytest.raises(AssertionError, match="Finding 0 has no graph node"):
            assert_findings_cite_graph_nodes(findings)
