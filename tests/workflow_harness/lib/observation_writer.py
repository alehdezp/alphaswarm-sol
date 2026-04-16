"""Thread-safe JSONL observation writer.

Writes ObservationRecord-compatible JSONL lines to
.vrs/observations/{session_id}.jsonl. Used by observation hooks
to record structured events during evaluation runs.

CONTRACT_VERSION: 02.1
CONSUMERS: [3.1c-03 (ObservationParser)]
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Thread lock for safe concurrent writes from multiple hooks
_write_lock = threading.Lock()


def get_observations_dir(base_dir: str | Path | None = None) -> Path:
    """Get the observations output directory.

    Args:
        base_dir: Override base directory. Defaults to CWD.

    Returns:
        Path to .vrs/observations/ directory (created if needed).
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    obs_dir = base / ".vrs" / "observations"
    obs_dir.mkdir(parents=True, exist_ok=True)
    return obs_dir


def write_observation(
    session_id: str,
    event_type: str,
    hook_name: str,
    data: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
    timestamp: str | None = None,
) -> Path:
    """Write a single observation record as a JSONL line.

    Thread-safe: uses a lock to prevent interleaved writes from
    concurrent hook processes.

    Args:
        session_id: Claude Code session identifier.
        event_type: Hook event type (e.g., 'tool_use', 'bskg_query').
        hook_name: Name of the hook script producing this record.
        data: Event-specific payload.
        base_dir: Override base directory. Defaults to CWD.
        timestamp: Override timestamp. Defaults to now (UTC ISO 8601).

    Returns:
        Path to the JSONL file that was written to.
    """
    obs_dir = get_observations_dir(base_dir)
    output_path = obs_dir / f"{session_id}.jsonl"

    record = {
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "event_type": event_type,
        "hook_name": hook_name,
        "data": data or {},
    }

    line = json.dumps(record, separators=(",", ":")) + "\n"

    with _write_lock:
        with open(output_path, "a") as f:
            f.write(line)

    return output_path


def write_observation_from_stdin(
    event_type: str,
    hook_name: str,
    extract_data: Any = None,
) -> None:
    """Read hook input from stdin and write an observation record.

    Convenience function for hook scripts. Reads JSON from stdin,
    extracts session_id, and writes a JSONL observation.

    Args:
        event_type: Hook event type.
        hook_name: Name of the calling hook script.
        extract_data: Callable(input_data) -> dict to extract
            event-specific data. If None, stores entire input.
    """
    import sys

    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return  # Silently skip malformed input

    session_id = input_data.get("session_id", "unknown")

    if callable(extract_data):
        data = extract_data(input_data)
    else:
        data = input_data

    write_observation(
        session_id=session_id,
        event_type=event_type,
        hook_name=hook_name,
        data=data,
    )
