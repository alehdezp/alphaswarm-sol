"""
Tests for Codex Output Schema and Formatting

Validates:
1. Schema is valid JSON Schema
2. VKG findings can be formatted to match the schema
3. Output validates against the schema
"""

import json
import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.findings.model import (
    Evidence,
    EvidenceRef,
    Finding,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    FindingTier,
    Location,
)
from alphaswarm_sol.templates.codex import (
    CODEX_OUTPUT_SCHEMA_VERSION,
    AuditMetadata,
    ContractInfo,
    Recommendation,
    calculate_summary,
    calculate_verdict,
    format_finding_for_codex,
    format_findings_for_codex,
    format_findings_to_json,
    generate_recommendations,
    get_output_schema,
    get_schema_json,
    validate_codex_output,
    validate_codex_output_file,
    write_output_schema,
)


class TestOutputSchema(unittest.TestCase):
    """Tests for the output schema definition."""

    def test_schema_has_required_fields(self):
        """Test that schema has required top-level fields."""
        schema = get_output_schema()
        self.assertEqual(schema["$schema"], "http://json-schema.org/draft-07/schema#")
        self.assertIn("findings", schema["required"])
        self.assertIn("summary", schema["required"])
        self.assertIn("metadata", schema["required"])

    def test_schema_has_all_properties(self):
        """Test that schema defines all expected properties."""
        schema = get_output_schema()
        properties = schema["properties"]
        self.assertIn("findings", properties)
        self.assertIn("summary", properties)
        self.assertIn("metadata", properties)
        self.assertIn("contracts_analyzed", properties)
        self.assertIn("recommendations", properties)
        self.assertIn("verdict", properties)

    def test_findings_schema(self):
        """Test findings array schema."""
        schema = get_output_schema()
        findings_schema = schema["properties"]["findings"]
        self.assertEqual(findings_schema["type"], "array")

        # Check finding item schema
        item_schema = findings_schema["items"]
        required_fields = item_schema["required"]
        self.assertIn("id", required_fields)
        self.assertIn("pattern_id", required_fields)
        self.assertIn("severity", required_fields)
        self.assertIn("confidence", required_fields)
        self.assertIn("title", required_fields)
        self.assertIn("description", required_fields)
        self.assertIn("location", required_fields)

    def test_severity_enum(self):
        """Test severity enum values."""
        schema = get_output_schema()
        severity_enum = schema["properties"]["findings"]["items"]["properties"]["severity"]["enum"]
        self.assertIn("critical", severity_enum)
        self.assertIn("high", severity_enum)
        self.assertIn("medium", severity_enum)
        self.assertIn("low", severity_enum)
        self.assertIn("info", severity_enum)

    def test_confidence_enum(self):
        """Test confidence enum values."""
        schema = get_output_schema()
        confidence_enum = schema["properties"]["findings"]["items"]["properties"]["confidence"]["enum"]
        self.assertIn("high", confidence_enum)
        self.assertIn("medium", confidence_enum)
        self.assertIn("low", confidence_enum)

    def test_tier_enum(self):
        """Test tier enum values."""
        schema = get_output_schema()
        tier_enum = schema["properties"]["findings"]["items"]["properties"]["tier"]["enum"]
        self.assertIn("tier_a", tier_enum)
        self.assertIn("tier_b", tier_enum)

    def test_location_schema(self):
        """Test location object schema."""
        schema = get_output_schema()
        location_schema = schema["properties"]["findings"]["items"]["properties"]["location"]
        self.assertEqual(location_schema["type"], "object")
        self.assertIn("file", location_schema["required"])
        self.assertIn("line", location_schema["required"])

        # Check location properties
        props = location_schema["properties"]
        self.assertIn("file", props)
        self.assertIn("line", props)
        self.assertIn("column", props)
        self.assertIn("function", props)
        self.assertIn("contract", props)

    def test_evidence_schema(self):
        """Test evidence object schema."""
        schema = get_output_schema()
        evidence_schema = schema["properties"]["findings"]["items"]["properties"]["evidence"]
        self.assertEqual(evidence_schema["type"], "object")

        # Check evidence properties
        props = evidence_schema["properties"]
        self.assertIn("behavioral_signature", props)
        self.assertIn("semantic_operations", props)
        self.assertIn("properties_matched", props)
        self.assertIn("why_vulnerable", props)
        self.assertIn("attack_scenario", props)

    def test_summary_schema(self):
        """Test summary object schema."""
        schema = get_output_schema()
        summary_schema = schema["properties"]["summary"]
        self.assertEqual(summary_schema["type"], "object")
        self.assertIn("total_findings", summary_schema["required"])
        self.assertIn("by_severity", summary_schema["required"])
        self.assertIn("by_tier", summary_schema["required"])

    def test_metadata_schema(self):
        """Test metadata object schema."""
        schema = get_output_schema()
        metadata_schema = schema["properties"]["metadata"]
        self.assertEqual(metadata_schema["type"], "object")
        self.assertIn("timestamp", metadata_schema["required"])
        self.assertIn("vkg_version", metadata_schema["required"])
        self.assertIn("schema_version", metadata_schema["required"])

    def test_verdict_schema(self):
        """Test verdict object schema."""
        schema = get_output_schema()
        verdict_schema = schema["properties"]["verdict"]
        self.assertEqual(verdict_schema["type"], "object")

        # Check verdict status enum
        status_enum = verdict_schema["properties"]["status"]["enum"]
        self.assertIn("pass", status_enum)
        self.assertIn("fail", status_enum)
        self.assertIn("needs_review", status_enum)

    def test_schema_is_valid_json(self):
        """Test that schema can be serialized to valid JSON."""
        schema = get_output_schema()
        json_str = json.dumps(schema)
        parsed = json.loads(json_str)
        self.assertEqual(parsed, schema)

    def test_get_schema_json(self):
        """Test get_schema_json function."""
        json_str = get_schema_json()
        self.assertIn("$schema", json_str)
        self.assertIn("findings", json_str)

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)


