#!/usr/bin/env python3
"""Observation hook: PostToolUse (filtered) — captures BSKG queries.

Event: PostToolUse (filtered: Bash with alphaswarm command)
Captures: BSKG query details (command, query text, results)
Output: JSONL to .vrs/observations/{session_id}.jsonl
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3]))

from tests.workflow_harness.lib.observation_writer import write_observation


def _is_bskg_command(input_data: dict) -> bool:
    """Check if this PostToolUse is a BSKG-related Bash command."""
    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        return False
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    return "alphaswarm" in command


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if not _is_bskg_command(input_data):
        sys.exit(0)  # Not a BSKG command, skip

    session_id = input_data.get("session_id", "unknown")
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    tool_output = input_data.get("tool_output", "")

    write_observation(
        session_id=session_id,
        event_type="bskg_query",
        hook_name="obs_bskg_query.py",
        data={
            "command": command,
            "result_preview": str(tool_output)[:1000],
            "result_length": len(str(tool_output)),
        },
    )


if __name__ == "__main__":
    main()
