"""Tests for Orchestration Module (Phase 5 Task 5.8).

Tests tool running, deduplication, and report generation.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Any

from alphaswarm_sol.orchestration import (
    ToolStatus,
    ToolResult,
    ToolRunner,
    DeduplicatedFinding,
    deduplicate_findings,
    merge_findings,
    get_disagreements,
    get_unique_to_tool,
    CATEGORY_ALIASES,
    OrchestratorReport,
    generate_report,
    format_report,
    format_markdown_report,
)


class TestToolStatus(unittest.TestCase):
    """Tests for ToolStatus enum."""

    def test_status_values(self):
        """All expected status values exist."""
        self.assertEqual(ToolStatus.SUCCESS.value, "success")
        self.assertEqual(ToolStatus.NOT_INSTALLED.value, "not_installed")
        self.assertEqual(ToolStatus.ERROR.value, "error")
        self.assertEqual(ToolStatus.SKIPPED.value, "skipped")


class TestToolResult(unittest.TestCase):
    """Tests for ToolResult dataclass."""

    def test_basic_result(self):
        """Basic result creation."""
        result = ToolResult(
            tool="vkg",
            status=ToolStatus.SUCCESS,
            findings=[{"id": "test"}],
            execution_time=1.5,
        )
        self.assertEqual(result.tool, "vkg")
        self.assertEqual(result.status, ToolStatus.SUCCESS)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.execution_time, 1.5)

    def test_error_result(self):
        """Error result with message."""
        result = ToolResult(
            tool="slither",
            status=ToolStatus.ERROR,
            error="Tool crashed",
        )
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertEqual(result.error, "Tool crashed")
        self.assertEqual(result.findings, [])

    def test_to_dict(self):
        """Convert result to dictionary."""
        result = ToolResult(
            tool="vkg",
            status=ToolStatus.SUCCESS,
            findings=[{"id": "1"}, {"id": "2"}],
            execution_time=2.0,
        )
        d = result.to_dict()
        self.assertEqual(d["tool"], "vkg")
        self.assertEqual(d["status"], "success")
        self.assertEqual(d["findings_count"], 2)
        self.assertEqual(d["execution_time"], 2.0)


class TestToolRunner(unittest.TestCase):
    """Tests for ToolRunner class."""

    def test_vkg_always_available(self):
        """VKG is always available."""
        runner = ToolRunner(Path("."))
        self.assertTrue(runner.check_tool_installed("vkg"))

    def test_supported_tools(self):
        """Supported tools list is correct."""
        self.assertEqual(
            ToolRunner.SUPPORTED_TOOLS,
            ["vkg", "slither", "aderyn"],
        )

    def test_unknown_tool(self):
        """Unknown tool returns error status."""
        runner = ToolRunner(Path("."))
        result = runner.run_tool("unknown_tool")
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertIn("Unknown tool", result.error)

    def test_get_available_tools(self):
        """Get available tools includes at least VKG."""
        runner = ToolRunner(Path("."))
        available = runner.get_available_tools()
        self.assertIn("vkg", available)


class TestNormalization(unittest.TestCase):
    """Tests for finding normalization."""

    def test_normalize_vkg_finding(self):
        """Normalize VKG pattern match."""
        runner = ToolRunner(Path("."))
        raw = {
            "pattern_id": "reentrancy-001",
            "title": "Classic Reentrancy",
            "severity": "critical",
            "category": "reentrancy",
            "location": {
                "file": "Vault.sol",
                "line": 45,
                "function": "withdraw",
            },
            "confidence": 0.9,
        }
        normalized = runner._normalize_vkg_finding(raw)
        self.assertEqual(normalized["source"], "vkg")
        self.assertEqual(normalized["id"], "reentrancy-001")
        self.assertEqual(normalized["severity"], "critical")
        self.assertEqual(normalized["file"], "Vault.sol")
        self.assertEqual(normalized["line"], 45)
        self.assertEqual(normalized["function"], "withdraw")

    def test_normalize_slither_finding(self):
        """Normalize Slither detector result."""
        runner = ToolRunner(Path("."))
        raw = {
            "check": "reentrancy-eth",
            "description": "Reentrancy vulnerability in withdraw()",
            "impact": "High",
            "confidence": "High",
            "elements": [
                {
                    "name": "withdraw",
                    "source_mapping": {
                        "filename": "contracts/Vault.sol",
                        "lines": [45, 46, 47],
                    },
                }
            ],
        }
        normalized = runner._normalize_slither_finding(raw)
        self.assertEqual(normalized["source"], "slither")
        self.assertEqual(normalized["id"], "reentrancy-eth")
        self.assertEqual(normalized["severity"], "high")
        self.assertEqual(normalized["file"], "contracts/Vault.sol")
        self.assertEqual(normalized["line"], 45)
        self.assertEqual(normalized["confidence"], 0.9)

    def test_normalize_aderyn_finding(self):
        """Normalize Aderyn issue."""
        runner = ToolRunner(Path("."))
        raw = {
            "detector_name": "reentrancy",
            "title": "Potential Reentrancy",
            "_severity": "high",
            "instances": [
                {"src": "Vault.sol:45:12", "contract_path": "Vault"}
            ],
        }
        normalized = runner._normalize_aderyn_finding(raw)
        self.assertEqual(normalized["source"], "aderyn")
        self.assertEqual(normalized["id"], "reentrancy")
        self.assertEqual(normalized["severity"], "high")
        self.assertEqual(normalized["file"], "Vault.sol")
        self.assertEqual(normalized["line"], 45)


class TestDeduplication(unittest.TestCase):
    """Tests for deduplication logic."""

    def test_deduplicate_same_location(self):
        """Findings at same location are deduplicated."""
        findings = [
            {
                "source": "vkg",
                "file": "Vault.sol",
                "line": 45,
                "category": "reentrancy",
                "severity": "high",
            },
            {
                "source": "slither",
                "file": "Vault.sol",
                "line": 47,
                "category": "reentrancy-eth",
                "severity": "high",
            },
        ]
        deduped = deduplicate_findings(findings, line_tolerance=5)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(set(deduped[0].sources), {"vkg", "slither"})
        self.assertTrue(deduped[0].agreement)

    def test_deduplicate_different_files(self):
        """Findings in different files are not deduplicated."""
        findings = [
            {
                "source": "vkg",
                "file": "Vault.sol",
                "line": 45,
                "category": "reentrancy",
                "severity": "high",
            },
            {
                "source": "slither",
                "file": "Token.sol",
                "line": 45,
                "category": "reentrancy",
                "severity": "high",
            },
        ]
        deduped = deduplicate_findings(findings, line_tolerance=5)
        self.assertEqual(len(deduped), 2)

    def test_deduplicate_different_categories(self):
        """Findings with different categories at same location stay separate."""
        findings = [
            {
                "source": "vkg",
                "file": "Vault.sol",
                "line": 45,
                "category": "reentrancy",
                "severity": "high",
            },
            {
                "source": "slither",
                "file": "Vault.sol",
                "line": 46,
                "category": "access-control",
                "severity": "medium",
            },
        ]
        deduped = deduplicate_findings(findings, line_tolerance=5)
        self.assertEqual(len(deduped), 2)

    def test_category_normalization(self):
        """Similar categories are normalized."""
        findings = [
            {
                "source": "vkg",
                "file": "Vault.sol",
                "line": 45,
                "category": "reentrancy",
                "severity": "high",
            },
            {
                "source": "slither",
                "file": "Vault.sol",
                "line": 46,
                "category": "reentrancy-eth",
                "severity": "high",
            },
            {
                "source": "aderyn",
                "file": "Vault.sol",
                "line": 47,
                "category": "reentrancy-no-eth",
                "severity": "high",
            },
        ]
        deduped = deduplicate_findings(findings, line_tolerance=5)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(set(deduped[0].sources), {"vkg", "slither", "aderyn"})

    def test_disagreement_on_severity(self):
        """Disagreement on severity is flagged."""
        findings = [
            {
                "source": "vkg",
                "file": "Vault.sol",
                "line": 45,
                "category": "reentrancy",
                "severity": "critical",
            },
            {
                "source": "slither",
                "file": "Vault.sol",
                "line": 45,
                "category": "reentrancy",
                "severity": "low",
            },
        ]
        deduped = deduplicate_findings(findings, line_tolerance=5)
        self.assertEqual(len(deduped), 1)
        self.assertFalse(deduped[0].agreement)
        # Should use most severe
        self.assertEqual(deduped[0].severity, "critical")

    def test_empty_findings(self):
        """Empty findings list returns empty result."""
        deduped = deduplicate_findings([])
        self.assertEqual(deduped, [])

    def test_line_tolerance_boundary(self):
        """Findings at tolerance boundary are grouped."""
        findings = [
            {
                "source": "vkg",
                "file": "Vault.sol",
                "line": 40,
                "category": "reentrancy",
                "severity": "high",
            },
            {
                "source": "slither",
                "file": "Vault.sol",
                "line": 45,
                "category": "reentrancy",
                "severity": "high",
            },
        ]
        # Exactly 5 lines apart with tolerance=5
        deduped = deduplicate_findings(findings, line_tolerance=5)
        self.assertEqual(len(deduped), 1)

        # 6 lines apart should not merge
        findings[1]["line"] = 46
        deduped = deduplicate_findings(findings, line_tolerance=5)
        self.assertEqual(len(deduped), 2)

    def test_severity_ordering(self):
        """Results are sorted by severity."""
        findings = [
            {
                "source": "vkg",
                "file": "A.sol",
                "line": 10,
                "category": "test",
                "severity": "low",
            },
            {
                "source": "vkg",
                "file": "B.sol",
                "line": 20,
                "category": "test",
                "severity": "critical",
            },
            {
                "source": "vkg",
                "file": "C.sol",
                "line": 30,
                "category": "test",
                "severity": "medium",
            },
        ]
        deduped = deduplicate_findings(findings)
        severities = [d.severity for d in deduped]
        self.assertEqual(severities, ["critical", "medium", "low"])


class TestDeduplicatedFinding(unittest.TestCase):
    """Tests for DeduplicatedFinding dataclass."""

    def test_source_count(self):
        """Source count property works."""
        finding = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function=None,
            category="test",
            severity="high",
            sources=["vkg", "slither"],
            findings=[],
        )
        self.assertEqual(finding.source_count, 2)

    def test_high_confidence(self):
        """High confidence requires multi-tool agreement."""
        # Single source - not high confidence
        finding1 = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function=None,
            category="test",
            severity="high",
            sources=["vkg"],
            findings=[],
            agreement=True,
        )
        self.assertFalse(finding1.high_confidence)

        # Multi-source with agreement - high confidence
        finding2 = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function=None,
            category="test",
            severity="high",
            sources=["vkg", "slither"],
            findings=[],
            agreement=True,
        )
        self.assertTrue(finding2.high_confidence)

        # Multi-source without agreement - not high confidence
        finding3 = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function=None,
            category="test",
            severity="high",
            sources=["vkg", "slither"],
            findings=[],
            agreement=False,
        )
        self.assertFalse(finding3.high_confidence)

    def test_to_dict(self):
        """Convert to dictionary."""
        finding = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function="withdraw",
            category="reentrancy",
            severity="high",
            sources=["vkg", "slither"],
            findings=[],
            agreement=True,
        )
        d = finding.to_dict()
        self.assertEqual(d["file"], "test.sol")
        self.assertEqual(d["line"], 10)
        self.assertEqual(d["function"], "withdraw")
        self.assertEqual(d["category"], "reentrancy")
        self.assertEqual(d["severity"], "high")
        self.assertEqual(d["source_count"], 2)
        self.assertTrue(d["high_confidence"])


class TestDedupHelpers(unittest.TestCase):
    """Tests for dedup helper functions."""

    def test_merge_findings(self):
        """Merge findings groups by category."""
        deduped = [
            DeduplicatedFinding(
                file="a.sol", line=1, function=None,
                category="reentrancy", severity="high",
                sources=["vkg"], findings=[],
            ),
            DeduplicatedFinding(
                file="b.sol", line=2, function=None,
                category="access_control", severity="medium",
                sources=["vkg"], findings=[],
            ),
            DeduplicatedFinding(
                file="c.sol", line=3, function=None,
                category="reentrancy", severity="critical",
                sources=["vkg"], findings=[],
            ),
        ]
        merged = merge_findings(deduped)
        self.assertEqual(len(merged["reentrancy"]), 2)
        self.assertEqual(len(merged["access_control"]), 1)

    def test_get_disagreements(self):
        """Get findings with disagreements."""
        deduped = [
            DeduplicatedFinding(
                file="a.sol", line=1, function=None,
                category="test", severity="high",
                sources=["vkg", "slither"], findings=[],
                agreement=True,
            ),
            DeduplicatedFinding(
                file="b.sol", line=2, function=None,
                category="test", severity="medium",
                sources=["vkg", "slither"], findings=[],
                agreement=False,
            ),
        ]
        disagreements = get_disagreements(deduped)
        self.assertEqual(len(disagreements), 1)
        self.assertEqual(disagreements[0].file, "b.sol")

    def test_get_unique_to_tool(self):
        """Get findings unique to a tool."""
        deduped = [
            DeduplicatedFinding(
                file="a.sol", line=1, function=None,
                category="test", severity="high",
                sources=["vkg"], findings=[],
            ),
            DeduplicatedFinding(
                file="b.sol", line=2, function=None,
                category="test", severity="high",
                sources=["vkg", "slither"], findings=[],
            ),
            DeduplicatedFinding(
                file="c.sol", line=3, function=None,
                category="test", severity="high",
                sources=["slither"], findings=[],
            ),
        ]
        vkg_only = get_unique_to_tool(deduped, "vkg")
        self.assertEqual(len(vkg_only), 1)
        self.assertEqual(vkg_only[0].file, "a.sol")

        slither_only = get_unique_to_tool(deduped, "slither")
        self.assertEqual(len(slither_only), 1)
        self.assertEqual(slither_only[0].file, "c.sol")


class TestCategoryAliases(unittest.TestCase):
    """Tests for category alias mapping."""

    def test_reentrancy_aliases(self):
        """Reentrancy category has expected aliases."""
        aliases = CATEGORY_ALIASES["reentrancy"]
        self.assertIn("reentrancy-eth", aliases)
        self.assertIn("reentrancy-no-eth", aliases)
        self.assertIn("read-only-reentrancy", aliases)

    def test_access_control_aliases(self):
        """Access control category has expected aliases."""
        aliases = CATEGORY_ALIASES["access_control"]
        self.assertIn("access-control", aliases)
        self.assertIn("tx-origin", aliases)


class TestOrchestratorReport(unittest.TestCase):
    """Tests for OrchestratorReport dataclass."""

    def test_basic_report(self):
        """Create basic report."""
        report = OrchestratorReport(
            project="./test-project",
            timestamp="2024-01-01T00:00:00",
            tools_run=["vkg", "slither"],
            tools_skipped=["aderyn"],
            total_findings=10,
            deduplicated_findings=7,
            findings_by_tool={
                "vkg": {"status": "success", "count": 5},
                "slither": {"status": "success", "count": 5},
            },
            disagreements=2,
            high_confidence_count=3,
            findings=[],
        )
        self.assertEqual(report.project, "./test-project")
        self.assertEqual(report.total_findings, 10)
        self.assertEqual(report.deduplicated_findings, 7)

    def test_to_dict(self):
        """Convert report to dictionary."""
        report = OrchestratorReport(
            project="./test",
            timestamp="2024-01-01",
            tools_run=["vkg"],
            total_findings=5,
            deduplicated_findings=3,
        )
        d = report.to_dict()
        self.assertIn("project", d)
        self.assertIn("summary", d)
        self.assertIn("tools", d)
        self.assertIn("findings", d)

    def test_to_json(self):
        """Convert report to JSON."""
        report = OrchestratorReport(
            project="./test",
            timestamp="2024-01-01",
        )
        json_str = report.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["project"], "./test")

    def test_save(self):
        """Save report to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = OrchestratorReport(
                project="./test",
                timestamp="2024-01-01",
            )
            path = Path(tmpdir) / "report.json"
            report.save(path)
            self.assertTrue(path.exists())
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["project"], "./test")


