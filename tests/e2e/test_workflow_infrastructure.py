"""
Tests for VRS Workflow Testing Infrastructure.

Tests the workflow evaluator and improvement loop
components that enable automated Claude Code workflow testing.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from alphaswarm_sol.testing.workflow import (
    WorkflowEvaluator,
    EvalStatus,
    EvalCriteria,
    EvalError,
    EvalResult,
)
from alphaswarm_sol.testing.workflow.workflow_evaluator import ErrorType


# =============================================================================
# WorkflowEvaluator Tests
# =============================================================================


class TestWorkflowEvaluator:
    """Tests for WorkflowEvaluator class."""

    def test_evaluator_init(self):
        """Test evaluator initialization."""
        evaluator = WorkflowEvaluator()
        assert evaluator.working_dir == Path.cwd()

    def test_evaluator_init_custom_dir(self):
        """Test evaluator with custom working directory."""
        evaluator = WorkflowEvaluator(working_dir="/tmp")
        assert evaluator.working_dir == Path("/tmp")

    def test_eval_status_enum(self):
        """Test EvalStatus enum values."""
        assert EvalStatus.PASS.value == "pass"
        assert EvalStatus.FAIL.value == "fail"
        assert EvalStatus.ERROR.value == "error"
        assert EvalStatus.DRIFT.value == "drift"
        assert EvalStatus.TIMEOUT.value == "timeout"

    def test_eval_criteria_defaults(self):
        """Test EvalCriteria default values."""
        criteria = EvalCriteria()

        assert criteria.expected_patterns == []
        assert criteria.forbidden_patterns == []
        assert criteria.expected_files == []
        assert criteria.max_errors == 0
        assert criteria.drift_threshold == 0.3

    def test_evaluate_pass_simple(self):
        """Test simple passing evaluation."""
        evaluator = WorkflowEvaluator()
        criteria = EvalCriteria(
            expected_patterns=["Complete"],
            forbidden_patterns=["Error:"],
        )

        result = evaluator.evaluate(
            transcript="Workflow Complete successfully",
            criteria=criteria,
        )

        assert result.status == EvalStatus.PASS
        assert "found: Complete" in result.passed_criteria
        assert "absent: Error:" in result.passed_criteria
        assert len(result.errors) == 0

    def test_evaluate_fail_missing_pattern(self):
        """Test failing evaluation with missing pattern."""
        evaluator = WorkflowEvaluator()
        criteria = EvalCriteria(
            expected_patterns=["Complete", "Success"],
        )

        result = evaluator.evaluate(
            transcript="Workflow running...",
            criteria=criteria,
        )

        assert result.status == EvalStatus.FAIL
        assert "missing: Complete" in result.failed_criteria
        assert "missing: Success" in result.failed_criteria

    def test_evaluate_fail_forbidden_pattern(self):
        """Test failing evaluation with forbidden pattern."""
        evaluator = WorkflowEvaluator()
        criteria = EvalCriteria(
            forbidden_patterns=["Error:"],
        )

        result = evaluator.evaluate(
            transcript="Error: Something went wrong",
            criteria=criteria,
        )

        assert result.status == EvalStatus.FAIL
        assert "forbidden: Error:" in result.failed_criteria

    def test_evaluate_error_import_error(self):
        """Test error detection for ImportError."""
        evaluator = WorkflowEvaluator()
        criteria = EvalCriteria()

        transcript = """
Traceback (most recent call last):
  File "src/module.py", line 5
    from missing import thing
ImportError: No module named 'missing'
"""

        result = evaluator.evaluate(transcript, criteria)

        assert result.status == EvalStatus.ERROR
        assert len(result.errors) == 1
        assert result.errors[0].error_type == ErrorType.IMPORT_ERROR
        assert "missing" in result.errors[0].message

    def test_evaluate_error_type_error(self):
        """Test error detection for TypeError."""
        evaluator = WorkflowEvaluator()
        criteria = EvalCriteria()

        transcript = """