class TestWriteOutputSchema(unittest.TestCase):
    """Tests for writing schema to file."""

    def test_write_output_schema(self):
        """Test writing schema to a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "test-schema.json"
            result = write_output_schema(schema_path)

            self.assertEqual(result, schema_path)
            self.assertTrue(schema_path.exists())

            # Verify content
            with open(schema_path) as f:
                content = json.load(f)
            self.assertEqual(content["$schema"], "http://json-schema.org/draft-07/schema#")

    def test_write_output_schema_string_path(self):
        """Test writing schema with string path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = str(Path(tmpdir) / "test-schema.json")
            result = write_output_schema(schema_path)

            self.assertEqual(result, Path(schema_path))
            self.assertTrue(Path(schema_path).exists())


class TestFormatFinding(unittest.TestCase):
    """Tests for formatting individual findings."""

    def create_sample_finding(self) -> Finding:
        """Create a sample finding for testing."""
        return Finding(
            pattern="reentrancy-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(
                file="contracts/Vault.sol",
                line=42,
                column=8,
                function="withdraw",
                contract="Vault",
            ),
            description="State write after external call",
            title="Reentrancy in withdraw",
            tier=FindingTier.TIER_A,
            evidence=Evidence(
                behavioral_signature="R:bal->X:out->W:bal",
                operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                properties_matched=["state_write_after_external_call"],
                why_vulnerable="External call transfers ETH before balance update",
                attack_scenario=[
                    "1. Attacker deposits funds",
                    "2. Attacker calls withdraw()",
                    "3. In receive(), attacker re-enters withdraw()",
                ],
            ),
            verification_steps=[
                "Check for external calls before state updates",
                "Verify reentrancy guard is not present",
            ],
            recommended_fix="Use checks-effects-interactions pattern",
            cwe="CWE-841",
            swc="SWC-107",
        )

    def test_format_finding_basic(self):
        """Test formatting a basic finding."""
        finding = self.create_sample_finding()
        formatted = format_finding_for_codex(finding)

        self.assertEqual(formatted["id"], finding.id)
        self.assertEqual(formatted["pattern_id"], "reentrancy-001")
        self.assertEqual(formatted["severity"], "high")
        self.assertEqual(formatted["confidence"], "high")
        self.assertEqual(formatted["tier"], "tier_a")
        self.assertEqual(formatted["title"], "Reentrancy in withdraw")
        self.assertEqual(formatted["description"], "State write after external call")

    def test_format_finding_location(self):
        """Test location formatting."""
        finding = self.create_sample_finding()
        formatted = format_finding_for_codex(finding)

        location = formatted["location"]
        self.assertEqual(location["file"], "contracts/Vault.sol")
        self.assertEqual(location["line"], 42)
        self.assertEqual(location["column"], 8)
        self.assertEqual(location["function"], "withdraw")
        self.assertEqual(location["contract"], "Vault")

    def test_format_finding_evidence(self):
        """Test evidence formatting."""
        finding = self.create_sample_finding()
        formatted = format_finding_for_codex(finding)

        evidence = formatted["evidence"]
        self.assertEqual(evidence["behavioral_signature"], "R:bal->X:out->W:bal")
        self.assertIn("TRANSFERS_VALUE_OUT", evidence["semantic_operations"])
        self.assertIn("state_write_after_external_call", evidence["properties_matched"])
        self.assertIn("External call transfers", evidence["why_vulnerable"])
        self.assertEqual(len(evidence["attack_scenario"]), 3)

    def test_format_finding_references(self):
        """Test references formatting."""
        finding = self.create_sample_finding()
        formatted = format_finding_for_codex(finding)

        references = formatted["references"]
        self.assertTrue(any(r["type"] == "cwe" and r["id"] == "CWE-841" for r in references))
        self.assertTrue(any(r["type"] == "swc" and r["id"] == "SWC-107" for r in references))

    def test_format_finding_severity_mapping(self):
        """Test that all severity levels are properly mapped."""
        severities = [
            (FindingSeverity.CRITICAL, "critical"),
            (FindingSeverity.HIGH, "high"),
            (FindingSeverity.MEDIUM, "medium"),
            (FindingSeverity.LOW, "low"),
            (FindingSeverity.INFO, "info"),
        ]
        for severity_enum, expected_str in severities:
            finding = Finding(
                pattern="test",
                severity=severity_enum,
                confidence=FindingConfidence.MEDIUM,
                location=Location(file="test.sol", line=1),
                description="Test",
            )
            formatted = format_finding_for_codex(finding)
            self.assertEqual(formatted["severity"], expected_str)

    def test_format_finding_tier_mapping(self):
        """Test that all tier levels are properly mapped."""
        tiers = [
            (FindingTier.TIER_A, "tier_a"),
            (FindingTier.TIER_B, "tier_b"),
        ]
        for tier_enum, expected_str in tiers:
            finding = Finding(
                pattern="test",
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.MEDIUM,
                tier=tier_enum,
                location=Location(file="test.sol", line=1),
                description="Test",
            )
            formatted = format_finding_for_codex(finding)
            self.assertEqual(formatted["tier"], expected_str)


