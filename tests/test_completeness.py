"""
Tests for Analysis Completeness Report

Validates the CompletenessReport class for tracking analysis coverage.
"""

import json
import tempfile
from pathlib import Path

import pytest

from alphaswarm_sol.report.completeness import (
    BuildInfo,
    CompletenessReport,
    CompletionStatus,
    COMPLETENESS_REPORT_SCHEMA,
    SkipReason,
    SkippedContract,
    UnsupportedFeature,
    generate_completeness_report,
)


class TestCompletionStatus:
    """Test completion status enum."""

    def test_complete_status(self):
        """Complete status when all contracts analyzed."""
        report = CompletenessReport()
        report.add_analyzed("Token.sol", "Token")
        report.add_analyzed("Vault.sol", "Vault")

        assert report.status == CompletionStatus.COMPLETE
        assert report.coverage_pct == 100.0

    def test_partial_status(self):
        """Partial status when some contracts skipped."""
        report = CompletenessReport()
        report.add_analyzed("Token.sol", "Token")
        report.add_skipped("YulHelper.sol", "YulHelper", SkipReason.INLINE_ASSEMBLY)

        assert report.status == CompletionStatus.PARTIAL
        assert report.coverage_pct == 50.0

    def test_failed_status_explicit(self):
        """Failed status when explicitly marked."""
        report = CompletenessReport()
        report.mark_failed("Slither crashed")

        assert report.status == CompletionStatus.FAILED
        assert "Slither crashed" in report.warnings[0]

    def test_failed_status_no_contracts(self):
        """Failed status when no contracts found."""
        report = CompletenessReport()

        assert report.status == CompletionStatus.FAILED
        assert report.coverage_pct == 0.0


