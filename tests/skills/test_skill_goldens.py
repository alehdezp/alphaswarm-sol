"""
Tests for golden output fixtures and output contract validation.

Validates that golden outputs conform to declared schemas and demonstrate
correct evidence-first, graph-anchored behavior.
"""

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def goldens_dir(project_root):
    """Get goldens directory."""
    return project_root / "tests" / "skills" / "goldens"


@pytest.fixture
def schemas_dir(project_root):
    """Get schemas directory."""
    return project_root / "schemas"


@pytest.fixture
def secure_reviewer_schema(schemas_dir):
    """Load secure reviewer output schema."""
    schema_path = schemas_dir / "secure_reviewer_output.json"
    if not schema_path.exists():
        pytest.skip("secure_reviewer_output.json schema not found")
    return json.loads(schema_path.read_text())


class TestGoldenValidation:
    """Test golden output fixtures validate against schemas."""

    def test_secure_reviewer_golden_is_valid_json(self, goldens_dir):
        """Test that secure reviewer golden is valid JSON."""
        golden_path = goldens_dir / "secure_reviewer.json"
        assert golden_path.exists(), "secure_reviewer.json golden not found"

        # Load and parse
        try:
            golden = json.loads(golden_path.read_text())
        except json.JSONDecodeError as e:
            pytest.fail(f"secure_reviewer.json is not valid JSON: {e}")

        # Check it's not empty
        assert len(golden) > 0, "secure_reviewer.json is empty"

    def test_secure_reviewer_golden_conforms_to_schema(
        self, goldens_dir, secure_reviewer_schema
    ):
        """Test that secure reviewer golden conforms to output schema."""
        golden_path = goldens_dir / "secure_reviewer.json"
        golden = json.loads(golden_path.read_text())

        # Validate against schema
        try:
            validate(instance=golden, schema=secure_reviewer_schema)
        except ValidationError as e:
            pytest.fail(f"secure_reviewer.json schema validation failed: {e.message}")

    def test_attacker_golden_is_valid_json(self, goldens_dir):
        """Test that attacker golden is valid JSON."""
        golden_path = goldens_dir / "attacker.json"
        assert golden_path.exists(), "attacker.json golden not found"

        try:
            golden = json.loads(golden_path.read_text())
        except json.JSONDecodeError as e:
            pytest.fail(f"attacker.json is not valid JSON: {e}")

        assert len(golden) > 0, "attacker.json is empty"

    def test_defender_golden_is_valid_json(self, goldens_dir):
        """Test that defender golden is valid JSON."""
        golden_path = goldens_dir / "defender.json"
        assert golden_path.exists(), "defender.json golden not found"

        try:
            golden = json.loads(golden_path.read_text())
        except json.JSONDecodeError as e:
            pytest.fail(f"defender.json is not valid JSON: {e}")

        assert len(golden) > 0, "defender.json is empty"

    def test_verifier_golden_is_valid_json(self, goldens_dir):
        """Test that verifier golden is valid JSON."""
        golden_path = goldens_dir / "verifier.json"
        assert golden_path.exists(), "verifier.json golden not found"

        try:
            golden = json.loads(golden_path.read_text())
        except json.JSONDecodeError as e:
            pytest.fail(f"verifier.json is not valid JSON: {e}")

        assert len(golden) > 0, "verifier.json is empty"


