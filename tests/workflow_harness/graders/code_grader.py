"""Deterministic grading: string match, regex, schema validation, tool usage.

CodeGrader inspects CollectedOutput against expected values using pure code
checks (no LLM calls). Each method returns a GradeResult with pass/fail,
score (0-100 integer), reason, and grader type.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.workflow_harness.lib.output_collector import CollectedOutput

from src.alphaswarm_sol.testing.scenarios.config_schema import GraderConfig


@dataclass
class GradeResult:
    """Result of grading a scenario run.

    Attributes:
        passed: Whether the check passed.
        score: Integer score from 0 (total failure) to 100 (perfect).
        reason: Human-readable explanation of the result.
        grader_type: "code" or "model" -- identifies which grader produced this.
    """

    passed: bool
    score: int
    reason: str
    grader_type: str


class CodeGrader:
    """Deterministic grading: string match, regex, schema validation, tool usage.

    All methods accept a CollectedOutput (from 3.1b-02's OutputCollector) and
    return a GradeResult. No LLM calls are made.
    """

    def _get_grading_text(self, output: CollectedOutput, config: "GraderConfig | None" = None) -> str:
        """Get text to grade against, based on config target.

        Args:
            output: Collected scenario output.
            config: Optional grader config with target field.

        Returns:
            Text string to grade against.
        """
        target = getattr(config, "target", None) if config else None

        if target == "response":
            return output.response_text
        if target == "structured_output":
            return json.dumps(output.structured_output) if output.structured_output else ""

        # Default: use summary
        from tests.workflow_harness.lib.output_collector import OutputCollector
        collector = OutputCollector()
        return collector.summary(output)

    def grade_string_match(
        self, output: CollectedOutput, expected: list[str], config: "GraderConfig | None" = None
    ) -> GradeResult:
        """Check that output contains all expected strings.

        Args:
            output: Collected scenario output.
            expected: List of strings that must all appear.
            config: Optional grader config for target routing.

        Returns:
            GradeResult with score = percentage of strings found (0-100).
        """
        text = self._get_grading_text(output, config)

        found = [s for s in expected if s in text]
        missing = [s for s in expected if s not in text]

        if not expected:
            return GradeResult(
                passed=True, score=100, reason="No expected strings specified", grader_type="code"
            )

        score = int(len(found) / len(expected) * 100)
        if missing:
            return GradeResult(
                passed=False,
                score=score,
                reason=f"Missing {len(missing)}/{len(expected)} strings: {missing}",
                grader_type="code",
            )
        return GradeResult(
            passed=True, score=100, reason=f"All {len(expected)} strings found", grader_type="code"
        )

    def grade_regex(self, output: CollectedOutput, pattern: str, config: "GraderConfig | None" = None) -> GradeResult:
        """Check that output matches a regex pattern.

        Args:
            output: Collected scenario output.
            pattern: Regular expression pattern to search for.
            config: Optional grader config for target routing.

        Returns:
            GradeResult with score 100 if match found, 0 otherwise.
        """
        text = self._get_grading_text(output, config)

        try:
            match = re.search(pattern, text)
        except re.error as exc:
            return GradeResult(
                passed=False, score=0, reason=f"Invalid regex: {exc}", grader_type="code"
            )

        if match:
            return GradeResult(
                passed=True,
                score=100,
                reason=f"Regex matched: '{match.group()}'",
                grader_type="code",
            )
        return GradeResult(
            passed=False,
            score=0,
            reason=f"Regex '{pattern}' did not match output",
            grader_type="code",
        )

    def grade_schema(self, output: CollectedOutput, schema_path: str) -> GradeResult:
        """Validate structured_output against a JSON Schema.

        Args:
            output: Collected scenario output (must have structured_output).
            schema_path: Path to JSON Schema file.

        Returns:
            GradeResult with score 100 if valid, 0 otherwise.
        """
        if output.structured_output is None:
            return GradeResult(
                passed=False,
                score=0,
                reason="No structured_output to validate",
                grader_type="code",
            )

        schema_file = Path(schema_path)
        if not schema_file.exists():
            return GradeResult(
                passed=False,
                score=0,
                reason=f"Schema file not found: {schema_path}",
                grader_type="code",
            )

        try:
            import jsonschema

            with open(schema_file) as f:
                schema = json.load(f)
            jsonschema.validate(instance=output.structured_output, schema=schema)
            return GradeResult(
                passed=True,
                score=100,
                reason="Structured output validates against schema",
                grader_type="code",
            )
        except ImportError:
            return GradeResult(
                passed=False,
                score=0,
                reason="jsonschema package not installed",
                grader_type="code",
            )
        except jsonschema.ValidationError as exc:
            return GradeResult(
                passed=False,
                score=0,
                reason=f"Schema validation failed: {exc.message}",
                grader_type="code",
            )

    def grade_tool_usage(
        self, output: CollectedOutput, expected_tools: list[str]
    ) -> GradeResult:
        """Check that expected tools were used during the run.

        Args:
            output: Collected scenario output.
            expected_tools: List of tool names that should appear in tool_sequence.

        Returns:
            GradeResult with score = percentage of expected tools found (0-100).
        """
        if not expected_tools:
            return GradeResult(
                passed=True, score=100, reason="No expected tools specified", grader_type="code"
            )

        actual_tools = set(output.tool_sequence)
        found = [t for t in expected_tools if t in actual_tools]
        missing = [t for t in expected_tools if t not in actual_tools]

        score = int(len(found) / len(expected_tools) * 100)
        if missing:
            return GradeResult(
                passed=False,
                score=score,
                reason=f"Missing tools: {missing} (found: {list(actual_tools)})",
                grader_type="code",
            )
        return GradeResult(
            passed=True,
            score=100,
            reason=f"All {len(expected_tools)} expected tools used",
            grader_type="code",
        )

    def grade(self, output: CollectedOutput, config: GraderConfig) -> GradeResult:
        """Route to appropriate grading method based on config.

        Args:
            output: Collected scenario output.
            config: Grader configuration specifying method and parameters.

        Returns:
            GradeResult from the selected grading method.
        """
        method = config.method

        if method == "string_match" or method == "contains_all":
            expected = config.expected
            if isinstance(expected, str):
                expected = [expected]
            elif expected is None:
                expected = []
            elif isinstance(expected, dict):
                expected = list(expected.keys())
            return self.grade_string_match(output, expected, config)

        if method == "regex":
            pattern = config.pattern or (config.expected if isinstance(config.expected, str) else "")
            return self.grade_regex(output, pattern, config)

        if method == "schema":
            schema_path = config.schema_path or ""
            return self.grade_schema(output, schema_path)

        if method == "tool_usage":
            expected = config.expected
            if isinstance(expected, str):
                expected = [expected]
            elif expected is None:
                expected = []
            elif isinstance(expected, dict):
                expected = list(expected.keys())
            return self.grade_tool_usage(output, expected)

        return GradeResult(
            passed=False,
            score=0,
            reason=f"Unknown grading method: {method}",
            grader_type="code",
        )
