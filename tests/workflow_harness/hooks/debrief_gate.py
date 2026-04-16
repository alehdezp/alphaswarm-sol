#!/usr/bin/env python3
"""Debrief gate hook: TeammateIdle -- blocks until debrief marker exists.

Event: TeammateIdle (type: "command")
Behavior: Exit 2 to block agent shutdown until debrief_done marker file exists.
Polls for the marker with configurable timeout.

IMPORTANT: Must use type: "command" hooks only (BUG #20221: type: "prompt" is broken).
IMPORTANT: Must check stop_hook_active flag to prevent infinite blocking loops.

Exit codes:
  0 — Allow (debrief marker found, or stop_hook_active)
  2 — Block (timeout exhausted, marker not found)
"""

import json
import os
import sys
import time
from pathlib import Path

# Configurable via environment (total timeout ~60s default)
DEFAULT_TIMEOUT_ITERATIONS = 30
DEFAULT_POLL_INTERVAL = 2.0  # seconds


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # MANDATORY: Prevent infinite loops (must be FIRST check)
    if input_data.get("stop_hook_active", False):
        sys.exit(0)  # Don't block during stop sequence

    teammate_name = input_data.get("teammate_name", "")
    if not teammate_name:
        # No teammate to gate — allow
        sys.exit(0)

    # Check for debrief marker file
    marker_path = Path(os.getcwd()) / ".vrs" / "debrief" / f"{teammate_name}.done"

    # Read configurable timeout from env
    timeout_iterations = int(
        os.environ.get("DEBRIEF_TIMEOUT_ITERATIONS", str(DEFAULT_TIMEOUT_ITERATIONS))
    )
    poll_interval = float(
        os.environ.get("DEBRIEF_POLL_INTERVAL", str(DEFAULT_POLL_INTERVAL))
    )

    # Timeout polling loop
    for _ in range(timeout_iterations):
        if marker_path.exists():
            sys.exit(0)  # Debrief complete — allow
        time.sleep(poll_interval)

    # Timeout exhausted — block (exit 2 tells Claude Code to wait)
    sys.exit(2)


if __name__ == "__main__":
    main()