class TestFormatFindings(unittest.TestCase):
    """Tests for formatting multiple findings."""

    def create_findings(self) -> list[Finding]:
        """Create multiple findings for testing."""
        return [
            Finding(
                pattern="reentrancy-001",
                severity=FindingSeverity.CRITICAL,
                confidence=FindingConfidence.HIGH,
                location=Location(file="Vault.sol", line=42, function="withdraw"),
                description="Critical reentrancy",
            ),
            Finding(
                pattern="auth-002",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.MEDIUM,
                location=Location(file="Access.sol", line=10, function="setOwner"),
                description="Missing access control",
            ),
            Finding(
                pattern="oracle-001",
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.HIGH,
                tier=FindingTier.TIER_B,
                location=Location(file="Price.sol", line=25, function="getPrice"),
                description="Missing staleness check",
            ),
        ]

    def test_format_findings_basic(self):
        """Test formatting multiple findings."""
        findings = self.create_findings()
        output = format_findings_for_codex(findings)

        self.assertIn("findings", output)
        self.assertIn("summary", output)
        self.assertIn("metadata", output)
        self.assertEqual(len(output["findings"]), 3)

    def test_format_findings_summary(self):
        """Test summary calculation."""
        findings = self.create_findings()
        output = format_findings_for_codex(findings)

        summary = output["summary"]
        self.assertEqual(summary["total_findings"], 3)
        self.assertEqual(summary["by_severity"]["critical"], 1)
        self.assertEqual(summary["by_severity"]["high"], 1)
        self.assertEqual(summary["by_severity"]["medium"], 1)
        self.assertEqual(summary["by_tier"]["tier_a"], 2)
        self.assertEqual(summary["by_tier"]["tier_b"], 1)

    def test_format_findings_verdict(self):
        """Test verdict calculation."""
        findings = self.create_findings()
        output = format_findings_for_codex(findings)

        verdict = output["verdict"]
        self.assertEqual(verdict["status"], "fail")  # Has critical
        self.assertTrue(verdict["critical_issues_found"])
        self.assertFalse(verdict["deployment_recommended"])

    def test_format_findings_no_critical(self):
        """Test verdict when no critical findings."""
        findings = [
            Finding(
                pattern="auth-001",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="High severity issue",
            ),
        ]
        output = format_findings_for_codex(findings)

        verdict = output["verdict"]
        self.assertEqual(verdict["status"], "needs_review")
        self.assertFalse(verdict["critical_issues_found"])

    def test_format_findings_pass(self):
        """Test verdict when only low/info findings."""
        findings = [
            Finding(
                pattern="info-001",
                severity=FindingSeverity.LOW,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="Low severity issue",
            ),
        ]
        output = format_findings_for_codex(findings)

        verdict = output["verdict"]
        self.assertEqual(verdict["status"], "pass")
        self.assertTrue(verdict["deployment_recommended"])

    def test_format_findings_with_contracts(self):
        """Test formatting with contracts info."""
        findings = self.create_findings()
        contracts = [
            ContractInfo(
                name="Vault",
                file="contracts/Vault.sol",
                function_count=10,
                findings_count=1,
            ),
            ContractInfo(
                name="Access",
                file="contracts/Access.sol",
                function_count=5,
                findings_count=1,
            ),
        ]
        output = format_findings_for_codex(findings, contracts=contracts)

        self.assertIn("contracts_analyzed", output)
        self.assertEqual(len(output["contracts_analyzed"]), 2)
        self.assertEqual(output["contracts_analyzed"][0]["name"], "Vault")

    def test_format_findings_with_metadata(self):
        """Test formatting with custom metadata."""
        findings = self.create_findings()
        metadata = AuditMetadata(
            vkg_version="3.5.1",
            codex_model="gpt-5-codex",
            graph_properties_count=150,
            patterns_evaluated=["reentrancy-*", "auth-*"],
            analysis_duration_seconds=12.5,
            project_path="/path/to/project",
        )
        output = format_findings_for_codex(findings, metadata=metadata)

        meta = output["metadata"]
        self.assertEqual(meta["vkg_version"], "3.5.1")
        self.assertEqual(meta["codex_model"], "gpt-5-codex")
        self.assertEqual(meta["graph_properties_count"], 150)

    def test_format_findings_recommendations(self):
        """Test recommendations generation."""
        findings = self.create_findings()
        output = format_findings_for_codex(findings)

        self.assertIn("recommendations", output)
        recommendations = output["recommendations"]
        self.assertTrue(len(recommendations) > 0)

        # Should have recommendations for reentrancy, auth, oracle
        categories = [r["category"].lower() for r in recommendations]
        self.assertIn("reentrancy", categories)
        self.assertIn("auth", categories)
        self.assertIn("oracle", categories)

    def test_format_findings_disable_recommendations(self):
        """Test disabling recommendations."""
        findings = self.create_findings()
        output = format_findings_for_codex(findings, include_recommendations=False)
        self.assertNotIn("recommendations", output)

    def test_format_findings_disable_verdict(self):
        """Test disabling verdict."""
        findings = self.create_findings()
        output = format_findings_for_codex(findings, include_verdict=False)
        self.assertNotIn("verdict", output)


