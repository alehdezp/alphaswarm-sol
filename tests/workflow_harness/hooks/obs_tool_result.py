#!/usr/bin/env python3
"""Observation hook: PostToolUse — captures tool results.

Event: PostToolUse
Captures: result snippet, duration
Output: JSONL to .vrs/observations/{session_id}.jsonl
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3]))

from tests.workflow_harness.lib.observation_writer import write_observation


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    session_id = input_data.get("session_id", "unknown")
    tool_name = input_data.get("tool_name", "")
    tool_output = input_data.get("tool_output", "")

    write_observation(
        session_id=session_id,
        event_type="tool_result",
        hook_name="obs_tool_result.py",
        data={
            "tool_name": tool_name,
            "result_preview": str(tool_output)[:500],
            "result_length": len(str(tool_output)),
        },
    )


if __name__ == "__main__":
    main()
