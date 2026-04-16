#!/usr/bin/env python3
"""Observation hook: PreToolUse — captures tool invocations.

Event: PreToolUse
Captures: tool name, args, timestamp
Output: JSONL to .vrs/observations/{session_id}.jsonl
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parents[3]))

from tests.workflow_harness.lib.observation_writer import write_observation


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    session_id = input_data.get("session_id", "unknown")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    write_observation(
        session_id=session_id,
        event_type="tool_use",
        hook_name="obs_tool_use.py",
        data={
            "tool_name": tool_name,
            "tool_input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else [],
            "tool_input_preview": str(tool_input)[:500],
        },
    )


if __name__ == "__main__":
    main()