class TestCalculateSummary(unittest.TestCase):
    """Tests for summary calculation."""

    def test_calculate_summary_empty(self):
        """Test summary with no findings."""
        summary = calculate_summary([])
        self.assertEqual(summary["total_findings"], 0)
        self.assertEqual(summary["risk_score"], 0.0)

    def test_calculate_summary_risk_score(self):
        """Test risk score calculation."""
        findings = [
            Finding(
                pattern="test",
                severity=FindingSeverity.CRITICAL,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="Critical",
            ),
            Finding(
                pattern="test2",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=2),
                description="High",
            ),
        ]
        summary = calculate_summary(findings)
        # 1 critical (25) + 1 high (15) = 40
        self.assertEqual(summary["risk_score"], 40.0)

    def test_calculate_summary_risk_score_capped(self):
        """Test risk score is capped at 100."""
        findings = [
            Finding(
                pattern=f"test-{i}",
                severity=FindingSeverity.CRITICAL,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=i),
                description=f"Critical {i}",
            )
            for i in range(10)  # 10 * 25 = 250, should cap at 100
        ]
        summary = calculate_summary(findings)
        self.assertEqual(summary["risk_score"], 100.0)

    def test_calculate_summary_top_risk_areas(self):
        """Test top risk areas identification."""
        findings = [
            Finding(
                pattern="reentrancy-001",
                severity=FindingSeverity.HIGH,
                location=Location(file="test.sol", line=1),
                confidence=FindingConfidence.HIGH,
                description="Test",
            ),
            Finding(
                pattern="reentrancy-002",
                severity=FindingSeverity.MEDIUM,
                location=Location(file="test.sol", line=2),
                confidence=FindingConfidence.HIGH,
                description="Test",
            ),
            Finding(
                pattern="auth-001",
                severity=FindingSeverity.HIGH,
                location=Location(file="test.sol", line=3),
                confidence=FindingConfidence.HIGH,
                description="Test",
            ),
        ]
        summary = calculate_summary(findings)
        self.assertIn("reentrancy", summary["top_risk_areas"])


