#!/usr/bin/env python3
"""Debrief hook: TaskCompleted -- alternative blocking point for debrief.

Event: TaskCompleted (type: "command")
Behavior: Records task completion observation and optionally blocks for debrief
using the same marker-file mechanism as debrief_gate.py.

IMPORTANT: Must use type: "command" hooks only (BUG #20221).
IMPORTANT: Must check stop_hook_active flag.

Exit codes:
  0 — Allow (marker found, stop_hook_active, or debrief not required)
  2 — Block (timeout exhausted when debrief required)
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3]))

from tests.workflow_harness.lib.observation_writer import write_observation

# Configurable via environment
DEFAULT_TIMEOUT_ITERATIONS = 15  # Shorter than debrief_gate (secondary hook)
DEFAULT_POLL_INTERVAL = 2.0


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # MANDATORY: Prevent infinite loops (must be FIRST check)
    if input_data.get("stop_hook_active", False):
        sys.exit(0)

    session_id = input_data.get("session_id", "unknown")

    # Record task completion as observation
    write_observation(
        session_id=session_id,
        event_type="task_completed",
        hook_name="debrief_task_complete.py",
        data={
            "task_id": input_data.get("task_id", ""),
            "task_subject": input_data.get("task_subject", ""),
        },
    )

    # Only block if debrief is required for this session
    # (signaled by DEBRIEF_REQUIRED env var or session marker)
    debrief_required = os.environ.get("VRS_DEBRIEF_REQUIRED", "").lower() == "true"
    if not debrief_required:
        sys.exit(0)

    teammate_name = input_data.get("teammate_name", "")
    if not teammate_name:
        sys.exit(0)

    marker_path = Path(os.getcwd()) / ".vrs" / "debrief" / f"{teammate_name}.done"

    timeout_iterations = int(
        os.environ.get("DEBRIEF_TIMEOUT_ITERATIONS", str(DEFAULT_TIMEOUT_ITERATIONS))
    )
    poll_interval = float(
        os.environ.get("DEBRIEF_POLL_INTERVAL", str(DEFAULT_POLL_INTERVAL))
    )

    for _ in range(timeout_iterations):
        if marker_path.exists():
            sys.exit(0)
        time.sleep(poll_interval)

    sys.exit(2)


if __name__ == "__main__":
    main()