class TestCompletenessReport:
    """Test CompletenessReport class."""

    def test_add_analyzed(self):
        """Test adding analyzed contracts."""
        report = CompletenessReport()
        report.add_analyzed("src/Token.sol", "Token")
        report.add_analyzed("src/Token.sol", "TokenStorage")
        report.add_analyzed("src/Vault.sol", "Vault")

        assert len(report.contracts_analyzed) == 3
        assert "src/Token.sol:Token" in report.contracts_analyzed
        assert "src/Token.sol:TokenStorage" in report.contracts_analyzed
        assert len(report.contracts_analyzed_files) == 2

    def test_add_skipped(self):
        """Test adding skipped contracts."""
        report = CompletenessReport()
        report.add_skipped(
            "src/YulHelper.sol",
            "YulHelper",
            SkipReason.INLINE_ASSEMBLY,
            "Contains Yul blocks",
        )

        assert len(report.skipped) == 1
        assert report.skipped[0].contract == "YulHelper"
        assert report.skipped[0].reason == SkipReason.INLINE_ASSEMBLY
        assert report.skipped[0].details == "Contains Yul blocks"
        assert len(report.warnings) == 1

    def test_add_unsupported_feature(self):
        """Test adding unsupported features."""
        report = CompletenessReport()
        report.add_unsupported_feature("inline_assembly", "Token.sol:100")
        report.add_unsupported_feature("inline_assembly", "Token.sol:200")
        report.add_unsupported_feature("delegatecall", "Proxy.sol:50")

        assert len(report.unsupported_features) == 2
        assert report.unsupported_features["inline_assembly"].occurrences == 2
        assert len(report.unsupported_features["inline_assembly"].locations) == 2
        assert report.unsupported_features["delegatecall"].occurrences == 1

    def test_coverage_calculation(self):
        """Test coverage percentage calculation."""
        report = CompletenessReport()

        # Empty report
        assert report.coverage_pct == 0.0

        # Add analyzed
        report.add_analyzed("A.sol", "A")
        report.add_analyzed("B.sol", "B")
        report.add_analyzed("C.sol", "C")
        assert report.coverage_pct == 100.0

        # Add skipped
        report.add_skipped("D.sol", "D", SkipReason.PARSE_ERROR)
        assert report.coverage_pct == 75.0

    def test_to_dict(self):
        """Test dictionary conversion."""
        report = CompletenessReport()
        report.add_analyzed("Token.sol", "Token")
        report.add_skipped("YulHelper.sol", "YulHelper", SkipReason.INLINE_ASSEMBLY)
        report.add_unsupported_feature("inline_assembly", "YulHelper.sol:10")
        report.add_warning("Custom warning")
        report.build_info.solc_version = "0.8.19"
        report.build_info.framework = "foundry"

        data = report.to_dict()

        assert data["status"] == "partial"
        assert data["coverage_pct"] == 50.0
        assert data["contracts_analyzed"] == 1
        assert data["contracts_skipped"] == 1
        assert data["contracts_total"] == 2
        assert len(data["analyzed_contracts"]) == 1
        assert len(data["skipped_details"]) == 1
        assert data["skipped_details"][0]["reason"] == "inline_assembly"
        assert len(data["unsupported_features"]) == 1
        assert data["build_info"]["solc_version"] == "0.8.19"

    def test_to_json(self):
        """Test JSON conversion."""
        report = CompletenessReport()
        report.add_analyzed("Token.sol", "Token")

        json_str = report.to_json()
        data = json.loads(json_str)

        assert data["status"] == "complete"
        assert data["contracts_analyzed"] == 1

    def test_save_and_load(self):
        """Test saving and loading report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.json"

            # Create and save
            report = CompletenessReport()
            report.add_analyzed("Token.sol", "Token")
            report.add_skipped("YulHelper.sol", "YulHelper", SkipReason.INLINE_ASSEMBLY, "Has Yul")
            report.add_unsupported_feature("inline_assembly", "YulHelper.sol:10")
            report.build_info.solc_version = "0.8.19"
            report.save(path)

            # Load and verify
            loaded = CompletenessReport.load(path)
            assert loaded.status == report.status
            assert len(loaded.contracts_analyzed) == len(report.contracts_analyzed)
            assert len(loaded.skipped) == len(report.skipped)
            assert loaded.skipped[0].reason == SkipReason.INLINE_ASSEMBLY
            assert loaded.build_info.solc_version == "0.8.19"

    def test_from_dict_with_failure(self):
        """Test loading a failed report."""
        data = {
            "status": "failed",
            "coverage_pct": 0,
            "contracts_analyzed": 0,
            "contracts_skipped": 0,
            "analyzed_contracts": [],
            "skipped_details": [],
            "unsupported_features": [],
            "warnings": ["Analysis failed: Test failure"],
            "build_info": {},
            "failure_reason": "Test failure",
        }

        report = CompletenessReport.from_dict(data)
        assert report.status == CompletionStatus.FAILED
        assert "Test failure" in report._failure_reason


class TestSkipReason:
    """Test skip reason enum."""

    def test_all_reasons(self):
        """Verify all skip reasons are valid."""
        reasons = [
            SkipReason.INLINE_ASSEMBLY,
            SkipReason.PROXY_UNRESOLVED,
            SkipReason.PARSE_ERROR,
            SkipReason.UNSUPPORTED_SOLC,
            SkipReason.COMPILATION_ERROR,
            SkipReason.TIMEOUT,
            SkipReason.IMPORT_ERROR,
            SkipReason.UNKNOWN,
        ]
        for reason in reasons:
            assert isinstance(reason.value, str)


class TestBuildInfo:
    """Test build info class."""

    def test_default_values(self):
        """Test default build info values."""
        info = BuildInfo()
        assert info.solc_version == ""
        assert info.framework == "unknown"
        assert info.optimizer_enabled is False

    def test_to_dict(self):
        """Test build info to dict."""
        info = BuildInfo(
            solc_version="0.8.19",
            framework="foundry",
            optimizer_enabled=True,
            slither_version="0.10.0",
        )
        data = info.to_dict()
        assert data["solc_version"] == "0.8.19"
        assert data["framework"] == "foundry"
        assert data["optimizer_enabled"] is True


class TestUnsupportedFeature:
    """Test unsupported feature class."""

    def test_to_dict(self):
        """Test unsupported feature to dict."""
        feature = UnsupportedFeature(
            feature="inline_assembly",
            occurrences=3,
            locations=["Token.sol:10", "Token.sol:20"],
        )
        data = feature.to_dict()
        assert data["feature"] == "inline_assembly"
        assert data["occurrences"] == 3
        assert len(data["locations"]) == 2


class TestSkippedContract:
    """Test skipped contract class."""

    def test_to_dict(self):
        """Test skipped contract to dict."""
        skipped = SkippedContract(
            contract="YulHelper",
            reason=SkipReason.INLINE_ASSEMBLY,
            details="Contains Yul blocks",
            file_path="src/YulHelper.sol",
        )
        data = skipped.to_dict()
        assert data["contract"] == "YulHelper"
        assert data["reason"] == "inline_assembly"
        assert data["reason_code"] == "inline_assembly"
        assert data["details"] == "Contains Yul blocks"
        assert data["file_path"] == "src/YulHelper.sol"


class TestCLIOutput:
    """Test CLI output formatting."""

    def test_complete_output(self):
        """Test CLI output for complete analysis."""
        report = CompletenessReport()
        report.add_analyzed("Token.sol", "Token")
        report.add_analyzed("Vault.sol", "Vault")
        report.build_info.framework = "foundry"
        report.build_info.solc_version = "0.8.19"

        output = report.format_cli_output()

        assert "COMPLETE" in output
        assert "100.0%" in output
        assert "2/2 contracts" in output
        assert "Foundry" in output
        assert "0.8.19" in output

    def test_partial_output(self):
        """Test CLI output for partial analysis."""
        report = CompletenessReport()
        report.add_analyzed("Token.sol", "Token")
        report.add_skipped("YulHelper.sol", "YulHelper", SkipReason.INLINE_ASSEMBLY)
        report.add_unsupported_feature("inline_assembly", "YulHelper.sol:10")

        output = report.format_cli_output()

        assert "PARTIAL" in output
        assert "50.0%" in output
        assert "WARNINGS:" in output
        assert "inline_assembly" in output.lower()

    def test_failed_output(self):
        """Test CLI output for failed analysis."""
        report = CompletenessReport()
        report.mark_failed("Compilation error")

        output = report.format_cli_output()

        assert "FAILED" in output

    def test_warning_limit(self):
        """Test warning output limits."""
        report = CompletenessReport()
        for i in range(15):
            report.add_warning(f"Warning {i}")

        output = report.format_cli_output()

        # Should show first 10 warnings
        assert "Warning 0" in output
        assert "Warning 9" in output
        assert "and 5 more" in output


class TestGenerateCompletenessReport:
    """Test the generate_completeness_report function."""

    def test_generate_from_args(self):
        """Test generating report from arguments."""
        metadata = {
            "solc_version_selected": "0.8.19",
            "framework": "foundry",
            "slither_version": "0.10.0",
        }
        analyzed = [
            ("Token.sol", "Token"),
            ("Vault.sol", "Vault"),
        ]
        skipped = [
            ("YulHelper.sol", "YulHelper", SkipReason.INLINE_ASSEMBLY, "Has Yul"),
        ]
        unsupported = [
            ("inline_assembly", "YulHelper.sol:10"),
        ]
        warnings = ["Custom warning"]

        report = generate_completeness_report(
            metadata, analyzed, skipped, unsupported, warnings
        )

        assert report.status == CompletionStatus.PARTIAL
        assert len(report.contracts_analyzed) == 2
        assert len(report.skipped) == 1
        assert "inline_assembly" in report.unsupported_features
        assert "Custom warning" in report.warnings
        assert report.build_info.solc_version == "0.8.19"


class TestSchemaValidation:
    """Test JSON schema validation."""

    def test_schema_exists(self):
        """Verify schema is defined."""
        assert COMPLETENESS_REPORT_SCHEMA is not None
        assert "$schema" in COMPLETENESS_REPORT_SCHEMA

    def test_report_matches_schema(self):
        """Test that report output matches schema."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        report = CompletenessReport()
        report.add_analyzed("Token.sol", "Token")
        report.add_skipped("YulHelper.sol", "YulHelper", SkipReason.INLINE_ASSEMBLY)
        report.add_unsupported_feature("inline_assembly", "YulHelper.sol:10")

        data = report.to_dict()

        # Should not raise
        jsonschema.validate(data, COMPLETENESS_REPORT_SCHEMA)

    def test_schema_required_fields(self):
        """Verify required fields in schema."""
        required = COMPLETENESS_REPORT_SCHEMA.get("required", [])
        assert "status" in required
        assert "coverage_pct" in required
        assert "contracts_analyzed" in required
        assert "contracts_skipped" in required