class TestGenerateReport(unittest.TestCase):
    """Tests for generate_report function."""

    def test_generate_from_results(self):
        """Generate report from tool results."""
        results = [
            ToolResult(
                tool="vkg",
                status=ToolStatus.SUCCESS,
                findings=[{"id": "1"}, {"id": "2"}],
                execution_time=1.5,
            ),
            ToolResult(
                tool="slither",
                status=ToolStatus.SUCCESS,
                findings=[{"id": "3"}],
                execution_time=2.0,
            ),
            ToolResult(
                tool="aderyn",
                status=ToolStatus.NOT_INSTALLED,
                error="not found",
            ),
        ]
        deduped = [
            DeduplicatedFinding(
                file="test.sol",
                line=10,
                function=None,
                category="test",
                severity="high",
                sources=["vkg", "slither"],
                findings=[],
                agreement=True,
            ),
        ]
        report = generate_report("./project", results, deduped)

        self.assertEqual(report.project, "./project")
        self.assertEqual(report.tools_run, ["vkg", "slither"])
        self.assertEqual(report.tools_skipped, ["aderyn"])
        self.assertEqual(report.total_findings, 3)
        self.assertEqual(report.deduplicated_findings, 1)
        self.assertEqual(report.high_confidence_count, 1)


class TestFormatReport(unittest.TestCase):
    """Tests for report formatting functions."""

    def test_format_report_text(self):
        """Format report as text."""
        report = OrchestratorReport(
            project="./test-project",
            timestamp="2024-01-01T00:00:00",
            tools_run=["vkg", "slither"],
            tools_skipped=["aderyn"],
            total_findings=10,
            deduplicated_findings=7,
            findings_by_tool={
                "vkg": {"status": "success", "count": 5, "execution_time_seconds": 1.0},
                "slither": {"status": "success", "count": 5, "execution_time_seconds": 2.0},
                "aderyn": {"status": "not_installed", "count": 0, "error": "not found"},
            },
            disagreements=2,
            high_confidence_count=3,
            findings=[
                {
                    "file": "Vault.sol",
                    "line": 45,
                    "category": "reentrancy",
                    "severity": "high",
                    "sources": ["vkg", "slither"],
                    "agreement": True,
                }
            ],
        )
        text = format_report(report)
        self.assertIn("ORCHESTRATOR REPORT", text)
        self.assertIn("./test-project", text)
        self.assertIn("vkg", text)
        self.assertIn("slither", text)

    def test_format_report_verbose(self):
        """Format report with verbose flag."""
        report = OrchestratorReport(
            project="./test",
            timestamp="2024-01-01",
            findings=[
                {
                    "file": "Test.sol",
                    "line": 10,
                    "category": "reentrancy",
                    "severity": "critical",
                    "sources": ["vkg"],
                    "agreement": True,
                }
            ],
        )
        text = format_report(report, verbose=True)
        self.assertIn("DETAILED FINDINGS", text)
        self.assertIn("Test.sol:10", text)

    def test_format_markdown_report(self):
        """Format report as Markdown."""
        report = OrchestratorReport(
            project="./test-project",
            timestamp="2024-01-01T00:00:00",
            tools_run=["vkg"],
            findings_by_tool={
                "vkg": {"status": "success", "count": 2, "execution_time_seconds": 1.0},
            },
            findings=[
                {
                    "file": "Vault.sol",
                    "line": 45,
                    "category": "reentrancy",
                    "severity": "high",
                    "sources": ["vkg"],
                    "agreement": True,
                }
            ],
        )
        md = format_markdown_report(report)
        self.assertIn("# Orchestrator Report", md)
        self.assertIn("| Metric | Value |", md)
        self.assertIn("### HIGH", md)


