"""Tests for Partial Results Handling (Task 10.6).

Tests the result aggregation and partial result handling for graceful
degradation when some analysis sources fail.
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from alphaswarm_sol.analysis.results import (
    SourceResult,
    AggregatedResults,
    ResultAggregator,
)
from alphaswarm_sol.analysis.partial import (
    format_partial_results,
    merge_partial_results,
    combine_results,
    PartialResultHandler,
)


class TestSourceResult(unittest.TestCase):
    """Test SourceResult dataclass."""

    def test_complete_result(self):
        """Complete result has complete=True."""
        result = SourceResult(
            source="slither",
            complete=True,
            findings=[{"id": 1}],
        )

        self.assertTrue(result.complete)
        self.assertTrue(result.ok)
        self.assertFalse(result.failed)
        self.assertEqual(len(result.findings), 1)

    def test_failed_result(self):
        """Failed result has error."""
        result = SourceResult(
            source="aderyn",
            complete=False,
            error="Timeout",
        )

        self.assertFalse(result.complete)
        self.assertFalse(result.ok)
        self.assertTrue(result.failed)
        self.assertEqual(result.error, "Timeout")

    def test_result_with_retry_command(self):
        """Failed result can have retry command."""
        result = SourceResult(
            source="aderyn",
            complete=False,
            error="Timeout",
            retry_command="vkg tools run aderyn --timeout 120",
        )

        self.assertIsNotNone(result.retry_command)

    def test_result_to_dict(self):
        """SourceResult serializes to dict."""
        result = SourceResult(
            source="slither",
            complete=True,
            findings=[{"id": 1}, {"id": 2}],
            runtime_ms=500,
        )

        data = result.to_dict()

        self.assertEqual(data["source"], "slither")
        self.assertTrue(data["complete"])
        self.assertEqual(data["finding_count"], 2)
        self.assertEqual(data["runtime_ms"], 500)

    def test_result_with_metadata(self):
        """SourceResult can have metadata."""
        result = SourceResult(
            source="vkg",
            complete=True,
            findings=[],
            metadata={"version": "4.0.0"},
        )

        self.assertEqual(result.metadata["version"], "4.0.0")


class TestAggregatedResults(unittest.TestCase):
    """Test AggregatedResults class."""

    def test_empty_results(self):
        """Empty results are not complete."""
        results = AggregatedResults()

        self.assertEqual(results.total_findings, 0)
        self.assertFalse(results.complete)
        self.assertEqual(results.total_sources, 0)
        self.assertEqual(results.success_rate, 0.0)

    def test_total_findings(self):
        """Total findings sums all sources."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, [{"id": 1}]))
        results.add_result(SourceResult("b", True, [{"id": 2}, {"id": 3}]))

        self.assertEqual(results.total_findings, 3)

    def test_complete_when_all_sources_complete(self):
        """Complete only when all sources complete."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, []))
        results.add_result(SourceResult("b", True, []))

        self.assertTrue(results.complete)
        self.assertFalse(results.partial)

    def test_incomplete_when_any_source_fails(self):
        """Incomplete when any source fails."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, []))
        results.add_result(SourceResult("b", False, error="Failed"))

        self.assertFalse(results.complete)
        self.assertTrue(results.partial)
        self.assertIn("b", results.incomplete_sources)
        self.assertIn("a", results.successful_sources)

    def test_success_rate(self):
        """Success rate calculated correctly."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, []))
        results.add_result(SourceResult("b", False, error="Failed"))
        results.add_result(SourceResult("c", True, []))

        self.assertAlmostEqual(results.success_rate, 2/3)

    def test_get_source(self):
        """Can retrieve specific source result."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, [{"id": 1}]))
        results.add_result(SourceResult("b", True, []))

        source_a = results.get_source("a")
        source_c = results.get_source("c")

        self.assertIsNotNone(source_a)
        self.assertEqual(len(source_a.findings), 1)
        self.assertIsNone(source_c)

    def test_get_all_findings(self):
        """Get all findings annotated with source."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, [{"id": 1}]))
        results.add_result(SourceResult("b", True, [{"id": 2}]))

        findings = results.get_all_findings()

        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["_source"], "a")
        self.assertEqual(findings[1]["_source"], "b")

    def test_get_errors(self):
        """Get all errors from failed sources."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, []))
        results.add_result(SourceResult("b", False, error="Timeout"))
        results.add_result(SourceResult("c", False, error="Not found"))

        errors = results.get_errors()

        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]["source"], "b")
        self.assertEqual(errors[1]["error"], "Not found")

    def test_to_dict(self):
        """AggregatedResults serializes to dict."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, [{"id": 1}]))
        results.add_result(SourceResult("b", False, error="Failed"))

        data = results.to_dict()

        self.assertEqual(data["total_findings"], 1)
        self.assertFalse(data["complete"])
        self.assertTrue(data["partial"])
        self.assertIn("b", data["incomplete_sources"])
        self.assertIn("timestamp", data)


class TestResultAggregator(unittest.TestCase):
    """Test ResultAggregator class."""

    def test_add_success(self):
        """Add success correctly."""
        agg = ResultAggregator()
        agg.add_success("slither", [{"id": 1}], runtime_ms=500)

        results = agg.get_results()

        self.assertEqual(results.total_findings, 1)
        self.assertTrue(results.complete)

    def test_add_failure(self):
        """Add failure with retry command."""
        agg = ResultAggregator()
        agg.add_failure("aderyn", "Connection error", retry_command="vkg tools run aderyn")

        results = agg.get_results()

        self.assertFalse(results.complete)
        self.assertEqual(results.sources[0].error, "Connection error")
        self.assertIsNotNone(results.sources[0].retry_command)

    def test_add_timeout(self):
        """Add timeout with automatic retry command."""
        agg = ResultAggregator()
        agg.add_timeout("aderyn", 60)

        results = agg.get_results()

        self.assertFalse(results.complete)
        self.assertIn("60s", results.sources[0].error)
        # Retry command should suggest double timeout
        self.assertIn("120", results.sources[0].retry_command)

    def test_add_skipped(self):
        """Add skipped source."""
        agg = ResultAggregator()
        agg.add_skipped("medusa", "Tool not installed")

        results = agg.get_results()

        self.assertFalse(results.complete)
        self.assertIn("Skipped", results.sources[0].error)
        self.assertIsNone(results.sources[0].retry_command)

    def test_add_success_with_metadata(self):
        """Add success with metadata."""
        agg = ResultAggregator()
        agg.add_success("vkg", [{"id": 1}], metadata={"version": "4.0"})

        results = agg.get_results()

        self.assertEqual(results.sources[0].metadata["version"], "4.0")

    def test_add_from_tool_result_success(self):
        """Add from ToolResult-like object (success)."""
        # Use spec to prevent MagicMock from auto-creating attributes
        tool_result = MagicMock(spec=["success", "output", "runtime_ms"])
        tool_result.success = True
        tool_result.output = '[{"id": 1}]'
        tool_result.runtime_ms = 100

        agg = ResultAggregator()
        agg.add_from_tool_result("slither", tool_result)

        results = agg.get_results()

        self.assertTrue(results.complete)
        self.assertEqual(results.total_findings, 1)

    def test_add_from_tool_result_failure(self):
        """Add from ToolResult-like object (failure)."""
        tool_result = MagicMock()
        tool_result.success = False
        tool_result.error = "Command failed"
        tool_result.recovery = "vkg tools run slither"

        agg = ResultAggregator()
        agg.add_from_tool_result("slither", tool_result)

        results = agg.get_results()

        self.assertFalse(results.complete)

    def test_add_from_tool_result_timeout(self):
        """Add from ToolResult with timeout error."""
        tool_result = MagicMock()
        tool_result.success = False
        tool_result.error = "Command timed out after 60s"
        tool_result.recovery = None

        agg = ResultAggregator()
        agg.add_from_tool_result("aderyn", tool_result)

        results = agg.get_results()

        self.assertFalse(results.complete)

    def test_reset(self):
        """Reset clears all results."""
        agg = ResultAggregator()
        agg.add_success("a", [{"id": 1}])

        agg.reset()
        results = agg.get_results()

        self.assertEqual(results.total_findings, 0)


class TestFormatPartialResults(unittest.TestCase):
    """Test result formatting."""

    def test_complete_results(self):
        """Complete results show 'Complete'."""
        results = AggregatedResults()
        results.add_result(SourceResult("slither", True, [{"id": 1}]))

        output = format_partial_results(results)

        self.assertIn("Complete", output)
        self.assertNotIn("Partial", output)

    def test_partial_results(self):
        """Partial results show warning."""
        results = AggregatedResults()
        results.add_result(SourceResult("slither", True, []))
        results.add_result(SourceResult("aderyn", False, error="Timeout"))

        output = format_partial_results(results)

        self.assertIn("Partial", output)
        self.assertIn("failed", output.lower())

    def test_shows_total_findings(self):
        """Output shows total findings."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, [{"id": 1}, {"id": 2}]))

        output = format_partial_results(results)

        self.assertIn("2", output)
        self.assertIn("findings", output.lower())

    def test_shows_retry_commands(self):
        """Partial results show retry commands."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, []))
        results.add_result(SourceResult(
            "b", False, error="Timeout",
            retry_command="vkg tools run b --timeout 120"
        ))

        output = format_partial_results(results)

        self.assertIn("Retry", output)
        self.assertIn("vkg tools run b", output)


class TestMergePartialResults(unittest.TestCase):
    """Test result merging."""

    def test_merge_replaces_failed(self):
        """Merge replaces failed source with new success."""
        existing = AggregatedResults()
        existing.add_result(SourceResult("a", True, [{"id": 1}]))
        existing.add_result(SourceResult("b", False, error="Failed"))

        new = AggregatedResults()
        new.add_result(SourceResult("b", True, [{"id": 2}]))

        merged = merge_partial_results(existing, new)

        self.assertTrue(merged.complete)
        self.assertEqual(merged.total_findings, 2)

    def test_merge_preserves_existing_success(self):
        """Merge preserves existing success not in new."""
        existing = AggregatedResults()
        existing.add_result(SourceResult("a", True, [{"id": 1}]))

        new = AggregatedResults()
        new.add_result(SourceResult("b", True, [{"id": 2}]))

        merged = merge_partial_results(existing, new)

        sources = {s.source for s in merged.sources}
        self.assertEqual(sources, {"a", "b"})

    def test_merge_new_takes_priority(self):
        """New results override existing for same source."""
        existing = AggregatedResults()
        existing.add_result(SourceResult("a", True, [{"id": 1}]))

        new = AggregatedResults()
        new.add_result(SourceResult("a", True, [{"id": 2}, {"id": 3}]))

        merged = merge_partial_results(existing, new)

        source_a = merged.get_source("a")
        self.assertEqual(len(source_a.findings), 2)  # New results, not old


class TestCombineResults(unittest.TestCase):
    """Test combining multiple result sets."""

    def test_combine_empty(self):
        """Combining nothing returns empty."""
        combined = combine_results()

        self.assertEqual(combined.total_sources, 0)

    def test_combine_single(self):
        """Combining single set returns same."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, [{"id": 1}]))

        combined = combine_results(results)

        self.assertEqual(combined.total_findings, 1)

    def test_combine_multiple(self):
        """Combining multiple sets merges all."""
        set1 = AggregatedResults()
        set1.add_result(SourceResult("a", True, [{"id": 1}]))

        set2 = AggregatedResults()
        set2.add_result(SourceResult("b", True, [{"id": 2}]))

        combined = combine_results(set1, set2)

        self.assertEqual(combined.total_sources, 2)
        self.assertEqual(combined.total_findings, 2)

    def test_combine_later_overrides(self):
        """Later sets override earlier for same source."""
        set1 = AggregatedResults()
        set1.add_result(SourceResult("a", False, error="Failed"))

        set2 = AggregatedResults()
        set2.add_result(SourceResult("a", True, [{"id": 1}]))

        combined = combine_results(set1, set2)

        self.assertTrue(combined.complete)