TypeError: expected str, got int
"""

        result = evaluator.evaluate(transcript, criteria)

        assert result.status == EvalStatus.ERROR
        assert len(result.errors) == 1
        assert result.errors[0].error_type == ErrorType.TYPE_ERROR

    def test_evaluate_timeout(self):
        """Test timeout handling."""
        evaluator = WorkflowEvaluator()
        criteria = EvalCriteria()

        result = evaluator.evaluate(
            transcript="partial output...",
            criteria=criteria,
            timed_out=True,
        )

        assert result.status == EvalStatus.TIMEOUT
        assert len(result.errors) == 1
        assert result.errors[0].error_type == ErrorType.TIMEOUT

    def test_evaluate_drift_detected(self):
        """Test drift detection against baseline."""
        evaluator = WorkflowEvaluator()

        baseline = "Expected output with specific content A B C"
        transcript = "Completely different output X Y Z"

        criteria = EvalCriteria(
            baseline_output=baseline,
            drift_threshold=0.3,
        )

        result = evaluator.evaluate(transcript, criteria)

        assert result.status == EvalStatus.DRIFT
        assert len(result.drift_indicators) > 0
        assert any("drift" in e.error_type.value for e in result.errors)

    def test_evaluate_drift_acceptable(self):
        """Test drift within acceptable threshold."""
        evaluator = WorkflowEvaluator()

        baseline = "Expected output with content"
        transcript = "Expected output with content and a bit more"

        criteria = EvalCriteria(
            baseline_output=baseline,
            drift_threshold=0.5,  # High threshold
        )

        result = evaluator.evaluate(transcript, criteria)

        # Should pass because difference is within threshold
        assert result.status == EvalStatus.PASS

    def test_evaluate_expected_files(self):
        """Test expected files checking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create expected file
            expected_file = Path(tmpdir) / "output.json"
            expected_file.write_text("{}")

            evaluator = WorkflowEvaluator(working_dir=tmpdir)
            criteria = EvalCriteria(
                expected_files=["output.json", "missing.json"],
            )

            result = evaluator.evaluate("", criteria)

            assert "file exists: output.json" in result.passed_criteria
            assert "file missing: missing.json" in result.failed_criteria

    def test_eval_error_to_dict(self):
        """Test EvalError serialization."""
        error = EvalError(
            error_type=ErrorType.IMPORT_ERROR,
            message="No module named 'test'",
            location="src/test.py:5",
            fixable_immediately=True,
            fix_suggestion="pip install test",
        )

        data = error.to_dict()

        assert data["error_type"] == "import_error"
        assert data["message"] == "No module named 'test'"
        assert data["location"] == "src/test.py:5"
        assert data["fixable_immediately"] is True

    def test_eval_result_properties(self):
        """Test EvalResult convenience properties."""
        result = EvalResult(
            status=EvalStatus.FAIL,
            errors=[
                EvalError(
                    error_type=ErrorType.IMPORT_ERROR,
                    message="test",
                    fixable_immediately=True,
                ),
                EvalError(
                    error_type=ErrorType.RUNTIME_ERROR,
                    message="test2",
                    fixable_immediately=False,
                ),
            ],
        )

        assert result.is_pass is False
        assert result.has_fixable_errors is True
        assert len(result.fixable_errors) == 1


# =============================================================================
# Integration Tests (WorkflowEvaluator only)
# =============================================================================


class TestWorkflowInfrastructureIntegration:
    """Integration tests for workflow testing infrastructure."""

    def test_multiple_error_types(self):
        """Test handling multiple error types."""
        transcript = """
ImportError: No module named 'mod1'
TypeError: expected str, got int
FileNotFoundError: [Errno 2] No such file: 'config.yaml'
AttributeError: 'NoneType' has no attribute 'foo'
"""

        evaluator = WorkflowEvaluator()
        result = evaluator.evaluate(transcript, EvalCriteria())

        assert result.status == EvalStatus.ERROR
        assert len(result.errors) == 4

        error_types = {e.error_type for e in result.errors}
        assert ErrorType.IMPORT_ERROR in error_types
        assert ErrorType.TYPE_ERROR in error_types
        assert ErrorType.FILE_NOT_FOUND in error_types
        assert ErrorType.ATTRIBUTE_ERROR in error_types

    def test_criteria_all_pass(self):
        """Test criteria that all pass."""
        transcript = """
Starting workflow...
Building graph...
Analysis complete.
Findings: 3 issues found
Verdict: PASS
Report generated: output.json
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create expected file
            (Path(tmpdir) / "output.json").write_text("{}")

            evaluator = WorkflowEvaluator(working_dir=tmpdir)
            criteria = EvalCriteria(
                expected_patterns=["complete", "Findings:", "PASS"],
                forbidden_patterns=["Error:", "FAIL", "Traceback"],
                expected_files=["output.json"],
            )

            result = evaluator.evaluate(transcript, criteria)

            assert result.status == EvalStatus.PASS
            assert len(result.failed_criteria) == 0
            assert len(result.errors) == 0
