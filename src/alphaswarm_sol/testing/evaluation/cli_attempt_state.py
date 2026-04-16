"""CLIAttemptState: Forensic detection of agent CLI usage from JSONL transcripts.

Provides post-session verification of whether an evaluation agent used the
alphaswarm CLI (`uv run alphaswarm query/build-kg`) or bypassed it via Python
imports (FM-3 failure mode from Plan 12 Batch 1).

This module is the DETECTION layer (forensic, post-session). Plan 01's
delegate_guard.py is the PREVENTION layer (runtime). Both are needed for
defense-in-depth.

Uses TranscriptParser from tests.workflow_harness.lib.transcript_parser as the
primary parsing mechanism (Decision D-2).

DC-2 enforcement: No imports from alphaswarm_sol.kg or alphaswarm_sol.vulndocs.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal


class CLIAttemptState(str, Enum):
    """Distinguishes 4 agent CLI usage behaviors from JSONL transcripts.

    Used by check 13 in agent_execution_validator.py for forensic detection.
    Maps to severity levels via cli_attempt_severity().
    """

    ATTEMPTED_SUCCESS = "attempted_success"
    """Agent called alphaswarm CLI and at least one query returned results."""

    ATTEMPTED_FAILED = "attempted_failed"
    """Agent called alphaswarm CLI but all queries failed or returned empty."""

    NOT_ATTEMPTED = "not_attempted"
    """No alphaswarm CLI calls found in transcript. Likely used Python imports (FM-3)."""

    TRANSCRIPT_UNAVAILABLE = "transcript_unavailable"
    """JSONL transcript not found, empty, or unreadable."""


def compute_cli_attempt_state(transcript_path: Path | None) -> CLIAttemptState:
    """Determine CLI usage state by parsing JSONL transcript content.

    This function MUST parse the actual JSONL content via TranscriptParser to
    determine whether alphaswarm CLI commands were executed. File existence
    alone is not sufficient -- an agent can have a transcript full of Python
    import commands without any CLI usage.

    Args:
        transcript_path: Path to the agent's JSONL transcript file, or None.

    Returns:
        CLIAttemptState enum value based on transcript content analysis.
    """
    # Handle missing/None path
    if transcript_path is None:
        return CLIAttemptState.TRANSCRIPT_UNAVAILABLE

    if not transcript_path.exists():
        return CLIAttemptState.TRANSCRIPT_UNAVAILABLE

    # Handle empty file (0 bytes) -- edge case from RESEARCH.md
    if transcript_path.stat().st_size == 0:
        return CLIAttemptState.TRANSCRIPT_UNAVAILABLE

    # Parse transcript using TranscriptParser (D-2: primary parsing mechanism)
    from tests.workflow_harness.lib.transcript_parser import TranscriptParser

    try:
        parser = TranscriptParser(transcript_path)
    except Exception:
        return CLIAttemptState.TRANSCRIPT_UNAVAILABLE

    # Check for BSKG queries (alphaswarm CLI commands)
    bskg_queries = parser.get_bskg_queries()

    if not bskg_queries:
        # No alphaswarm CLI calls found -- agent never tried CLI
        return CLIAttemptState.NOT_ATTEMPTED

    # Check if any query returned results (non-empty result_snippet)
    # Mixed results edge case: if SOME succeed and SOME fail, return SUCCESS
    for query in bskg_queries:
        if query.result_snippet and query.result_snippet.strip():
            # Check it's not just an error message
            lower_result = query.result_snippet.lower()
            if not _is_error_result(lower_result):
                return CLIAttemptState.ATTEMPTED_SUCCESS

    # All queries failed or returned empty/error
    return CLIAttemptState.ATTEMPTED_FAILED


def cli_attempt_severity(state: CLIAttemptState) -> Literal["critical", "warning", "info"]:
    """Map CLIAttemptState to integrity violation severity.

    Severity rationale:
    - NOT_ATTEMPTED (critical): Agent chose to bypass CLI entirely (FM-3).
      This is an agent behavior problem requiring investigation.
    - ATTEMPTED_FAILED (warning): Agent tried CLI but it's broken (FM-1).
      Infrastructure issue, not agent evasion.
    - TRANSCRIPT_UNAVAILABLE (warning): Graceful degradation -- we can't
      verify, but this is an infrastructure gap, not evasion.
    - ATTEMPTED_SUCCESS (info): No violation -- agent used CLI correctly.
    """
    _severity_map: dict[CLIAttemptState, Literal["critical", "warning", "info"]] = {
        CLIAttemptState.NOT_ATTEMPTED: "critical",
        CLIAttemptState.ATTEMPTED_FAILED: "warning",
        CLIAttemptState.TRANSCRIPT_UNAVAILABLE: "warning",
        CLIAttemptState.ATTEMPTED_SUCCESS: "info",
    }
    return _severity_map[state]


def _is_error_result(lower_result: str) -> bool:
    """Heuristic check if a query result indicates an error rather than data.

    Args:
        lower_result: Lowercased result string.

    Returns:
        True if the result looks like an error message.
    """
    error_indicators = [
        "error:",
        "traceback",
        "exception",
        "command not found",
        "no such file",
        "permission denied",
        "usage:",  # help text instead of results
    ]
    # Short results that are just error text
    if len(lower_result) < 50:
        return any(indicator in lower_result for indicator in error_indicators)

    # Longer results: check if the first line is an error
    first_line = lower_result.split("\n")[0].strip()
    return any(indicator in first_line for indicator in error_indicators)