class TestIntegration(unittest.TestCase):
    """Integration tests for orchestration workflow."""

    def test_full_workflow(self):
        """Test complete deduplication workflow."""
        # Simulate findings from multiple tools
        vkg_findings = [
            {
                "source": "vkg",
                "file": "contracts/Vault.sol",
                "line": 45,
                "category": "reentrancy",
                "severity": "critical",
                "function": "withdraw",
            },
            {
                "source": "vkg",
                "file": "contracts/Token.sol",
                "line": 100,
                "category": "access_control",
                "severity": "high",
                "function": "mint",
            },
        ]
        slither_findings = [
            {
                "source": "slither",
                "file": "contracts/Vault.sol",
                "line": 47,
                "category": "reentrancy-eth",
                "severity": "high",
                "function": "withdraw",
            },
        ]
        aderyn_findings = [
            {
                "source": "aderyn",
                "file": "contracts/Vault.sol",
                "line": 46,
                "category": "reentrancy",
                "severity": "high",
                "function": "withdraw",
            },
        ]

        all_findings = vkg_findings + slither_findings + aderyn_findings
        deduped = deduplicate_findings(all_findings, line_tolerance=5)

        # Should have 2 findings: one for reentrancy (merged), one for access_control
        self.assertEqual(len(deduped), 2)

        # Reentrancy finding should have all 3 sources
        reentrancy = next(f for f in deduped if "reentrancy" in f.category)
        self.assertEqual(set(reentrancy.sources), {"vkg", "slither", "aderyn"})

        # Access control should only have vkg
        access = next(f for f in deduped if "access" in f.category)
        self.assertEqual(access.sources, ["vkg"])

    def test_workflow_with_report(self):
        """Test workflow including report generation."""
        results = [
            ToolResult(
                tool="vkg",
                status=ToolStatus.SUCCESS,
                findings=[
                    {
                        "source": "vkg",
                        "file": "Test.sol",
                        "line": 10,
                        "category": "reentrancy",
                        "severity": "high",
                    }
                ],
                execution_time=1.0,
            ),
        ]

        all_findings = []
        for r in results:
            all_findings.extend(r.findings)

        deduped = deduplicate_findings(all_findings)
        report = generate_report("./test", results, deduped)

        self.assertEqual(report.total_findings, 1)
        self.assertEqual(report.deduplicated_findings, 1)
        self.assertEqual(len(report.findings), 1)


if __name__ == "__main__":
    unittest.main()
