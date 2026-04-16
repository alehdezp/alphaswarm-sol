#!/usr/bin/env python3
"""Observation hook: SubagentStop — captures agent exit info.

Event: SubagentStop
Captures: agent ID, transcript path, exit info
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

    write_observation(
        session_id=session_id,
        event_type="agent_stop",
        hook_name="obs_agent_stop.py",
        data={
            "agent_id": input_data.get("agent_id", ""),
            "agent_transcript_path": input_data.get("agent_transcript_path", ""),
            "stop_hook_active": input_data.get("stop_hook_active", False),
        },
    )


if __name__ == "__main__":
    main()
