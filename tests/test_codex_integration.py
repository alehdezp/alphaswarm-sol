"""
Codex Noninteractive Integration Tests (Task 3.8c)

This module tests the VKG integration with OpenAI Codex CLI's noninteractive mode.
Since we cannot actually run `codex exec` in the test environment, these tests validate:

1. Output Schema Test - Schema is valid for `--output-schema`
2. Finding Format Test - Individual findings format correctly
3. Summary Format Test - Summary statistics are calculated correctly
4. Verdict Logic Test - Pass/fail/needs_review logic works
5. Recommendations Test - Recommendations are prioritized correctly
6. Full Audit Output Test - Complete audit output validates
7. CI/CD Helpers Test - CI/CD helper functions work correctly

Reference: task/4.0/phases/phase-3/R3.3-CODEX-NONINTERACTIVE-RESEARCH.md
"""

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from alphaswarm_sol.findings.model import (
    Evidence,
    Finding,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    FindingTier,
    Location,
)
from alphaswarm_sol.templates.codex import (
    CODEX_OUTPUT_SCHEMA_VERSION,
    VKG_VERSION,
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


class TestOutputSchemaForCodexCLI(unittest.TestCase):
    """Test 1: Schema is valid for `codex exec --output-schema`.

    The schema must:
    - Be valid JSON Schema draft-07
    - Be parseable by JSON Schema validators
    - Have all required fields properly defined
    - Have proper $schema and $id fields
    """

    def test_schema_is_valid_json_schema_draft07(self):
        """Schema declares itself as JSON Schema draft-07."""
        schema = get_output_schema()
        self.assertEqual(
            schema["$schema"],
            "http://json-schema.org/draft-07/schema#",
            "Schema must be JSON Schema draft-07 for Codex compatibility"
        )

    def test_schema_has_id(self):
        """Schema has a $id for reference."""
        schema = get_output_schema()
        self.assertIn("$id", schema)
        self.assertTrue(
            schema["$id"].startswith("https://"),
            "Schema $id should be a valid URL"
        )

    def test_schema_has_title_and_description(self):
        """Schema has title and description for documentation."""
        schema = get_output_schema()
        self.assertIn("title", schema)
        self.assertIn("description", schema)
        self.assertIn("VKG", schema["title"])
        self.assertIn("Codex", schema["description"])

    def test_schema_can_be_written_to_file(self):
        """Schema can be written to a file for Codex --output-schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "vkg-codex-output.json"
            result = write_output_schema(schema_path)

            self.assertTrue(result.exists())

            # Verify file contents are valid JSON
            with open(result) as f:
                loaded = json.load(f)

            self.assertEqual(loaded["$schema"], "http://json-schema.org/draft-07/schema#")
            self.assertIn("findings", loaded["properties"])

    def test_schema_file_matches_programmatic_schema(self):
        """Schema file in schemas/ matches get_output_schema()."""
        schema_path = Path(__file__).parent.parent / "schemas" / "vkg-codex-output.json"

        if not schema_path.exists():
            self.skipTest("Schema file not found at schemas/vkg-codex-output.json")

        with open(schema_path) as f:
            file_schema = json.load(f)

        code_schema = get_output_schema()

        # Key fields must match
        self.assertEqual(file_schema["$schema"], code_schema["$schema"])
        self.assertEqual(file_schema["type"], code_schema["type"])
        self.assertEqual(set(file_schema["required"]), set(code_schema["required"]))

    def test_schema_validates_with_jsonschema_library(self):
        """Schema itself is valid according to jsonschema library."""
        try:
            import jsonschema
            from jsonschema import Draft7Validator
        except ImportError:
            self.skipTest("jsonschema package not installed")

        schema = get_output_schema()

        # This should not raise if schema is valid
        try:
            Draft7Validator.check_schema(schema)
        except jsonschema.SchemaError as e:
            self.fail(f"Schema is not valid JSON Schema: {e}")

    def test_schema_no_additional_properties_at_top_level(self):
        """Schema disallows additional properties for strict validation."""
        schema = get_output_schema()
        self.assertFalse(
            schema.get("additionalProperties", True),
            "Schema should not allow additional properties for strict Codex validation"
        )


class TestFindingFormatForCodex(unittest.TestCase):
    """Test 2: Individual findings format correctly for Codex output."""

    def create_comprehensive_finding(self) -> Finding:
        """Create a finding with all possible fields populated."""
        return Finding(
            pattern="reentrancy-001",
            severity=FindingSeverity.CRITICAL,
            confidence=FindingConfidence.HIGH,
            tier=FindingTier.TIER_A,
            title="Critical Reentrancy in withdraw()",
            description="State write after external call allows reentrancy attack.",
            location=Location(
                file="contracts/Vault.sol",
                line=42,
                column=8,
                end_line=55,
                end_column=12,
                function="withdraw",
                contract="Vault",
            ),
            evidence=Evidence(
                behavioral_signature="R:bal->X:out->W:bal",
                operations=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                properties_matched=["state_write_after_external_call", "no_reentrancy_guard"],
                properties_missing=["has_reentrancy_guard"],
                code_snippet="function withdraw(uint amount) external {\n    uint bal = balances[msg.sender];\n    (bool success,) = msg.sender.call{value: bal}(\"\");\n    balances[msg.sender] = 0;\n}",
                why_vulnerable="The balance is updated after the external call, allowing reentrant calls to withdraw more than entitled.",
                attack_scenario=[
                    "1. Attacker deposits 1 ETH",
                    "2. Attacker calls withdraw()",
                    "3. In receive(), attacker re-enters withdraw()",
                    "4. Balance check passes again (not yet updated)",
                    "5. Attacker drains contract",
                ],
                data_flow=["msg.sender", "balances[msg.sender]", "msg.sender.call"],
                guard_analysis="No reentrancy guard (nonReentrant modifier) detected.",
            ),
            verification_steps=[
                "1. Confirm external call before state update",
                "2. Verify no ReentrancyGuard imported",
                "3. Check for CEI pattern violation",
            ],
            recommended_fix="Apply checks-effects-interactions pattern: update balances[msg.sender] = 0 before the call.",
            cwe="CWE-841",
            swc="SWC-107",
            references=["CVE-2016-1000", "https://consensys.github.io/smart-contract-best-practices/"],
            status=FindingStatus.PENDING,
        )

    def test_formatted_finding_has_required_fields(self):
        """Formatted finding has all required schema fields."""
        finding = self.create_comprehensive_finding()
        formatted = format_finding_for_codex(finding)

        required_fields = ["id", "pattern_id", "severity", "confidence", "title", "description", "location"]
        for field in required_fields:
            self.assertIn(field, formatted, f"Missing required field: {field}")

    def test_finding_id_matches_schema_pattern(self):
        """Finding ID matches the VKG-[A-F0-9]{8} pattern."""
        finding = self.create_comprehensive_finding()
        formatted = format_finding_for_codex(finding)

        import re
        pattern = r"^VKG-[A-F0-9]{8}$"
        self.assertTrue(
            re.match(pattern, formatted["id"]),
            f"Finding ID '{formatted['id']}' does not match pattern {pattern}"
        )

    def test_severity_is_valid_enum_value(self):
        """Severity is one of the allowed enum values."""
        valid_severities = ["critical", "high", "medium", "low", "info"]

        for severity in FindingSeverity:
            finding = Finding(
                pattern="test",
                severity=severity,
                confidence=FindingConfidence.MEDIUM,
                location=Location(file="test.sol", line=1),
                description="Test",
            )
            formatted = format_finding_for_codex(finding)
            self.assertIn(
                formatted["severity"],
                valid_severities,
                f"Severity '{formatted['severity']}' not in allowed values"
            )

    def test_confidence_is_valid_enum_value(self):
        """Confidence is one of the allowed enum values."""
        valid_confidences = ["high", "medium", "low"]

        for confidence in FindingConfidence:
            finding = Finding(
                pattern="test",
                severity=FindingSeverity.MEDIUM,
                confidence=confidence,
                location=Location(file="test.sol", line=1),
                description="Test",
            )
            formatted = format_finding_for_codex(finding)
            self.assertIn(
                formatted["confidence"],
                valid_confidences,
                f"Confidence '{formatted['confidence']}' not in allowed values"
            )

    def test_tier_is_valid_enum_value(self):
        """Tier is one of the allowed enum values."""
        valid_tiers = ["tier_a", "tier_b"]

        for tier in FindingTier:
            finding = Finding(
                pattern="test",
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.MEDIUM,
                tier=tier,
                location=Location(file="test.sol", line=1),
                description="Test",
            )
            formatted = format_finding_for_codex(finding)
            self.assertIn(
                formatted["tier"],
                valid_tiers,
                f"Tier '{formatted['tier']}' not in allowed values"
            )

    def test_location_has_required_fields(self):
        """Location object has required file and line fields."""
        finding = self.create_comprehensive_finding()
        formatted = format_finding_for_codex(finding)

        location = formatted["location"]
        self.assertIn("file", location)
        self.assertIn("line", location)
        self.assertIsInstance(location["line"], int)
        self.assertGreaterEqual(location["line"], 1)

    def test_evidence_structure_matches_schema(self):
        """Evidence object structure matches schema expectations."""
        finding = self.create_comprehensive_finding()
        formatted = format_finding_for_codex(finding)

        self.assertIn("evidence", formatted)
        evidence = formatted["evidence"]

        # Check expected evidence fields
        self.assertIn("behavioral_signature", evidence)
        self.assertIn("semantic_operations", evidence)
        self.assertIn("properties_matched", evidence)
        self.assertIn("why_vulnerable", evidence)
        self.assertIn("attack_scenario", evidence)

        # Types are correct
        self.assertIsInstance(evidence["semantic_operations"], list)
        self.assertIsInstance(evidence["attack_scenario"], list)

    def test_references_format_correctly(self):
        """References are formatted with type and id/url."""
        finding = self.create_comprehensive_finding()
        formatted = format_finding_for_codex(finding)

        self.assertIn("references", formatted)
        references = formatted["references"]

        # Should have CWE, SWC, and documentation references
        types_found = {ref["type"] for ref in references}
        self.assertIn("cwe", types_found)
        self.assertIn("swc", types_found)

    def test_minimal_finding_formats_correctly(self):
        """Minimal finding (only required fields) formats correctly."""
        finding = Finding(
            pattern="test-001",
            severity=FindingSeverity.LOW,
            confidence=FindingConfidence.LOW,
            location=Location(file="test.sol", line=1),
            description="Minimal test finding",
        )
        formatted = format_finding_for_codex(finding)

        # Should have all required fields
        self.assertIn("id", formatted)
        self.assertIn("pattern_id", formatted)
        self.assertIn("severity", formatted)
        self.assertIn("location", formatted)

    def test_formatted_finding_validates_against_schema(self):
        """Formatted finding validates against the schema."""
        finding = self.create_comprehensive_finding()
        formatted = format_finding_for_codex(finding)

        # Create a minimal valid output with this finding
        output = format_findings_for_codex([finding])

        is_valid, errors = validate_codex_output(output)
        self.assertTrue(is_valid, f"Validation errors: {errors}")


class TestSummaryCalculation(unittest.TestCase):
    """Test 3: Summary statistics are calculated correctly."""

    def test_empty_findings_summary(self):
        """Empty findings produce correct summary."""
        summary = calculate_summary([])

        self.assertEqual(summary["total_findings"], 0)
        self.assertEqual(summary["by_severity"]["critical"], 0)
        self.assertEqual(summary["by_tier"]["tier_a"], 0)
        self.assertEqual(summary["risk_score"], 0.0)

    def test_severity_counts_are_accurate(self):
        """By-severity counts match actual finding severities."""
        findings = [
            Finding(pattern="t1", severity=FindingSeverity.CRITICAL, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
            Finding(pattern="t2", severity=FindingSeverity.CRITICAL, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=2), description="t"),
            Finding(pattern="t3", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=3), description="t"),
            Finding(pattern="t4", severity=FindingSeverity.MEDIUM, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=4), description="t"),
            Finding(pattern="t5", severity=FindingSeverity.LOW, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=5), description="t"),
            Finding(pattern="t6", severity=FindingSeverity.INFO, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=6), description="t"),
        ]
        summary = calculate_summary(findings)

        self.assertEqual(summary["total_findings"], 6)
        self.assertEqual(summary["by_severity"]["critical"], 2)
        self.assertEqual(summary["by_severity"]["high"], 1)
        self.assertEqual(summary["by_severity"]["medium"], 1)
        self.assertEqual(summary["by_severity"]["low"], 1)
        self.assertEqual(summary["by_severity"]["info"], 1)

    def test_tier_counts_are_accurate(self):
        """By-tier counts match actual finding tiers."""
        findings = [
            Finding(pattern="t1", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, tier=FindingTier.TIER_A, location=Location(file="t.sol", line=1), description="t"),
            Finding(pattern="t2", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, tier=FindingTier.TIER_A, location=Location(file="t.sol", line=2), description="t"),
            Finding(pattern="t3", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, tier=FindingTier.TIER_B, location=Location(file="t.sol", line=3), description="t"),
        ]
        summary = calculate_summary(findings)

        self.assertEqual(summary["by_tier"]["tier_a"], 2)
        self.assertEqual(summary["by_tier"]["tier_b"], 1)

    def test_confidence_counts_are_accurate(self):
        """By-confidence counts match actual finding confidences."""
        findings = [
            Finding(pattern="t1", severity=FindingSeverity.MEDIUM, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
            Finding(pattern="t2", severity=FindingSeverity.MEDIUM, confidence=FindingConfidence.MEDIUM, location=Location(file="t.sol", line=2), description="t"),
            Finding(pattern="t3", severity=FindingSeverity.MEDIUM, confidence=FindingConfidence.LOW, location=Location(file="t.sol", line=3), description="t"),
        ]
        summary = calculate_summary(findings)

        self.assertEqual(summary["by_confidence"]["high"], 1)
        self.assertEqual(summary["by_confidence"]["medium"], 1)
        self.assertEqual(summary["by_confidence"]["low"], 1)

    def test_risk_score_calculation(self):
        """Risk score is calculated with correct weights."""
        # 1 critical (25) + 1 high (15) = 40
        findings = [
            Finding(pattern="t1", severity=FindingSeverity.CRITICAL, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
            Finding(pattern="t2", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=2), description="t"),
        ]
        summary = calculate_summary(findings)
        self.assertEqual(summary["risk_score"], 40.0)

    def test_risk_score_capped_at_100(self):
        """Risk score does not exceed 100."""
        # 5 critical = 125, should cap at 100
        findings = [
            Finding(pattern=f"t{i}", severity=FindingSeverity.CRITICAL, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=i), description="t")
            for i in range(5)
        ]
        summary = calculate_summary(findings)
        self.assertEqual(summary["risk_score"], 100.0)

    def test_top_risk_areas_identified(self):
        """Top risk areas are correctly identified from patterns."""
        findings = [
            Finding(pattern="reentrancy-001", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
            Finding(pattern="reentrancy-002", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=2), description="t"),
            Finding(pattern="auth-001", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=3), description="t"),
        ]
        summary = calculate_summary(findings)

        self.assertIn("top_risk_areas", summary)
        # Reentrancy should be first (2 findings) before auth (1 finding)
        self.assertEqual(summary["top_risk_areas"][0], "reentrancy")


class TestVerdictLogic(unittest.TestCase):
    """Test 4: Pass/fail/needs_review verdict logic works correctly."""

    def test_empty_findings_pass(self):
        """No findings results in pass verdict."""
        verdict = calculate_verdict([])

        self.assertEqual(verdict["status"], "pass")
        self.assertFalse(verdict["critical_issues_found"])
        self.assertTrue(verdict["deployment_recommended"])

    def test_critical_finding_fails(self):
        """Critical finding results in fail verdict."""
        findings = [
            Finding(
                pattern="t1",
                severity=FindingSeverity.CRITICAL,
                confidence=FindingConfidence.HIGH,
                location=Location(file="t.sol", line=1),
                description="Critical issue",
            )
        ]
        verdict = calculate_verdict(findings)

        self.assertEqual(verdict["status"], "fail")
        self.assertTrue(verdict["critical_issues_found"])
        self.assertFalse(verdict["deployment_recommended"])
        self.assertIn("critical", verdict["reasoning"].lower())

    def test_high_finding_needs_review(self):
        """High (but no critical) finding results in needs_review verdict."""
        findings = [
            Finding(
                pattern="t1",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.HIGH,
                location=Location(file="t.sol", line=1),
                description="High issue",
            )
        ]
        verdict = calculate_verdict(findings)

        self.assertEqual(verdict["status"], "needs_review")
        self.assertFalse(verdict["critical_issues_found"])
        self.assertFalse(verdict["deployment_recommended"])
        self.assertIn("high", verdict["reasoning"].lower())

    def test_medium_low_pass(self):
        """Only medium/low findings result in pass verdict."""
        findings = [
            Finding(pattern="t1", severity=FindingSeverity.MEDIUM, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="Medium"),
            Finding(pattern="t2", severity=FindingSeverity.LOW, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=2), description="Low"),
        ]
        verdict = calculate_verdict(findings)

        self.assertEqual(verdict["status"], "pass")
        self.assertFalse(verdict["critical_issues_found"])
        self.assertTrue(verdict["deployment_recommended"])

    def test_info_only_pass(self):
        """Info-only findings result in pass verdict."""
        findings = [
            Finding(
                pattern="t1",
                severity=FindingSeverity.INFO,
                confidence=FindingConfidence.HIGH,
                location=Location(file="t.sol", line=1),
                description="Info",
            )
        ]
        verdict = calculate_verdict(findings)

        self.assertEqual(verdict["status"], "pass")
        self.assertTrue(verdict["deployment_recommended"])

    def test_multiple_critical_still_fail(self):
        """Multiple critical findings all result in fail."""
        findings = [
            Finding(pattern=f"t{i}", severity=FindingSeverity.CRITICAL, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=i), description="Critical")
            for i in range(5)
        ]
        verdict = calculate_verdict(findings)

        self.assertEqual(verdict["status"], "fail")
        self.assertIn("5", verdict["reasoning"])  # Should mention count

    def test_verdict_has_all_required_fields(self):
        """Verdict has all schema-required fields."""
        verdict = calculate_verdict([])

        self.assertIn("status", verdict)
        self.assertIn("reasoning", verdict)
        self.assertIn("critical_issues_found", verdict)
        self.assertIn("deployment_recommended", verdict)


class TestRecommendationsPrioritization(unittest.TestCase):
    """Test 5: Recommendations are prioritized correctly."""

    def test_empty_findings_no_recommendations(self):
        """No findings produce no recommendations."""
        recommendations = generate_recommendations([])
        self.assertEqual(len(recommendations), 0)

    def test_recommendations_grouped_by_category(self):
        """Recommendations are grouped by vulnerability category."""
        findings = [
            Finding(pattern="reentrancy-001", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
            Finding(pattern="reentrancy-002", severity=FindingSeverity.MEDIUM, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=2), description="t"),
            Finding(pattern="auth-001", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=3), description="t"),
        ]
        recommendations = generate_recommendations(findings)

        # Should have one recommendation per category
        categories = [r["category"].lower() for r in recommendations]
        self.assertIn("reentrancy", categories)
        self.assertIn("auth", categories)

    def test_recommendations_sorted_by_priority(self):
        """Recommendations are sorted by priority (critical first)."""
        findings = [
            Finding(pattern="oracle-001", severity=FindingSeverity.MEDIUM, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
            Finding(pattern="reentrancy-001", severity=FindingSeverity.CRITICAL, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=2), description="t"),
            Finding(pattern="auth-001", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=3), description="t"),
        ]
        recommendations = generate_recommendations(findings)

        # First should be critical (reentrancy)
        self.assertEqual(recommendations[0]["priority"], "critical")
        # Second should be high (auth)
        self.assertEqual(recommendations[1]["priority"], "high")
        # Third should be medium (oracle)
        self.assertEqual(recommendations[2]["priority"], "medium")

    def test_recommendation_has_affected_findings(self):
        """Recommendations list affected finding IDs."""
        findings = [
            Finding(pattern="reentrancy-001", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
        ]
        recommendations = generate_recommendations(findings)

        self.assertGreater(len(recommendations), 0)
        rec = recommendations[0]
        self.assertIn("affected_findings", rec)
        self.assertIsInstance(rec["affected_findings"], list)
        self.assertGreater(len(rec["affected_findings"]), 0)

    def test_known_categories_have_recommendations(self):
        """Known vulnerability categories produce specific recommendations."""
        known_categories = ["reentrancy", "auth", "oracle", "mev", "dos", "token", "upgrade", "crypto"]

        for category in known_categories:
            findings = [
                Finding(
                    pattern=f"{category}-001",
                    severity=FindingSeverity.HIGH,
                    confidence=FindingConfidence.HIGH,
                    location=Location(file="t.sol", line=1),
                    description="t",
                )
            ]
            recommendations = generate_recommendations(findings)

            if len(recommendations) > 0:
                self.assertEqual(
                    recommendations[0]["category"].lower(),
                    category,
                    f"Category {category} should produce recommendation"
                )


class TestFullAuditOutput(unittest.TestCase):
    """Test 6: Complete audit output validates against schema."""

    def create_realistic_audit_findings(self) -> list[Finding]:
        """Create a realistic set of audit findings."""
        return [
            Finding(
                pattern="reentrancy-001",
                severity=FindingSeverity.CRITICAL,
                confidence=FindingConfidence.HIGH,
                tier=FindingTier.TIER_A,
                title="Critical Reentrancy in withdraw()",
                location=Location(file="Vault.sol", line=42, function="withdraw", contract="Vault"),
                description="State update after external call",
                evidence=Evidence(
                    behavioral_signature="R:bal->X:out->W:bal",
                    operations=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                ),
                recommended_fix="Use CEI pattern",
                cwe="CWE-841",
            ),
            Finding(
                pattern="auth-002",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.MEDIUM,
                tier=FindingTier.TIER_A,
                title="Missing Access Control on setOwner()",
                location=Location(file="Access.sol", line=15, function="setOwner", contract="Access"),
                description="Anyone can change owner",
            ),
            Finding(
                pattern="oracle-001",
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.HIGH,
                tier=FindingTier.TIER_B,
                title="Missing Oracle Staleness Check",
                location=Location(file="Price.sol", line=28, function="getPrice", contract="Price"),
                description="Oracle price may be stale",
            ),
        ]

    def test_full_output_has_all_sections(self):
        """Full output has findings, summary, metadata, etc."""
        findings = self.create_realistic_audit_findings()
        output = format_findings_for_codex(findings)

        self.assertIn("findings", output)
        self.assertIn("summary", output)
        self.assertIn("metadata", output)
        self.assertIn("recommendations", output)
        self.assertIn("verdict", output)

    def test_full_output_validates_against_schema(self):
        """Complete output validates against schema."""
        findings = self.create_realistic_audit_findings()
        contracts = [
            ContractInfo(name="Vault", file="Vault.sol", function_count=10, findings_count=1),
            ContractInfo(name="Access", file="Access.sol", function_count=5, findings_count=1),
            ContractInfo(name="Price", file="Price.sol", function_count=3, findings_count=1),
        ]
        metadata = AuditMetadata(
            vkg_version="3.5",
            codex_model="gpt-5-codex",
            graph_properties_count=150,
            patterns_evaluated=["reentrancy-*", "auth-*", "oracle-*"],
            analysis_duration_seconds=12.5,
            project_path="/path/to/project",
        )

        output = format_findings_for_codex(findings, contracts, metadata)

        is_valid, errors = validate_codex_output(output)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_full_output_json_is_valid(self):
        """Full output can be serialized to valid JSON."""
        findings = self.create_realistic_audit_findings()
        json_str = format_findings_to_json(findings)

        # Should be valid JSON
        parsed = json.loads(json_str)
        self.assertIn("findings", parsed)
        self.assertEqual(len(parsed["findings"]), 3)

    def test_output_with_no_findings_validates(self):
        """Output with no findings still validates."""
        output = format_findings_for_codex([])

        is_valid, errors = validate_codex_output(output)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

        self.assertEqual(output["summary"]["total_findings"], 0)
        self.assertEqual(output["verdict"]["status"], "pass")

    def test_output_metadata_has_required_fields(self):
        """Output metadata has all required fields."""
        output = format_findings_for_codex([])
        metadata = output["metadata"]

        self.assertIn("timestamp", metadata)
        self.assertIn("vkg_version", metadata)
        self.assertIn("schema_version", metadata)

    def test_output_timestamp_is_iso_format(self):
        """Metadata timestamp is in ISO 8601 format."""
        output = format_findings_for_codex([])
        timestamp = output["metadata"]["timestamp"]

        # Should be parseable as ISO datetime
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            self.fail(f"Timestamp '{timestamp}' is not valid ISO 8601")

    def test_contracts_analyzed_included_when_provided(self):
        """Contracts analyzed section is included when provided."""
        contracts = [
            ContractInfo(name="Vault", file="Vault.sol"),
        ]
        output = format_findings_for_codex([], contracts=contracts)

        self.assertIn("contracts_analyzed", output)
        self.assertEqual(len(output["contracts_analyzed"]), 1)
        self.assertEqual(output["contracts_analyzed"][0]["name"], "Vault")


class TestCICDHelpers(unittest.TestCase):
    """Test 7: CI/CD helper functions work correctly."""

    def test_validate_file_returns_true_for_valid(self):
        """validate_codex_output_file returns True for valid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = format_findings_for_codex([])
            output_path = Path(tmpdir) / "output.json"
            with open(output_path, "w") as f:
                json.dump(output, f)

            is_valid, errors = validate_codex_output_file(output_path)
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)

    def test_validate_file_returns_false_for_missing(self):
        """validate_codex_output_file returns False for missing file."""
        is_valid, errors = validate_codex_output_file("/nonexistent/path.json")

        self.assertFalse(is_valid)
        self.assertIn("not found", errors[0].lower())

    def test_validate_file_returns_false_for_invalid_json(self):
        """validate_codex_output_file returns False for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid.json"
            path.write_text("{ not valid json")

            is_valid, errors = validate_codex_output_file(path)

            self.assertFalse(is_valid)
            self.assertIn("Invalid JSON", errors[0])

    def test_validate_file_returns_false_for_schema_mismatch(self):
        """validate_codex_output_file returns False for schema mismatch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mismatch.json"
            # Missing required fields
            path.write_text('{"findings": [], "extra": true}')

            is_valid, errors = validate_codex_output_file(path)

            self.assertFalse(is_valid)

    def test_schema_version_constant_exists(self):
        """Schema version constant is defined."""
        self.assertIsNotNone(CODEX_OUTPUT_SCHEMA_VERSION)
        self.assertIsInstance(CODEX_OUTPUT_SCHEMA_VERSION, str)
        # Should be semver-like
        parts = CODEX_OUTPUT_SCHEMA_VERSION.split(".")
        self.assertEqual(len(parts), 3)

    def test_vkg_version_constant_exists(self):
        """VKG version constant is defined."""
        self.assertIsNotNone(VKG_VERSION)
        self.assertIsInstance(VKG_VERSION, str)

    def test_write_schema_creates_valid_file(self):
        """write_output_schema creates a valid schema file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            result = write_output_schema(schema_path)

            self.assertTrue(result.exists())

            # Validate the schema file
            with open(result) as f:
                schema = json.load(f)

            self.assertEqual(schema["$schema"], "http://json-schema.org/draft-07/schema#")

    def test_get_schema_json_returns_valid_json(self):
        """get_schema_json returns valid JSON string."""
        json_str = get_schema_json()

        parsed = json.loads(json_str)
        self.assertIn("$schema", parsed)
        self.assertIn("properties", parsed)


class TestCodexCLISimulation(unittest.TestCase):
    """Simulate Codex CLI workflow without actually running it.

    Tests that the VKG output format would work with:
    - `codex exec --output-schema vkg-schema.json`
    - Processing the structured output
    - CI/CD integration scenarios
    """

    def test_audit_workflow_simulation(self):
        """Simulate complete audit workflow output."""
        # Step 1: Generate schema file (for --output-schema)
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "vkg-audit-schema.json"
            write_output_schema(schema_path)

            # Step 2: Simulate VKG producing audit output
            findings = [
                Finding(
                    pattern="reentrancy-001",
                    severity=FindingSeverity.CRITICAL,
                    confidence=FindingConfidence.HIGH,
                    location=Location(file="Vault.sol", line=42),
                    description="Reentrancy vulnerability",
                ),
            ]
            output = format_findings_for_codex(findings)

            # Step 3: Write output (simulating Codex -o flag)
            output_path = Path(tmpdir) / "audit-results.json"
            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)

            # Step 4: Validate output against schema
            is_valid, errors = validate_codex_output_file(output_path)
            self.assertTrue(is_valid, f"Validation errors: {errors}")

            # Step 5: Extract key info (CI/CD processing)
            with open(output_path) as f:
                result = json.load(f)

            critical_count = result["summary"]["by_severity"]["critical"]
            verdict_status = result["verdict"]["status"]

            self.assertEqual(critical_count, 1)
            self.assertEqual(verdict_status, "fail")  # Critical = fail

    def test_cicd_exit_code_determination(self):
        """Test exit code determination for CI/CD."""
        # Critical findings = exit 1 (fail)
        output_critical = format_findings_for_codex([
            Finding(pattern="t", severity=FindingSeverity.CRITICAL, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
        ])
        self.assertEqual(output_critical["verdict"]["status"], "fail")

        # High findings = exit 2 (needs review)
        output_high = format_findings_for_codex([
            Finding(pattern="t", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
        ])
        self.assertEqual(output_high["verdict"]["status"], "needs_review")

        # Low/medium = exit 0 (pass)
        output_low = format_findings_for_codex([
            Finding(pattern="t", severity=FindingSeverity.LOW, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
        ])
        self.assertEqual(output_low["verdict"]["status"], "pass")

    def test_github_action_output_format(self):
        """Test output format suitable for GitHub Action processing."""
        findings = [
            Finding(pattern="reentrancy-001", severity=FindingSeverity.CRITICAL, confidence=FindingConfidence.HIGH, location=Location(file="Vault.sol", line=42, function="withdraw"), description="Reentrancy"),
        ]
        output = format_findings_for_codex(findings)

        # Should be able to extract summary for PR comment
        summary = output["summary"]
        self.assertIn("total_findings", summary)
        self.assertIn("by_severity", summary)

        # Should be able to list findings for annotation
        for finding in output["findings"]:
            self.assertIn("location", finding)
            self.assertIn("file", finding["location"])
            self.assertIn("line", finding["location"])
            self.assertIn("severity", finding)
            self.assertIn("title", finding)

    def test_jq_compatible_extraction(self):
        """Test that output is suitable for jq processing (common in CI)."""
        findings = [
            Finding(pattern="t1", severity=FindingSeverity.CRITICAL, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=1), description="t"),
            Finding(pattern="t2", severity=FindingSeverity.HIGH, confidence=FindingConfidence.HIGH, location=Location(file="t.sol", line=2), description="t"),
        ]
        json_str = format_findings_to_json(findings)

        # Parse and verify jq-style extractions would work
        data = json.loads(json_str)

        # jq '.summary.by_severity.critical'
        self.assertEqual(data["summary"]["by_severity"]["critical"], 1)

        # jq '.findings | length'
        self.assertEqual(len(data["findings"]), 2)

        # jq '.verdict.status'
        self.assertEqual(data["verdict"]["status"], "fail")


class TestSchemaCompatibility(unittest.TestCase):
    """Test schema compatibility with Codex expectations."""

    def test_schema_matches_research_specification(self):
        """Schema matches the specification from R3.3 research."""
        schema = get_output_schema()

        # Required top-level fields from research
        expected_required = {"findings", "summary", "metadata"}
        actual_required = set(schema["required"])
        self.assertEqual(actual_required, expected_required)

        # Optional sections from research
        properties = schema["properties"]
        self.assertIn("contracts_analyzed", properties)
        self.assertIn("recommendations", properties)
        self.assertIn("verdict", properties)

    def test_finding_schema_matches_research(self):
        """Finding schema matches research specification."""
        schema = get_output_schema()
        finding_schema = schema["properties"]["findings"]["items"]

        # Required finding fields from research
        expected_required = {
            "id", "pattern_id", "severity", "confidence",
            "title", "description", "location"
        }
        actual_required = set(finding_schema["required"])
        self.assertEqual(actual_required, expected_required)

        # Severity enum from research
        severity_enum = set(finding_schema["properties"]["severity"]["enum"])
        expected_severities = {"critical", "high", "medium", "low", "info"}
        self.assertEqual(severity_enum, expected_severities)

    def test_evidence_schema_has_vkg_properties(self):
        """Evidence schema includes VKG-specific properties."""
        schema = get_output_schema()
        evidence_schema = schema["properties"]["findings"]["items"]["properties"]["evidence"]["properties"]

        # VKG-specific evidence fields
        self.assertIn("behavioral_signature", evidence_schema)
        self.assertIn("semantic_operations", evidence_schema)
        self.assertIn("properties_matched", evidence_schema)
        self.assertIn("properties_missing", evidence_schema)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_finding_with_unicode(self):
        """Finding with unicode characters formats correctly."""
        finding = Finding(
            pattern="test-001",
            severity=FindingSeverity.MEDIUM,
            confidence=FindingConfidence.MEDIUM,
            location=Location(file="Test\u00e9.sol", line=1),
            description="Unicode test: \u2713 \u2717 \u26a0",
        )
        formatted = format_finding_for_codex(finding)
        json_str = json.dumps(formatted, ensure_ascii=False)  # Should not raise

        self.assertIn("\u2713", json_str)

    def test_finding_with_long_description(self):
        """Finding with very long description formats correctly."""
        long_desc = "A" * 10000
        finding = Finding(
            pattern="test-001",
            severity=FindingSeverity.MEDIUM,
            confidence=FindingConfidence.MEDIUM,
            location=Location(file="test.sol", line=1),
            description=long_desc,
        )
        formatted = format_finding_for_codex(finding)

        self.assertEqual(len(formatted["description"]), 10000)

    def test_finding_with_special_characters_in_path(self):
        """Finding with special characters in file path formats correctly."""
        finding = Finding(
            pattern="test-001",
            severity=FindingSeverity.MEDIUM,
            confidence=FindingConfidence.MEDIUM,
            location=Location(file="contracts/My Contract (v2).sol", line=1),
            description="test",
        )
        formatted = format_finding_for_codex(finding)

        self.assertEqual(formatted["location"]["file"], "contracts/My Contract (v2).sol")

    def test_metadata_with_empty_patterns(self):
        """Metadata with empty patterns list is valid."""
        metadata = AuditMetadata(patterns_evaluated=[])
        output = format_findings_for_codex([], metadata=metadata)

        is_valid, errors = validate_codex_output(output)
        self.assertTrue(is_valid, f"Validation errors: {errors}")

    def test_large_number_of_findings(self):
        """Large number of findings formats correctly."""
        findings = [
            Finding(
                pattern=f"test-{i:03d}",
                severity=FindingSeverity.MEDIUM,
                confidence=FindingConfidence.MEDIUM,
                location=Location(file=f"test{i}.sol", line=i),
                description=f"Finding {i}",
            )
            for i in range(100)
        ]
        output = format_findings_for_codex(findings)

        self.assertEqual(len(output["findings"]), 100)
        self.assertEqual(output["summary"]["total_findings"], 100)


if __name__ == "__main__":
    unittest.main()