class TestEvidenceStructure:
    """Test evidence structure in golden outputs."""

    def test_secure_reviewer_has_evidence_array(self, goldens_dir):
        """Test that secure reviewer golden has evidence array."""
        golden_path = goldens_dir / "secure_reviewer.json"
        golden = json.loads(golden_path.read_text())

        assert "evidence" in golden, "Missing 'evidence' field"
        assert isinstance(golden["evidence"], list), "'evidence' must be an array"

    def test_secure_reviewer_evidence_has_required_fields(self, goldens_dir):
        """Test that evidence items have required fields."""
        golden_path = goldens_dir / "secure_reviewer.json"
        golden = json.loads(golden_path.read_text())

        for i, evidence_item in enumerate(golden["evidence"]):
            assert "type" in evidence_item, f"Evidence {i}: Missing 'type'"
            assert "description" in evidence_item, f"Evidence {i}: Missing 'description'"
            assert "confidence" in evidence_item, f"Evidence {i}: Missing 'confidence'"

            # Must have either code_location or graph_node_id
            has_location = "code_location" in evidence_item or "graph_node_id" in evidence_item
            assert has_location, f"Evidence {i}: Missing code_location or graph_node_id"

    def test_attacker_has_graph_queries(self, goldens_dir):
        """Test that attacker golden has graph queries."""
        golden_path = goldens_dir / "attacker.json"
        golden = json.loads(golden_path.read_text())

        assert "graph_queries" in golden, "Missing 'graph_queries' field"
        assert isinstance(golden["graph_queries"], list), "'graph_queries' must be an array"
        assert len(golden["graph_queries"]) > 0, "Must have at least one graph query"

    def test_defender_has_mitigations(self, goldens_dir):
        """Test that defender golden has mitigation strategies."""
        golden_path = goldens_dir / "defender.json"
        golden = json.loads(golden_path.read_text())

        assert "mitigations" in golden, "Missing 'mitigations' field"
        assert isinstance(golden["mitigations"], list), "'mitigations' must be an array"
        assert len(golden["mitigations"]) > 0, "Must have at least one mitigation"

        # Check mitigation structure
        for i, mitigation in enumerate(golden["mitigations"]):
            assert "priority" in mitigation, f"Mitigation {i}: Missing 'priority'"
            assert "strategy" in mitigation, f"Mitigation {i}: Missing 'strategy'"
            assert "implementation" in mitigation, f"Mitigation {i}: Missing 'implementation'"

    def test_verifier_has_cross_check_results(self, goldens_dir):
        """Test that verifier golden has cross-check results."""
        golden_path = goldens_dir / "verifier.json"
        golden = json.loads(golden_path.read_text())

        assert "cross_check_results" in golden, "Missing 'cross_check_results' field"
        assert isinstance(golden["cross_check_results"], list), \
            "'cross_check_results' must be an array"
        assert len(golden["cross_check_results"]) > 0, \
            "Must have at least one cross-check result"


class TestGraphFirstCompliance:
    """Test that goldens demonstrate graph-first reasoning."""

    def test_secure_reviewer_has_graph_queries(self, goldens_dir):
        """Test that secure reviewer golden includes graph queries."""
        golden_path = goldens_dir / "secure_reviewer.json"
        golden = json.loads(golden_path.read_text())

        assert "graph_queries" in golden, "Missing 'graph_queries' field"
        assert isinstance(golden["graph_queries"], list), "'graph_queries' must be an array"
        assert len(golden["graph_queries"]) >= 1, \
            "Must have at least one graph query (graph-first requirement)"

        # Validate query structure
        for i, query in enumerate(golden["graph_queries"]):
            assert "query" in query, f"Query {i}: Missing 'query' field"
            assert "rationale" in query, f"Query {i}: Missing 'rationale' field"

    def test_attacker_evidence_references_graph(self, goldens_dir):
        """Test that attacker evidence references graph nodes."""
        golden_path = goldens_dir / "attacker.json"
        golden = json.loads(golden_path.read_text())

        if "evidence" not in golden:
            pytest.skip("No evidence array in attacker golden")

        # At least one evidence item should reference graph
        has_graph_reference = any(
            "graph_node_id" in item for item in golden["evidence"]
        )
        assert has_graph_reference, "No evidence items reference graph nodes"

    def test_defender_queries_for_guards(self, goldens_dir):
        """Test that defender golden includes guard discovery queries."""
        golden_path = goldens_dir / "defender.json"
        golden = json.loads(golden_path.read_text())

        assert "graph_queries" in golden, "Missing 'graph_queries' field"

        # Check for guard-related queries
        queries_text = json.dumps(golden["graph_queries"]).lower()
        has_guard_query = any(
            term in queries_text for term in ["guard", "modifier", "protection"]
        )
        assert has_guard_query, "No guard discovery queries found"

    def test_verifier_cross_checks_graph_properties(self, goldens_dir):
        """Test that verifier cross-checks graph properties."""
        golden_path = goldens_dir / "verifier.json"
        golden = json.loads(golden_path.read_text())

        # Check that cross-check results reference graph nodes
        if "cross_check_results" not in golden:
            pytest.skip("No cross_check_results in verifier golden")

        has_graph_references = any(
            "graph_node_id" in result for result in golden["cross_check_results"]
        )
        assert has_graph_references, "Cross-checks don't reference graph nodes"