class TestPartialResultHandler(unittest.TestCase):
    """Test PartialResultHandler class."""

    def test_handle_complete(self):
        """Handler returns True for complete results."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, []))

        handler = PartialResultHandler(auto_suggest_retry=False)
        is_complete = handler.handle(results)

        self.assertTrue(is_complete)

    def test_handle_partial(self):
        """Handler returns False for partial results."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, []))
        results.add_result(SourceResult("b", False, error="Failed"))

        handler = PartialResultHandler(auto_suggest_retry=False)
        is_complete = handler.handle(results)

        self.assertFalse(is_complete)

    def test_format_summary_complete(self):
        """Summary for complete results."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, [{"id": 1}]))

        handler = PartialResultHandler()
        summary = handler.format_summary(results)

        self.assertIn("Complete", summary)
        self.assertIn("1", summary)

    def test_format_summary_partial(self):
        """Summary for partial results."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", True, []))
        results.add_result(SourceResult("b", False, error="Failed"))

        handler = PartialResultHandler()
        summary = handler.format_summary(results)

        self.assertIn("Partial", summary)
        self.assertIn("1/2", summary)

    def test_should_warn(self):
        """Should warn when results incomplete."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", False, error="Failed"))

        handler = PartialResultHandler()

        self.assertTrue(handler.should_warn(results))

    def test_get_recommendations_timeout(self):
        """Recommendations for timeout errors."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", False, error="Timeout occurred"))

        handler = PartialResultHandler()
        recs = handler.get_recommendations(results)

        self.assertTrue(any("timeout" in r.lower() for r in recs))

    def test_get_recommendations_not_found(self):
        """Recommendations for not found errors."""
        results = AggregatedResults()
        results.add_result(SourceResult("a", False, error="Tool not found"))

        handler = PartialResultHandler()
        recs = handler.get_recommendations(results)

        self.assertTrue(any("install" in r.lower() for r in recs))


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for real-world scenarios."""

    def test_typical_analysis_flow(self):
        """Test typical multi-tool analysis flow."""
        agg = ResultAggregator()

        # Slither succeeds
        agg.add_success("slither", [
            {"id": "SL-001", "title": "Reentrancy"},
            {"id": "SL-002", "title": "Unchecked return"},
        ], runtime_ms=2500)

        # Aderyn times out
        agg.add_timeout("aderyn", 60)

        # VKG succeeds
        agg.add_success("vkg", [
            {"id": "VKG-001", "title": "Missing access control"},
        ], runtime_ms=800)

        results = agg.get_results()

        self.assertFalse(results.complete)
        self.assertTrue(results.partial)
        self.assertEqual(results.total_findings, 3)
        self.assertEqual(len(results.successful_sources), 2)
        self.assertEqual(len(results.incomplete_sources), 1)

        # Format should show partial
        output = format_partial_results(results)
        self.assertIn("Partial", output)
        self.assertIn("aderyn", output.lower())

    def test_retry_and_merge_flow(self):
        """Test retry flow with merging."""
        # Initial run: aderyn fails
        agg1 = ResultAggregator()
        agg1.add_success("slither", [{"id": "SL-001"}])
        agg1.add_timeout("aderyn", 60)
        results1 = agg1.get_results()

        self.assertFalse(results1.complete)

        # Retry: aderyn succeeds
        agg2 = ResultAggregator()
        agg2.add_success("aderyn", [{"id": "AD-001"}])
        results2 = agg2.get_results()

        # Merge results
        merged = merge_partial_results(results1, results2)

        self.assertTrue(merged.complete)
        self.assertEqual(merged.total_findings, 2)

    def test_all_fail_gracefully(self):
        """Test handling when all tools fail."""
        agg = ResultAggregator()
        agg.add_failure("slither", "Parse error")
        agg.add_timeout("aderyn", 60)
        agg.add_skipped("medusa", "Not installed")

        results = agg.get_results()

        self.assertFalse(results.complete)
        self.assertEqual(results.total_findings, 0)
        self.assertEqual(results.success_rate, 0.0)

        # Should still format without errors
        output = format_partial_results(results)
        self.assertIn("Partial", output)


if __name__ == "__main__":
    unittest.main()
