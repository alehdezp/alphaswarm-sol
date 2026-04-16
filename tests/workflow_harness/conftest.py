"""pytest fixtures for the workflow harness.

Provides workspace management and scenario execution fixtures.
The controller bridge (Phase 3.1b-02) is not yet available,
so the run_scenario fixture is a placeholder that will be wired
once the Python bridge to the controller REST API exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .lib.controller_events import EventStream
from .lib.transcript_parser import TranscriptParser
from .lib.workspace import WorkspaceManager


EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples" / "testing"


@pytest.fixture
def workspace_manager() -> WorkspaceManager:
    """WorkspaceManager rooted at examples/testing/."""
    return WorkspaceManager(base_dir=EXAMPLES_DIR)


@pytest.fixture
def event_stream_factory():
    """Factory fixture: create an EventStream from a list of raw event dicts."""
    def _make(events: list[dict]) -> EventStream:
        return EventStream(events)
    return _make


@pytest.fixture
def transcript_parser_factory(tmp_path: Path):
    """Factory fixture: create a TranscriptParser from JSONL content lines."""
    def _make(jsonl_lines: list[dict]) -> TranscriptParser:
        jsonl_file = tmp_path / "transcript.jsonl"
        with open(jsonl_file, "w") as f:
            for record in jsonl_lines:
                f.write(json.dumps(record) + "\n")
        return TranscriptParser(jsonl_file)

    import json
    return _make
