"""Deep JSONL transcript extractor for SessionRecorder.

The "structure" step in the capture → structure → search pipeline
(see session_recorder.py for the full architecture note).

Wraps the existing TranscriptParser from tests/workflow_harness/lib/ and
extracts structured records suitable for SessionRecorder.record_session():
- Tool call records with input/output
- CLI attempts (build-kg, query) with exit codes
- Task actions (TaskCreate/TaskUpdate) with subjects
- Skill invocations
- Violations detected via pattern matching

This module reads JSONL once, classifies every event, and produces a dict
ready for SessionRecorder.record_session(parsed_data=...).

DC-2 enforcement: No imports from kg or vulndocs subpackages.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


# Violation detection patterns
_PYTHON_IMPORT_PATTERNS = [
    re.compile(r"python\s+-c\s+.*import", re.IGNORECASE),
    re.compile(r"python3?\s+-c\s+.*from\s+\w+", re.IGNORECASE),
    re.compile(r"uv\s+run\s+python", re.IGNORECASE),
]

_CONTEXT_READ_PATHS = [
    ".claude/CLAUDE.md",
    "CLAUDE.md",
    ".planning/",
    "docs/",
    "vulndocs/",
    ".claude/settings.json",
]

_FABRICATION_PATTERNS = [
    re.compile(r"EVD-[0-9a-f]{6,10}\b"),  # Fabricated evidence refs
    re.compile(r"function:[0-9a-f]{10,14}\b"),  # Fabricated node IDs
]

# Tool output excerpt limits
_TOOL_OUTPUT_LIMIT = 500
_CLI_OUTPUT_LIMIT = 1000


class TranscriptSessionExtractor:
    """Extract structured session data from a JSONL transcript.

    Usage:
        extractor = TranscriptSessionExtractor(Path("session.jsonl"))
        parsed_data = extractor.extract()
        session_id = recorder.record_session(path, metadata, parsed_data=parsed_data)
    """

    def __init__(self, jsonl_path: Path) -> None:
        self._path = jsonl_path
        self._records: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load and parse the JSONL file."""
        if not self._path.exists():
            return
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    def extract(self) -> dict[str, Any]:
        """Extract all structured records from the transcript.

        Returns:
            Dict with keys: tool_calls, cli_attempts, task_actions,
            skill_usage, violations, start_time, end_time, duration_seconds.
        """
        tool_calls: list[dict[str, Any]] = []
        cli_attempts: list[dict[str, Any]] = []
        task_actions: list[dict[str, Any]] = []
        skill_usage: list[dict[str, Any]] = []
        violations: list[dict[str, Any]] = []

        # Build tool_use_id -> result mapping for output excerpts
        result_map = self._build_result_map()

        # Extract timestamps for session duration
        timestamps = self._extract_timestamps()
        start_time = timestamps[0] if timestamps else ""
        end_time = timestamps[-1] if timestamps else ""
        duration = self._compute_duration(start_time, end_time)

        seq_num = 0
        record_index = 0
        for record in self._records:
            if record.get("type") != "assistant":
                continue
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue

            ts = record.get("timestamp") or message.get("timestamp")
            ts_str = str(ts) if ts and isinstance(ts, str) else ""

            for block in content:
                if not isinstance(block, dict):
                    continue

                # Check assistant text blocks for fabrication
                if block.get("type") == "text":
                    text = block.get("text", "")
                    for v in self._check_assistant_text_fabrication(
                        text, record_index
                    ):
                        v["timestamp"] = ts_str
                        violations.append(v)
                    continue

                if block.get("type") != "tool_use":
                    continue

                tool_name = block.get("name", "unknown")
                tool_input = block.get("input", {})
                tool_id = block.get("id", "")
                input_json = json.dumps(tool_input)[:2000]

                # Get result excerpt
                result_text = result_map.get(tool_id, "")
                is_error = result_map.get(f"{tool_id}:is_error", False)

                # Record tool call
                tool_calls.append({
                    "sequence_num": seq_num,
                    "tool_name": tool_name,
                    "tool_input": input_json,
                    "tool_output_excerpt": result_text[:_TOOL_OUTPUT_LIMIT],
                    "timestamp": ts_str,
                    "blocked": is_error and "blocked" in result_text.lower(),
                })

                # Classify specific tool types
                if tool_name == "Bash":
                    cli_record = self._extract_cli_attempt(
                        tool_input, result_text, is_error, ts_str
                    )
                    if cli_record:
                        cli_attempts.append(cli_record)

                    # Check for python import violations
                    for v in self._check_python_import(tool_input, seq_num):
                        v["timestamp"] = ts_str
                        violations.append(v)

                elif tool_name in ("TaskCreate", "TaskUpdate", "TaskList", "TaskGet"):
                    ta = self._extract_task_action(tool_name, tool_input, ts_str)
                    if ta:
                        task_actions.append(ta)

                elif tool_name == "Skill":
                    su = self._extract_skill_usage(tool_input, result_text, is_error)
                    if su:
                        skill_usage.append(su)

                elif tool_name == "Read":
                    # Check for context read violations
                    for v in self._check_context_read(tool_input, seq_num):
                        v["timestamp"] = ts_str
                        violations.append(v)

                # Check for fabrication in tool inputs and outputs
                for v in self._check_fabrication(
                    result_text, tool_name, seq_num, tool_input_json=input_json
                ):
                    v["timestamp"] = ts_str
                    violations.append(v)

                seq_num += 1
            record_index += 1

        return {
            "tool_calls": tool_calls,
            "cli_attempts": cli_attempts,
            "task_actions": task_actions,
            "skill_usage": skill_usage,
            "violations": violations,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": duration,
        }

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _build_result_map(self) -> dict[str, Any]:
        """Build a mapping of tool_use_id -> result text."""
        result_map: dict[str, Any] = {}
        for record in self._records:
            if record.get("type") != "user":
                continue
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tool_id = block.get("tool_use_id", "")
                if not tool_id:
                    continue

                result_content = block.get("content", "")
                if isinstance(result_content, list):
                    texts = []
                    for part in result_content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            texts.append(part.get("text", ""))
                    result_content = "\n".join(texts)
                result_map[tool_id] = str(result_content)
                result_map[f"{tool_id}:is_error"] = block.get("is_error", False)
        return result_map

    def _extract_timestamps(self) -> list[str]:
        """Extract all ISO 8601 timestamps from records."""
        timestamps: list[str] = []
        for r in self._records:
            ts = r.get("timestamp") or r.get("message", {}).get("timestamp")
            if ts and isinstance(ts, str):
                timestamps.append(ts)
        return timestamps

    @staticmethod
    def _compute_duration(start: str, end: str) -> float:
        """Compute duration in seconds between two ISO timestamps."""
        if not start or not end:
            return 0.0
        try:
            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
            e = datetime.fromisoformat(end.replace("Z", "+00:00"))
            return max(0.0, (e - s).total_seconds())
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _extract_cli_attempt(
        tool_input: dict[str, Any],
        result_text: str,
        is_error: bool,
        timestamp: str,
    ) -> dict[str, Any] | None:
        """Extract a CLI attempt from a Bash tool call, if it's an alphaswarm command."""
        cmd = tool_input.get("command", "")
        if not cmd or "alphaswarm" not in cmd:
            return None

        # Classify the command
        if "build-kg" in cmd:
            command_type = "build-kg"
        elif "query" in cmd:
            command_type = "query"
        elif "vulndocs" in cmd:
            command_type = "vulndocs"
        elif "tools" in cmd:
            command_type = "tools"
        else:
            command_type = "other"

        # Determine state from result
        if is_error:
            state = "ATTEMPTED_FAILED"
        elif result_text:
            state = "ATTEMPTED_SUCCESS"
        else:
            state = "ATTEMPTED_SUCCESS"  # No output but no error

        return {
            "command": f"{command_type}: {cmd[:200]}",
            "full_bash_input": cmd[:2000],
            "exit_code": 1 if is_error else 0,
            "stdout_excerpt": result_text[:_CLI_OUTPUT_LIMIT],
            "state": state,
            "timestamp": timestamp,
        }

    @staticmethod
    def _extract_task_action(
        tool_name: str, tool_input: dict[str, Any], timestamp: str
    ) -> dict[str, Any] | None:
        """Extract a task action from TaskCreate/TaskUpdate/etc."""
        action_map = {
            "TaskCreate": "create",
            "TaskUpdate": "update",
            "TaskList": "list",
            "TaskGet": "get",
        }
        action = action_map.get(tool_name, "unknown")

        subject = tool_input.get("subject", "")
        description = tool_input.get("description", "")
        status = tool_input.get("status", "")

        return {
            "action": action,
            "task_subject": subject,
            "task_description": description[:500],
            "task_status": status,
            "timestamp": timestamp,
        }

    @staticmethod
    def _extract_skill_usage(
        tool_input: dict[str, Any],
        result_text: str,
        is_error: bool,
    ) -> dict[str, Any] | None:
        """Extract skill usage from a Skill tool call."""
        skill_name = tool_input.get("skill", "")
        if not skill_name:
            return None

        if is_error:
            invocation_result = "error"
        elif "blocked" in result_text.lower():
            invocation_result = "blocked"
        else:
            invocation_result = "success"

        return {
            "skill_name": skill_name,
            "was_invoked": True,
            "was_available": not (is_error and "not found" in result_text.lower()),
            "invocation_result": invocation_result,
        }

    @staticmethod
    def _check_python_import(
        tool_input: dict[str, Any], seq_num: int
    ) -> list[dict[str, Any]]:
        """Check for python import violations in Bash commands."""
        cmd = tool_input.get("command", "")
        if not cmd:
            return []

        for pattern in _PYTHON_IMPORT_PATTERNS:
            if pattern.search(cmd):
                return [{
                    "violation_type": "python_import",
                    "evidence": f"Tool #{seq_num} Bash: {cmd[:300]}",
                    "severity": "critical",
                }]
        return []

    @staticmethod
    def _check_context_read(
        tool_input: dict[str, Any], seq_num: int
    ) -> list[dict[str, Any]]:
        """Check for context read violations in Read tool calls."""
        file_path = tool_input.get("file_path", "")
        if not file_path:
            return []

        for forbidden_path in _CONTEXT_READ_PATHS:
            if forbidden_path in file_path:
                return [{
                    "violation_type": "context_read",
                    "evidence": f"Tool #{seq_num} Read: {file_path}",
                    "severity": "critical",
                }]
        return []

    @staticmethod
    def _check_fabrication(
        result_text: str,
        tool_name: str,
        seq_num: int,
        tool_input_json: str = "",
    ) -> list[dict[str, Any]]:
        """Check for fabricated identifiers in tool output and input.

        Fabrication means the *agent* invented IDs. These appear in:
        - tool_input (the JSON-serialized input string)
        - tool output (except Bash outputs which come from real CLI)
        """
        violations: list[dict[str, Any]] = []

        # Scan tool input for fabricated IDs (agent-generated)
        if tool_input_json:
            for pattern in _FABRICATION_PATTERNS:
                matches = pattern.findall(tool_input_json)
                if matches:
                    violations.append({
                        "violation_type": "fabrication",
                        "evidence": (
                            f"Tool #{seq_num} {tool_name} input: "
                            f"found {len(matches)} suspect IDs: {matches[:3]}"
                        ),
                        "severity": "warning",
                    })

        # Scan tool output (skip Bash outputs — they come from real CLI)
        if result_text and tool_name != "Bash":
            for pattern in _FABRICATION_PATTERNS:
                matches = pattern.findall(result_text)
                if matches:
                    violations.append({
                        "violation_type": "fabrication",
                        "evidence": (
                            f"Tool #{seq_num} {tool_name} output: "
                            f"found {len(matches)} suspect IDs: {matches[:3]}"
                        ),
                        "severity": "warning",
                    })
        return violations

    @staticmethod
    def _check_assistant_text_fabrication(
        text: str, record_index: int
    ) -> list[dict[str, Any]]:
        """Check for fabricated identifiers in assistant text content blocks."""
        if not text:
            return []
        violations: list[dict[str, Any]] = []
        for pattern in _FABRICATION_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                violations.append({
                    "violation_type": "fabrication",
                    "evidence": (
                        f"Assistant text (record #{record_index}): "
                        f"found {len(matches)} suspect IDs: {matches[:3]}"
                    ),
                    "severity": "warning",
                })
        return violations
