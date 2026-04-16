"""AI judge grading using Claude Code CLI subprocess.

ModelGrader shells out to ``claude --print -p`` for nuanced evaluation.
It does NOT make direct API calls. Cost is covered by Claude Code subscription.
"""

from __future__ import annotations

import json
import subprocess

from tests.workflow_harness.graders.code_grader import GradeResult
from tests.workflow_harness.lib.output_collector import CollectedOutput, OutputCollector


class ModelGrader:
    """AI judge grading using Claude Code subagent.

    Constructs a prompt combining evaluation instructions with the captured
    output summary, sends it to ``claude --print`` via subprocess, and parses
    the response for a pass/fail determination and score.

    Attributes:
        model: Claude Code model name (e.g., "sonnet", "opus"). Default: "sonnet".
        timeout: Subprocess timeout in seconds. Default: 60.
    """

    def __init__(self, model: str = "sonnet", timeout: int = 60):
        self.model = model
        self.timeout = timeout

    def grade(
        self,
        output: CollectedOutput,
        prompt: str,
        timeout: int | None = None,
    ) -> GradeResult:
        """Send evaluation prompt + output summary to Claude for grading.

        Builds a combined prompt from the evaluation instructions and the
        collected output summary, then calls ``claude --print -p`` and parses
        the JSON response.

        Args:
            output: Collected scenario output to evaluate.
            prompt: Evaluation instructions/questions for the AI judge.
            timeout: Override instance timeout for this call.

        Returns:
            GradeResult with the AI judge's assessment. On subprocess failure
            or parse errors, returns a failed GradeResult with the error detail.
        """
        collector = OutputCollector()
        summary_text = collector.summary(output)

        full_prompt = (
            f"You are an AI judge evaluating a security analysis scenario run.\n\n"
            f"## Scenario Output\n{summary_text}\n\n"
            f"## Evaluation Instructions\n{prompt}\n\n"
            f"Respond with ONLY a JSON object with these fields:\n"
            f'- "passed": boolean (did the run meet the criteria?)\n'
            f'- "score": number 0-100 (quality score)\n'
            f'- "reason": string (brief explanation)\n'
        )

        effective_timeout = timeout if timeout is not None else self.timeout

        try:
            result = subprocess.run(
                [
                    "claude",
                    "--print",
                    "-p",
                    full_prompt,
                    "--output-format",
                    "json",
                    "--model",
                    self.model,
                ],
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
        except FileNotFoundError:
            return GradeResult(
                passed=False,
                score=0,
                reason="claude CLI not found -- install Claude Code",
                grader_type="model",
            )
        except subprocess.TimeoutExpired:
            return GradeResult(
                passed=False,
                score=0,
                reason=f"Model grading timed out after {effective_timeout}s",
                grader_type="model",
            )

        if result.returncode != 0:
            return GradeResult(
                passed=False,
                score=0,
                reason=f"claude CLI exited with code {result.returncode}: {result.stderr[:200]}",
                grader_type="model",
            )

        return self._parse_response(result.stdout)

    def _parse_response(self, raw_output: str) -> GradeResult:
        """Parse Claude CLI JSON response into a GradeResult.

        Handles both direct JSON and JSON embedded in the response text.
        """
        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            # Try to extract JSON from response text
            import re

            match = re.search(r"\{[^}]+\}", raw_output, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    return GradeResult(
                        passed=False,
                        score=0,
                        reason=f"Could not parse model response as JSON: {raw_output[:200]}",
                        grader_type="model",
                    )
            else:
                return GradeResult(
                    passed=False,
                    score=0,
                    reason=f"No JSON found in model response: {raw_output[:200]}",
                    grader_type="model",
                )

        # Handle wrapped response (--output-format json wraps in {"result": "..."})
        if "result" in data and isinstance(data["result"], str):
            try:
                inner = json.loads(data["result"])
                data = inner
            except (json.JSONDecodeError, TypeError):
                pass

        passed = data.get("passed", False)
        score_raw = data.get("score", 0)
        # Keep score as 0-100 integer (LLM is prompted for 0-100)
        score = int(score_raw) if isinstance(score_raw, (int, float)) else 0
        reason = data.get("reason", "No reason provided")

        return GradeResult(
            passed=bool(passed),
            score=max(0, min(100, score)),
            reason=str(reason),
            grader_type="model",
        )