class TestCalculateVerdict(unittest.TestCase):
    """Tests for verdict calculation."""

    def test_verdict_fail_critical(self):
        """Test fail verdict with critical findings."""
        findings = [
            Finding(
                pattern="test",
                severity=FindingSeverity.CRITICAL,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="Critical issue",
            ),
        ]
        verdict = calculate_verdict(findings)
        self.assertEqual(verdict["status"], "fail")
        self.assertTrue(verdict["critical_issues_found"])
        self.assertFalse(verdict["deployment_recommended"])

    def test_verdict_needs_review_high(self):
        """Test needs_review verdict with high findings."""
        findings = [
            Finding(
                pattern="test",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="High issue",
            ),
        ]
        verdict = calculate_verdict(findings)
        self.assertEqual(verdict["status"], "needs_review")
        self.assertFalse(verdict["critical_issues_found"])
        self.assertFalse(verdict["deployment_recommended"])

    def test_verdict_pass_low(self):
        """Test pass verdict with low findings."""
        findings = [
            Finding(
                pattern="test",
                severity=FindingSeverity.LOW,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="Low issue",
            ),
        ]
        verdict = calculate_verdict(findings)
        self.assertEqual(verdict["status"], "pass")
        self.assertFalse(verdict["critical_issues_found"])
        self.assertTrue(verdict["deployment_recommended"])

    def test_verdict_empty(self):
        """Test verdict with no findings."""
        verdict = calculate_verdict([])
        self.assertEqual(verdict["status"], "pass")
        self.assertTrue(verdict["deployment_recommended"])


