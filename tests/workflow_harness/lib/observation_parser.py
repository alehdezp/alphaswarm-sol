"""Thin adapter over TranscriptParser for ObservationSummary extraction.

Delegates all data extraction to TranscriptParser.to_observation_summary().
Adds session_id filtering (O(1) file lookup) and data quality tracking.

CONTRACT_VERSION: 03.2
CONSUMERS: [3.1c-04 (GVS), 3.1c-07 (Evaluator), 3.1c-08 (Runner)]
"""

from __future__ import annotations

import os
import time
import warnings
from pathlib import Path

from alphaswarm_sol.testing.evaluation.models import ObservationDataQuality
from tests.workflow_harness.lib.transcript_parser import (
    ObservationSummary,
    TranscriptParser,
)

# Re-export for backwards compatibility — consumers import from here
__all__ = ["ObservationParser", "ObservationSummary"]


class ObservationParser:
    """Parse session JSONL into ObservationSummary via TranscriptParser.

    Thin adapter (~40 LOC). All extraction logic lives in TranscriptParser.
    This class handles: file selection, session filtering, data quality,
    staleness guard, and the ObservationSummary interface.

    Usage:
        parser = ObservationParser(obs_dir, session_id="abc123")
        summary = parser.parse()
    """

    def __init__(
        self,
        obs_dir: Path,
        session_id: str | None = None,
        max_staleness_seconds: int = 3600,
    ):
        self._obs_dir = obs_dir
        self._session_id = session_id
        self._max_staleness_seconds = max_staleness_seconds
        if session_id is None:
            warnings.warn(
                "ObservationParser instantiated without session_id; "
                "will read all JSONL files (O(n), not session-safe)",
                stacklevel=2,
            )

    def _resolve_files(self) -> list[Path]:
        """Resolve JSONL files to parse. O(1) when session_id is set."""
        if not self._obs_dir.exists():
            return []
        if self._session_id is not None:
            target = self._obs_dir / f"{self._session_id}.jsonl"
            return [target] if target.exists() else []
        return sorted(self._obs_dir.glob("*.jsonl"))

    def parse(self) -> ObservationSummary:
        """Parse session transcript(s) into ObservationSummary.

        Delegates extraction to TranscriptParser.to_observation_summary().
        Returns ObservationSummary with data_quality populated.
        """
        files = self._resolve_files()
        quality = ObservationDataQuality()
        now = time.time()

        # Staleness guard: skip files older than max_staleness_seconds
        valid_files: list[Path] = []
        for f in files:
            try:
                mtime = os.path.getmtime(f)
                if (now - mtime) > self._max_staleness_seconds:
                    quality.stale_files_excluded += 1
                    warnings.warn(
                        f"Skipping stale file {f.name} "
                        f"(age={int(now - mtime)}s > {self._max_staleness_seconds}s)",
                        stacklevel=2,
                    )
                    continue
            except OSError:
                quality.serialize_errors += 1
                continue
            valid_files.append(f)

        if not valid_files:
            quality.degraded = len(files) > 0 and len(valid_files) == 0
            summary = ObservationSummary()
            summary.data_quality = quality
            return summary

        # Delegate to TranscriptParser for each file, merge results
        merged = ObservationSummary()
        for f in valid_files:
            tp = TranscriptParser(f)
            obs = tp.to_observation_summary()

            # Cross-session contamination check (glob path only):
            # When session_id was used for O(1) lookup, the file is already correct.
            # When globbing, track if multiple sessions appear.
            if not self._session_id and merged.session_id and obs.session_id:
                if obs.session_id != merged.session_id:
                    quality.cross_session_records_dropped += 1

            # Merge into combined summary
            merged.tool_counts = {
                k: merged.tool_counts.get(k, 0) + v
                for k, v in obs.tool_counts.items()
            }
            merged.tool_sequences.extend(obs.tool_sequences)
            merged.bskg_query_events.extend(obs.bskg_query_events)
            merged.tool_failures.extend(obs.tool_failures)
            merged.agent_lifecycle_events.extend(obs.agent_lifecycle_events)
            merged.total_tool_calls += obs.total_tool_calls
            if obs.session_id and not merged.session_id:
                merged.session_id = obs.session_id

        merged.data_quality = quality
        return merged

    def get_tool_timeline(self) -> list:
        """Get chronological tool sequence entries."""
        return self.parse().tool_sequences

    def get_bskg_observations(self) -> list:
        """Get all BSKG query events."""
        return self.parse().bskg_query_events
