#!/usr/bin/env python3
"""Hook: log session/transcript paths for post-hoc analysis.

Installed into each test workspace's .claude/hooks/ directory.
Appends session metadata to .vrs/testing/session.json on SubagentStop and Stop events.

Input (stdin): JSON with fields like session_id, agent_id, agent_transcript_path
Output: None (writes to .vrs/testing/session.json)
"""

import json
import os
import sys
from datetime import datetime


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    out_dir = os.path.join(os.getcwd(), ".vrs", "testing")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "session.json")

    # Read existing or initialize
    if os.path.exists(out_path):
        try:
            with open(out_path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {"events": []}
    else:
        existing = {"events": []}

    if "events" not in existing:
        existing["events"] = []

    existing["events"].append({
        "timestamp": datetime.now().isoformat(),
        "event_type": input_data.get("hook_event_name", "unknown"),
        "agent_id": input_data.get("agent_id"),
        "agent_transcript_path": input_data.get("agent_transcript_path"),
        "session_id": input_data.get("session_id"),
        "transcript_path": input_data.get("transcript_path"),
        "stop_hook_active": input_data.get("stop_hook_active"),
    })

    with open(out_path, "w") as f:
        json.dump(existing, f, indent=2)


if __name__ == "__main__":
    main()