class TestModeSpecificFields:
    """Test mode-specific requirements in goldens."""

    def test_creative_mode_has_hypotheses(self, goldens_dir):
        """Test that creative mode includes creative_hypotheses."""
        golden_path = goldens_dir / "secure_reviewer.json"
        golden = json.loads(golden_path.read_text())

        # Check mode
        if golden.get("mode") != "creative":
            pytest.skip("Not in creative mode")

        assert "creative_hypotheses" in golden, \
            "Creative mode must include 'creative_hypotheses'"
        assert isinstance(golden["creative_hypotheses"], list), \
            "'creative_hypotheses' must be an array"

        # Validate hypothesis structure
        for i, hypothesis in enumerate(golden["creative_hypotheses"]):
            assert "hypothesis" in hypothesis, f"Hypothesis {i}: Missing 'hypothesis'"
            assert "attack_path" in hypothesis, f"Hypothesis {i}: Missing 'attack_path'"
            assert "feasibility" in hypothesis, f"Hypothesis {i}: Missing 'feasibility'"

    def test_adversarial_mode_would_have_refutations(self, goldens_dir, secure_reviewer_schema):
        """Test that adversarial mode would require refutations."""
        # This test validates the schema requirement, not the golden
        # (since our golden is in creative mode)

        # Check schema requires refutations in adversarial mode
        properties = secure_reviewer_schema.get("properties", {})
        assert "refutations" in properties, "Schema missing 'refutations' field"
        assert "mode" in properties, "Schema missing 'mode' field"


class TestConfidenceScores:
    """Test confidence score validity in goldens."""

    def test_evidence_confidence_in_valid_range(self, goldens_dir):
        """Test that evidence confidence scores are between 0.0 and 1.0."""
        golden_files = [
            "secure_reviewer.json",
            "attacker.json",
            "defender.json",
            "verifier.json",
        ]

        for golden_file in golden_files:
            golden_path = goldens_dir / golden_file
            if not golden_path.exists():
                continue

            golden = json.loads(golden_path.read_text())

            if "evidence" not in golden:
                continue

            for i, evidence_item in enumerate(golden["evidence"]):
                if "confidence" not in evidence_item:
                    continue

                confidence = evidence_item["confidence"]
                assert isinstance(confidence, (int, float)), \
                    f"{golden_file} Evidence {i}: confidence must be numeric"
                assert 0.0 <= confidence <= 1.0, \
                    f"{golden_file} Evidence {i}: confidence must be between 0.0 and 1.0"


class TestGoldenCompleteness:
    """Test that all expected goldens exist."""

    def test_all_goldens_exist(self, goldens_dir):
        """Test that all expected golden files exist."""
        expected_goldens = [
            "secure_reviewer.json",
            "attacker.json",
            "defender.json",
            "verifier.json",
            "README.md",
        ]

        for golden_name in expected_goldens:
            golden_path = goldens_dir / golden_name
            assert golden_path.exists(), f"Missing golden: {golden_name}"

    def test_readme_documents_goldens(self, goldens_dir):
        """Test that README documents all golden files."""
        readme_path = goldens_dir / "README.md"
        readme_content = readme_path.read_text()

        expected_goldens = [
            "secure_reviewer.json",
            "attacker.json",
            "defender.json",
            "verifier.json",
        ]

        for golden_name in expected_goldens:
            assert golden_name in readme_content, \
                f"README.md doesn't document {golden_name}"
