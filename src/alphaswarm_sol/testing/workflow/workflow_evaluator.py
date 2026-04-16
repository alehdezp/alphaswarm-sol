"""
Workflow Evaluator for VRS Testing.

This module provides evaluation capabilities for workflow transcripts,
classifying results as pass/fail/error/drift/timeout and extracting
actionable error information.

Usage:
    from alphaswarm_sol.testing.workflow import (
        WorkflowEvaluator,
        EvalCriteria,
        EvalStatus,
    )

    criteria = EvalCriteria(
        expected_patterns=["PASS", "Complete"],
        forbidden_patterns=["Error:", "Failed"],
        expected_files=["output.json"],
    )

    evaluator = WorkflowEvaluator()
    result = evaluator.evaluate(transcript, criteria)

    if result.status == EvalStatus.PASS:
        print("Workflow passed!")
    else:
        for error in result.errors:
            print(f"{error.error_type}: {error.message}")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EvalStatus(Enum):
    """Status of a workflow evaluation."""

    PASS = "pass"  # All criteria met
    FAIL = "fail"  # Criteria not met
    ERROR = "error"  # Execution error occurred
    DRIFT = "drift"  # Behavior changed from expected
    TIMEOUT = "timeout"  # Execution timed out


class ErrorType(Enum):
    """Types of errors that can be detected."""

    IMPORT_ERROR = "import_error"
    TYPE_ERROR = "type_error"
    ATTRIBUTE_ERROR = "attribute_error"
    VALUE_ERROR = "value_error"
    RUNTIME_ERROR = "runtime_error"
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_ERROR = "permission_error"
    ASSERTION_ERROR = "assertion_error"
    MISSING_PATTERN = "missing_pattern"
    FORBIDDEN_PATTERN = "forbidden_pattern"
    MISSING_FILE = "missing_file"
    UNEXPECTED_OUTPUT = "unexpected_output"
    DRIFT_DETECTED = "drift_detected"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class EvalCriteria:
    """Criteria for evaluating a workflow transcript."""

    # Patterns that must be present in output
    expected_patterns: list[str] = field(default_factory=list)

    # Patterns that must NOT be present
    forbidden_patterns: list[str] = field(default_factory=list)

    # Files that should be created/modified
    expected_files: list[str] = field(default_factory=list)

    # Maximum allowed errors in output
    max_errors: int = 0

    # Expected duration range (seconds)
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None

    # Drift detection - previous successful output to compare against
    baseline_output: Optional[str] = None
    drift_threshold: float = 0.3  # Max allowed difference ratio

    # Custom validators (pattern -> validation function)
    custom_validators: dict[str, callable] = field(default_factory=dict)


@dataclass
class EvalError:
    """Information about an error detected during evaluation."""

    error_type: ErrorType
    message: str
    location: Optional[str] = None  # File:line if available
    context: Optional[str] = None  # Surrounding context
    fixable_immediately: bool = False
    fix_suggestion: Optional[str] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "location": self.location,
            "context": self.context,
            "fixable_immediately": self.fixable_immediately,
            "fix_suggestion": self.fix_suggestion,
            "stack_trace": self.stack_trace,
        }


@dataclass
class EvalResult:
    """Result of evaluating a workflow transcript."""

    status: EvalStatus
    passed_criteria: list[str] = field(default_factory=list)
    failed_criteria: list[str] = field(default_factory=list)
    errors: list[EvalError] = field(default_factory=list)
    drift_indicators: list[str] = field(default_factory=list)
    transcript: str = ""
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_pass(self) -> bool:
        """Check if evaluation passed."""
        return self.status == EvalStatus.PASS

    @property
    def has_fixable_errors(self) -> bool:
        """Check if any errors are immediately fixable."""
        return any(e.fixable_immediately for e in self.errors)

    @property
    def fixable_errors(self) -> list[EvalError]:
        """Get list of immediately fixable errors."""
        return [e for e in self.errors if e.fixable_immediately]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "passed_criteria": self.passed_criteria,
            "failed_criteria": self.failed_criteria,
            "errors": [e.to_dict() for e in self.errors],
            "drift_indicators": self.drift_indicators,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat(),
        }


class WorkflowEvaluator:
    """
    Evaluator for workflow transcripts.

    This evaluator analyzes workflow output to determine success/failure,
    extract errors, and detect behavioral drift.

    Example:
        evaluator = WorkflowEvaluator()

        criteria = EvalCriteria(
            expected_patterns=["PASS", "Complete"],
            forbidden_patterns=["Error:", "FAIL"],
        )

        result = evaluator.evaluate(transcript, criteria)
        print(f"Status: {result.status.value}")
        for error in result.errors:
            print(f"  - {error.message}")
    """

    # Patterns for extracting Python errors
    PYTHON_ERROR_PATTERNS = {
        ErrorType.IMPORT_ERROR: re.compile(
            r"ImportError: ([^\n]+)", re.MULTILINE
        ),
        ErrorType.TYPE_ERROR: re.compile(
            r"TypeError: ([^\n]+)", re.MULTILINE
        ),
        ErrorType.ATTRIBUTE_ERROR: re.compile(
            r"AttributeError: ([^\n]+)", re.MULTILINE
        ),
        ErrorType.VALUE_ERROR: re.compile(
            r"ValueError: ([^\n]+)", re.MULTILINE
        ),
        ErrorType.RUNTIME_ERROR: re.compile(
            r"RuntimeError: ([^\n]+)", re.MULTILINE
        ),
        ErrorType.FILE_NOT_FOUND: re.compile(
            r"FileNotFoundError: ([^\n]+)", re.MULTILINE
        ),
        ErrorType.PERMISSION_ERROR: re.compile(
            r"PermissionError: ([^\n]+)", re.MULTILINE
        ),
        ErrorType.ASSERTION_ERROR: re.compile(
            r"AssertionError: ([^\n]+)", re.MULTILINE
        ),
    }

    # Pattern for extracting file:line location from traceback
    TRACEBACK_LOCATION = re.compile(
        r'File "([^"]+)", line (\d+)', re.MULTILINE
    )

    # Pattern for extracting stack traces
    STACK_TRACE_PATTERN = re.compile(
        r"Traceback \(most recent call last\):.*?(?=\n\n|\Z)",
        re.DOTALL,
    )

    def __init__(self, working_dir: Optional[str] = None):
        """
        Initialize the evaluator.

        Args:
            working_dir: Working directory for file checks
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def evaluate(
        self,
        transcript: str,
        criteria: EvalCriteria,
        duration_seconds: float = 0.0,
        timed_out: bool = False,
    ) -> EvalResult:
        """
        Evaluate a workflow transcript against criteria.

        Args:
            transcript: The workflow output transcript
            criteria: Evaluation criteria
            duration_seconds: Actual execution duration
            timed_out: Whether the execution timed out

        Returns:
            EvalResult with status and detailed analysis
        """
        result = EvalResult(
            status=EvalStatus.PASS,
            transcript=transcript,
            duration_seconds=duration_seconds,
        )

        # Check for timeout first
        if timed_out:
            result.status = EvalStatus.TIMEOUT
            result.errors.append(
                EvalError(
                    error_type=ErrorType.TIMEOUT,
                    message="Workflow execution timed out",
                    fixable_immediately=False,
                )
            )
            return result

        # Extract and analyze errors from transcript
        self._extract_errors(transcript, result)

        # Check expected patterns
        self._check_expected_patterns(transcript, criteria, result)

        # Check forbidden patterns
        self._check_forbidden_patterns(transcript, criteria, result)

        # Check expected files
        self._check_expected_files(criteria, result)

        # Check duration constraints
        self._check_duration(duration_seconds, criteria, result)

        # Check for drift
        if criteria.baseline_output:
            self._check_drift(transcript, criteria, result)

        # Run custom validators
        self._run_custom_validators(transcript, criteria, result)

        # Determine final status
        self._determine_status(criteria, result)

        return result

    def _extract_errors(self, transcript: str, result: EvalResult) -> None:
        """Extract Python errors from transcript."""
        # Find all stack traces first
        stack_traces = self.STACK_TRACE_PATTERN.findall(transcript)

        # Extract typed errors
        for error_type, pattern in self.PYTHON_ERROR_PATTERNS.items():
            matches = pattern.finditer(transcript)
            for match in matches:
                message = match.group(1)

                # Find location in traceback
                location = None
                context = None

                # Look for nearest stack trace
                error_pos = match.start()
                for trace in stack_traces:
                    trace_pos = transcript.find(trace)
                    if trace_pos < error_pos:
                        # Extract location from this trace
                        loc_matches = self.TRACEBACK_LOCATION.findall(trace)
                        if loc_matches:
                            last_loc = loc_matches[-1]
                            location = f"{last_loc[0]}:{last_loc[1]}"

                        # Get context (last few lines before error)
                        context = trace[-500:] if len(trace) > 500 else trace

                # Determine if fixable
                fixable, suggestion = self._analyze_fixability(
                    error_type, message, location
                )

                result.errors.append(
                    EvalError(
                        error_type=error_type,
                        message=message,
                        location=location,
                        context=context,
                        fixable_immediately=fixable,
                        fix_suggestion=suggestion,
                    )
                )

    def _check_expected_patterns(
        self,
        transcript: str,
        criteria: EvalCriteria,
        result: EvalResult,
    ) -> None:
        """Check that all expected patterns are present."""
        for pattern in criteria.expected_patterns:
            if pattern in transcript:
                result.passed_criteria.append(f"found: {pattern}")
            else:
                result.failed_criteria.append(f"missing: {pattern}")
                result.errors.append(
                    EvalError(
                        error_type=ErrorType.MISSING_PATTERN,
                        message=f"Expected pattern not found: {pattern}",
                        fixable_immediately=False,
                    )
                )

    def _check_forbidden_patterns(
        self,
        transcript: str,
        criteria: EvalCriteria,
        result: EvalResult,
    ) -> None:
        """Check that no forbidden patterns are present."""
        for pattern in criteria.forbidden_patterns:
            if pattern in transcript:
                result.failed_criteria.append(f"forbidden: {pattern}")
                result.errors.append(
                    EvalError(
                        error_type=ErrorType.FORBIDDEN_PATTERN,
                        message=f"Forbidden pattern found: {pattern}",
                        fixable_immediately=False,
                    )
                )
            else:
                result.passed_criteria.append(f"absent: {pattern}")

    def _check_expected_files(
        self,
        criteria: EvalCriteria,
        result: EvalResult,
    ) -> None:
        """Check that expected files exist."""
        for file_path in criteria.expected_files:
            full_path = self.working_dir / file_path
            if full_path.exists():
                result.passed_criteria.append(f"file exists: {file_path}")
            else:
                result.failed_criteria.append(f"file missing: {file_path}")
                result.errors.append(
                    EvalError(
                        error_type=ErrorType.MISSING_FILE,
                        message=f"Expected file not found: {file_path}",
                        fixable_immediately=False,
                    )
                )

    def _check_duration(
        self,
        duration: float,
        criteria: EvalCriteria,
        result: EvalResult,
    ) -> None:
        """Check duration constraints."""
        if criteria.min_duration is not None and duration < criteria.min_duration:
            result.drift_indicators.append(
                f"Duration {duration:.1f}s below minimum {criteria.min_duration:.1f}s"
            )

        if criteria.max_duration is not None and duration > criteria.max_duration:
            result.drift_indicators.append(
                f"Duration {duration:.1f}s above maximum {criteria.max_duration:.1f}s"
            )

    def _check_drift(
        self,
        transcript: str,
        criteria: EvalCriteria,
        result: EvalResult,
    ) -> None:
        """Check for behavioral drift against baseline."""
        if not criteria.baseline_output:
            return

        baseline = criteria.baseline_output

        # Simple difference ratio
        from difflib import SequenceMatcher

        ratio = SequenceMatcher(None, baseline, transcript).ratio()
        difference = 1 - ratio

        if difference > criteria.drift_threshold:
            result.drift_indicators.append(
                f"Output differs {difference:.1%} from baseline "
                f"(threshold: {criteria.drift_threshold:.1%})"
            )
            result.errors.append(
                EvalError(
                    error_type=ErrorType.DRIFT_DETECTED,
                    message=f"Behavioral drift detected: {difference:.1%} difference",
                    fixable_immediately=False,
                )
            )

    def _run_custom_validators(
        self,
        transcript: str,
        criteria: EvalCriteria,
        result: EvalResult,
    ) -> None:
        """Run custom validation functions."""
        for name, validator in criteria.custom_validators.items():
            try:
                is_valid, message = validator(transcript)
                if is_valid:
                    result.passed_criteria.append(f"custom:{name}")
                else:
                    result.failed_criteria.append(f"custom:{name}")
                    result.errors.append(
                        EvalError(
                            error_type=ErrorType.UNKNOWN,
                            message=f"Custom validator '{name}' failed: {message}",
                            fixable_immediately=False,
                        )
                    )
            except Exception as e:
                logger.warning(f"Custom validator {name} raised exception: {e}")
                result.errors.append(
                    EvalError(
                        error_type=ErrorType.RUNTIME_ERROR,
                        message=f"Custom validator '{name}' error: {e}",
                        fixable_immediately=False,
                    )
                )

    def _determine_status(
        self,
        criteria: EvalCriteria,
        result: EvalResult,
    ) -> None:
        """Determine final evaluation status."""
        # Check error count
        if len(result.errors) > criteria.max_errors:
            # If we have drift errors, mark as drift
            drift_errors = [
                e for e in result.errors
                if e.error_type == ErrorType.DRIFT_DETECTED
            ]
            if drift_errors:
                result.status = EvalStatus.DRIFT
            # If we have Python runtime errors, mark as error
            elif any(
                e.error_type
                in (
                    ErrorType.IMPORT_ERROR,
                    ErrorType.TYPE_ERROR,
                    ErrorType.ATTRIBUTE_ERROR,
                    ErrorType.RUNTIME_ERROR,
                )
                for e in result.errors
            ):
                result.status = EvalStatus.ERROR
            else:
                result.status = EvalStatus.FAIL
        elif result.failed_criteria:
            result.status = EvalStatus.FAIL
        else:
            result.status = EvalStatus.PASS

    def _analyze_fixability(
        self,
        error_type: ErrorType,
        message: str,
        location: Optional[str],
    ) -> tuple[bool, Optional[str]]:
        """
        Analyze if an error is immediately fixable.

        Returns:
            Tuple of (is_fixable, suggestion)
        """
        # ImportError patterns that are usually fixable
        if error_type == ErrorType.IMPORT_ERROR:
            if "No module named" in message:
                module = message.split("'")[1] if "'" in message else message
                return True, f"Install missing module: pip install {module}"
            if "cannot import name" in message:
                return True, f"Check import path and fix typo in: {location}"

        # Missing file errors
        if error_type == ErrorType.FILE_NOT_FOUND:
            return True, f"Create missing file or fix path"

        # Attribute errors often indicate typos
        if error_type == ErrorType.ATTRIBUTE_ERROR:
            if "has no attribute" in message:
                return True, f"Check for typo in attribute name at {location}"

        # Type errors might be fixable
        if error_type == ErrorType.TYPE_ERROR:
            if "argument" in message and "expected" in message:
                return True, f"Fix argument type at {location}"

        return False, None
