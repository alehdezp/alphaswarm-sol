#!/usr/bin/env python3
"""Observation hook: SessionStart — captures session metadata.

Event: SessionStart (via Stop event with session metadata)
Captures: session ID, model, working directory, source, agent_type
Output: JSONL to .vrs/observations/{session_id}.jsonl

P13-IMP-05: Added source and agent_type fields for evaluation pipeline.
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

    # P13-IMP-05: source and agent_type fields
    source = input_data.get("source", "unknown")
    agent_type = input_data.get("agent_type", "main")

    write_observation(
        session_id=session_id,
        event_type="session_start",
        hook_name="obs_session_start.py",
        data={
            "session_id": session_id,
            "cwd": input_data.get("cwd", ""),
            "model": input_data.get("model", ""),
            "source": source,
            "agent_type": agent_type,
        },
    )


if __name__ == "__main__":
    main()
