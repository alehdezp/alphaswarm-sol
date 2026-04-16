#!/usr/bin/env python3
"""Observation hook: PreCompact — snapshot before transcript compaction.

Event: PreCompact (auto trigger)
Behavior:
  - trigger == "auto": read transcript, extract BSKG node IDs, write
    precompact_snapshot observation and .compacted marker
  - trigger == "manual": exit 0, no marker

CONSTRAINTS (P11-IMP-01, P11-ADV-1-02, P11-CSC-02):
  - MUST use stdlib imports ONLY (no TranscriptParser, no project imports)
  - MUST be synchronous, target < 2s completion
  - Does NOT compute ObservationSummary fields (that is TranscriptParser's job)
"""

import json
import os
import re
import sys
from pathlib import Path

_BSKG_NODE_RE = re.compile(r"[FCE]-\w+-\w+")


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    trigger = input_data.get("trigger", "manual")

    # Manual trigger: exit cleanly, no marker
    if trigger != "auto":
        sys.exit(0)

    session_id = input_data.get("session_id", "unknown")
    transcript_path = input_data.get("transcript_path", "")

    # Extract BSKG node IDs from transcript using inline stdlib JSONL parsing
    node_ids: list[str] = []
    if transcript_path and os.path.isfile(transcript_path):
        try:
            with open(transcript_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # Extract node IDs from tool results in user records
                    if record.get("type") != "user":
                        continue
                    msg = record.get("message", {})
                    if not isinstance(msg, dict):
                        continue
                    content = msg.get("content", [])
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            result_text = str(block.get("content", ""))
                            found = _BSKG_NODE_RE.findall(result_text)
                            node_ids.extend(found)
        except OSError:
            pass

    unique_nodes = sorted(set(node_ids))

    # Write precompact_snapshot observation event
    obs_dir = Path(os.getcwd()) / ".vrs" / "observations"
    obs_dir.mkdir(parents=True, exist_ok=True)
    obs_path = obs_dir / f"{session_id}.jsonl"

    from datetime import datetime, timezone

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "event_type": "precompact_snapshot",
        "hook_name": "obs_precompact.py",
        "data": {
            "bskg_node_ids": unique_nodes,
            "node_count": len(unique_nodes),
        },
    }

    try:
        with open(obs_path, "a") as f:
            f.write(json.dumps(snapshot) + "\n")
    except OSError:
        pass

    # Write .compacted marker
    marker_dir = Path(os.getcwd()) / ".vrs" / "markers"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker_path = marker_dir / f"{session_id}.compacted"
    try:
        marker_path.write_text(session_id)
    except OSError:
        pass


if __name__ == "__main__":
    main()
