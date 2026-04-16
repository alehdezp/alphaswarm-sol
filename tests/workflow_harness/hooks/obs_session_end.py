#!/usr/bin/env python3
"""Observation hook: SessionEnd — writes session_ended marker.

Event: Stop
Behavior: Write {session_id}.session_ended marker file.
Observation-only hook — cannot block (exit 0 always).

P11-IMP-01: Lightweight session lifecycle tracking.
"""

import json
import os
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

    # Write observation record
    write_observation(
        session_id=session_id,
        event_type="session_end",
        hook_name="obs_session_end.py",
        data={
            "session_id": session_id,
        },
    )

    # Write session_ended marker
    marker_dir = Path(os.getcwd()) / ".vrs" / "markers"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker_path = marker_dir / f"{session_id}.session_ended"
    try:
        marker_path.write_text(session_id)
    except OSError:
        pass


if __name__ == "__main__":
    main()