class TestGenerateRecommendations(unittest.TestCase):
    """Tests for recommendation generation."""

    def test_generate_recommendations_empty(self):
        """Test recommendations with no findings."""
        recommendations = generate_recommendations([])
        self.assertEqual(len(recommendations), 0)

    def test_generate_recommendations_known_categories(self):
        """Test recommendations for known categories."""
        findings = [
            Finding(
                pattern="reentrancy-001",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="Reentrancy",
            ),
        ]
        recommendations = generate_recommendations(findings)
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["category"], "Reentrancy")
        self.assertIn("checks-effects-interactions", recommendations[0]["recommendation"])

    def test_generate_recommendations_priority_order(self):
        """Test recommendations are ordered by priority."""
        findings = [
            Finding(
                pattern="oracle-001",
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="Oracle",
            ),
            Finding(
                pattern="reentrancy-001",
                severity=FindingSeverity.CRITICAL,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=2),
                description="Reentrancy",
            ),
        ]
        recommendations = generate_recommendations(findings)
        # Reentrancy (critical) should come before oracle (medium)
        priorities = [r["priority"] for r in recommendations]
        self.assertEqual(priorities[0], "critical")
        self.assertEqual(priorities[1], "medium")


class TestValidation(unittest.TestCase):
    """Tests for output validation."""

    def test_validate_valid_output(self):
        """Test validation of valid output."""
        findings = [
            Finding(
                pattern="test-001",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="Test finding",
            ),
        ]
        output = format_findings_for_codex(findings)
        is_valid, errors = validate_codex_output(output)
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_empty_findings(self):
        """Test validation with empty findings."""
        output = format_findings_for_codex([])
        is_valid, errors = validate_codex_output(output)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_validate_missing_required_field(self):
        """Test validation fails with missing required field."""
        output = {
            "findings": [],
            # Missing "summary" and "metadata"
        }
        is_valid, errors = validate_codex_output(output)
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)

    def test_validate_invalid_severity(self):
        """Test validation fails with invalid severity."""
        output = {
            "findings": [
                {
                    "id": "VKG-12345678",
                    "pattern_id": "test",
                    "severity": "invalid",  # Invalid
                    "confidence": "high",
                    "title": "Test",
                    "description": "Test",
                    "location": {"file": "test.sol", "line": 1},
                }
            ],
            "summary": {
                "total_findings": 1,
                "by_severity": {},
                "by_tier": {},
            },
            "metadata": {
                "timestamp": "2026-01-08T00:00:00Z",
                "vkg_version": "3.5",
                "schema_version": "1.0.0",
            },
        }
        is_valid, errors = validate_codex_output(output)
        self.assertFalse(is_valid)

    def test_validate_file(self):
        """Test validation of file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write valid output
            findings = [
                Finding(
                    pattern="test-001",
                    severity=FindingSeverity.HIGH,
                    confidence=FindingConfidence.HIGH,
                    location=Location(file="test.sol", line=1),
                    description="Test finding",
                ),
            ]
            output = format_findings_for_codex(findings)
            output_path = Path(tmpdir) / "output.json"
            with open(output_path, "w") as f:
                json.dump(output, f)

            is_valid, errors = validate_codex_output_file(output_path)
            self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_validate_file_not_found(self):
        """Test validation with missing file."""
        is_valid, errors = validate_codex_output_file("/nonexistent/path.json")
        self.assertFalse(is_valid)
        self.assertIn("not found", errors[0].lower())

    def test_validate_file_invalid_json(self):
        """Test validation with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid.json"
            path.write_text("{ invalid json }")
            is_valid, errors = validate_codex_output_file(path)
            self.assertFalse(is_valid)
            self.assertIn("Invalid JSON", errors[0])


