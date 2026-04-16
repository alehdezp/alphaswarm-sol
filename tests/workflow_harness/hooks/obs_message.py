#!/usr/bin/env python3
"""Observation hook: PostToolUse (filtered) — captures inter-agent messages.

Event: PostToolUse (filtered: SendMessage tool)
Captures: sender, recipient, content preview, message type
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

    tool_name = input_data.get("tool_name", "")
    if tool_name != "SendMessage":
        sys.exit(0)

    session_id = input_data.get("session_id", "unknown")
    tool_input = input_data.get("tool_input", {})

    if not isinstance(tool_input, dict):
        sys.exit(0)

    write_observation(
        session_id=session_id,
        event_type="message",
        hook_name="obs_message.py",
        data={
            "recipient": tool_input.get("recipient", ""),
            "message_type": tool_input.get("type", "message"),
            "content_preview": str(tool_input.get("content", ""))[:500],
            "summary": tool_input.get("summary", ""),
        },
    )


if __name__ == "__main__":
    main()