class TestFormatToJson(unittest.TestCase):
    """Tests for JSON output formatting."""

    def test_format_to_json(self):
        """Test format_findings_to_json function."""
        findings = [
            Finding(
                pattern="test-001",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="Test finding",
            ),
        ]
        json_str = format_findings_to_json(findings)

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertIn("findings", parsed)
        self.assertEqual(len(parsed["findings"]), 1)

    def test_format_to_json_indent(self):
        """Test format_findings_to_json with custom indent."""
        findings = [
            Finding(
                pattern="test-001",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.HIGH,
                location=Location(file="test.sol", line=1),
                description="Test finding",
            ),
        ]
        # With indent 4
        json_str = format_findings_to_json(findings, indent=4)
        self.assertIn("    ", json_str)  # Should have 4-space indentation


class TestDataClasses(unittest.TestCase):
    """Tests for helper data classes."""

    def test_contract_info(self):
        """Test ContractInfo dataclass."""
        info = ContractInfo(
            name="Vault",
            file="Vault.sol",
            function_count=10,
            findings_count=2,
            properties_extracted=150,
        )
        d = info.to_dict()
        self.assertEqual(d["name"], "Vault")
        self.assertEqual(d["function_count"], 10)

    def test_recommendation(self):
        """Test Recommendation dataclass."""
        rec = Recommendation(
            priority="high",
            category="Reentrancy",
            recommendation="Use ReentrancyGuard",
            affected_findings=["VKG-12345678"],
        )
        d = rec.to_dict()
        self.assertEqual(d["priority"], "high")
        self.assertEqual(d["category"], "Reentrancy")
        self.assertIn("VKG-12345678", d["affected_findings"])

    def test_audit_metadata_defaults(self):
        """Test AuditMetadata with defaults."""
        meta = AuditMetadata()
        self.assertTrue(meta.timestamp)  # Auto-generated
        self.assertEqual(meta.vkg_version, "3.5")
        self.assertEqual(meta.schema_version, CODEX_OUTPUT_SCHEMA_VERSION)

    def test_audit_metadata_to_dict(self):
        """Test AuditMetadata.to_dict()."""
        meta = AuditMetadata(
            vkg_version="3.5.1",
            codex_model="gpt-5",
            patterns_evaluated=["reentrancy-*"],
        )
        d = meta.to_dict()
        self.assertEqual(d["vkg_version"], "3.5.1")
        self.assertEqual(d["codex_model"], "gpt-5")
        self.assertIn("reentrancy-*", d["patterns_evaluated"])


class TestSchemaVersioning(unittest.TestCase):
    """Tests for schema version handling."""

    def test_schema_version_constant(self):
        """Test schema version constant exists."""
        self.assertEqual(CODEX_OUTPUT_SCHEMA_VERSION, "1.0.0")

    def test_schema_version_in_output(self):
        """Test schema version is included in output."""
        output = format_findings_for_codex([])
        self.assertEqual(
            output["metadata"]["schema_version"],
            CODEX_OUTPUT_SCHEMA_VERSION
        )


class TestSchemaFileMatchesCode(unittest.TestCase):
    """Test that JSON file matches code-generated schema."""

    def test_schema_file_matches_code(self):
        """Verify schemas/vkg-codex-output.json matches get_output_schema()."""
        schema_path = Path(__file__).parent.parent / "schemas" / "vkg-codex-output.json"

        if not schema_path.exists():
            self.skipTest("Schema file not found")

        with open(schema_path) as f:
            file_schema = json.load(f)

        code_schema = get_output_schema()

        # Compare key fields (not exact match due to formatting)
        self.assertEqual(file_schema["$schema"], code_schema["$schema"])
        self.assertEqual(file_schema["required"], code_schema["required"])
        self.assertEqual(
            set(file_schema["properties"].keys()),
            set(code_schema["properties"].keys())
        )


if __name__ == "__main__":
    unittest.main()
