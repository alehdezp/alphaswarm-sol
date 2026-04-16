"""Agent Execution Integrity Validator.

Automatically detects when evaluation agents:
- Fabricate findings instead of running CLI tools
- Run raw Python imports instead of the CLI (`uv run alphaswarm ...`)
- Leak project context despite isolation instructions
- Produce implausible session metadata

This module is the automated regression gate for agent execution quality.
Run AFTER every Agent Teams evaluation session to catch issues before
results pollute baselines.

DC-2 enforcement: No imports from kg or vulndocs subpackages.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- Thresholds (tunable) ---

# Minimum plausible session duration for a single contract analysis.
# Building a BSKG graph + running queries takes at minimum ~10 seconds.
MIN_SESSION_DURATION_SECONDS = 10

# Maximum plausible queries for a single contract analysis.
# Agents should run 2-6 queries per contract, not 50.
MAX_PLAUSIBLE_QUERIES = 20

# Minimum plausible graph nodes for any non-trivial contract.
# Even a minimal contract produces at least 3 nodes (contract + constructor + fallback).
MIN_PLAUSIBLE_NODES = 2

# Knowledge leakage: project-specific terms that a context-isolated agent
# should NOT know. These come from CLAUDE.md, docs/, .planning/, vulndocs/.
#
# NOTE: Pattern IDs (auth-001, oracle-003, etc.) and pattern names
# (statemachine-reentrancy-guard-missing, etc.) are EXCLUDED from this list
# because they appear in normal CLI query output (`uv run alphaswarm query`).
# Agents faithfully reporting CLI output should not be flagged as leaking.
LEAKED_TERMS = [
    # Evidence reference format (project-internal: EVD-{hex})
    r"EVD-[0-9a-f]{8}",
    # BSKG-specific terminology unlikely from CLI output alone
    "Tier A, deterministic",
    "Tier B",
    "Tier C",
    "semantic ops:",
]

# Regex patterns for fabricated-looking identifiers
FABRICATED_NODE_ID_PATTERN = re.compile(r"function:[0-9a-f]{10,14}\b")
FABRICATED_BUILD_HASH_PATTERN = re.compile(r"build.hash.*?:\s*[0-9a-f]{10,14}\b")
FABRICATED_EVIDENCE_REF_PATTERN = re.compile(r"EVD-[0-9a-f]{6,10}\b")


class IntegrityViolation(BaseModel):
    """Single integrity violation detected in an observation file."""

    check_name: str = Field(description="Name of the check that triggered")
    severity: Literal["critical", "warning", "info"] = Field(
        description="critical = session data is unreliable"
    )
    file_path: str = Field(description="Observation file that failed")
    details: str = Field(description="Human-readable explanation")
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting data for the violation",
    )
    failure_mode: str | None = Field(
        default=None,
        description=(
            "Failure mode code: FM-1 (cli_empty_results), "
            "FM-2 (shared_graph_state), FM-3 (python_import_bypass), "
            "FM-4 (context_leakage), FM-OTHER (uncategorized)"
        ),
    )


class IntegrityReport(BaseModel):
    """Full integrity report for a batch of observation files."""

    batch_id: str = Field(description="Batch identifier (e.g., 'batch-1')")
    total_files: int
    files_checked: int
    violations: list[IntegrityViolation] = Field(default_factory=list)
    verdict: Literal["PASS", "FAIL", "DEGRADED"] = Field(
        description="FAIL if any critical violation, DEGRADED if warnings only"
    )
    summary: str = Field(description="Human-readable summary")

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Failure mode classification (maps check_name -> FM code)
# ---------------------------------------------------------------------------

# Failure mode codes (from CONTEXT.md failure mode mapping)
_CHECK_TO_FAILURE_MODE: dict[str, str] = {
    # FM-1: CLI queries return empty results
    "zero_queries": "FM-1",
    "excessive_queries": "FM-1",
    # FM-2: Shared graph state cross-contamination
    "graph_stats_implausible": "FM-2",
    "graph_no_edges": "FM-2",
    "graph_stats_mismatch": "FM-2",
    "identical_timestamps": "FM-2",
    # FM-3: Python import fallback via Bash
    "cli_attempt_state": "FM-3",
    # FM-4: Context leakage via project file access
    "knowledge_leakage": "FM-4",
}


def _classify_failure_mode(check_name: str) -> str:
    """Map a check name to its failure mode code.

    Returns the FM code for known checks, or "FM-OTHER" for checks
    not mapped to the known Batch 1 failure modes.
    """
    return _CHECK_TO_FAILURE_MODE.get(check_name, "FM-OTHER")


def validate_observation_file(
    file_path: Path,
    transcript_path: Path | None = None,
) -> list[IntegrityViolation]:
    """Run all integrity checks on a single observation JSON file.

    Args:
        file_path: Path to the observation JSON file.
        transcript_path: Optional path to the agent's JSONL transcript
            for check 13 (CLI attempt state verification). When provided,
            enables forensic detection of CLI bypass (FM-3).

    Returns list of violations (empty = clean).
    """
    violations: list[IntegrityViolation] = []
    fp = str(file_path)

    try:
        data = json.loads(file_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        violations.append(
            IntegrityViolation(
                check_name="file_readable",
                severity="critical",
                file_path=fp,
                details=f"Cannot read/parse observation file: {e}",
                failure_mode=_classify_failure_mode("file_readable"),
            )
        )
        return violations

    # --- Check 1: Session duration plausibility ---
    violations.extend(_check_session_duration(data, fp))

    # --- Check 2: Graph stats plausibility ---
    violations.extend(_check_graph_stats(data, fp))

    # --- Check 3: Knowledge leakage ---
    violations.extend(_check_knowledge_leakage(data, fp))

    # --- Check 4: Fabricated identifiers ---
    violations.extend(_check_fabricated_identifiers(data, fp))

    # --- Check 5: Finding structure uniformity ---
    violations.extend(_check_finding_uniformity(data, fp))

    # --- Check 6: Query count plausibility ---
    violations.extend(_check_query_count(data, fp))

    # --- Check 13: CLI attempt state (transcript-based forensic) ---
    violations.extend(_check_cli_attempt_state(data, fp, transcript_path))

    return violations


def validate_batch(
    observation_dir: Path,
    batch_id: str = "unknown",
    ground_truth_dir: Path | None = None,
) -> IntegrityReport:
    """Validate all observation files in a directory.

    Args:
        observation_dir: Directory containing cal-*.json files.
        batch_id: Identifier for this batch.
        ground_truth_dir: Optional dir with real build outputs for comparison.

    Returns:
        IntegrityReport with all violations and verdict.
    """
    files = sorted(observation_dir.glob("cal-*.json"))
    all_violations: list[IntegrityViolation] = []

    # Resolve transcript paths from agent_stop observation events
    transcript_map = _resolve_transcript_paths(observation_dir)

    for f in files:
        # Try to find a matching transcript for this observation file
        # The observation filename (e.g., cal-01-attacker.json) maps to agent_id
        obs_stem = f.stem  # e.g., "cal-01-attacker"
        tp = transcript_map.get(obs_stem)
        all_violations.extend(validate_observation_file(f, transcript_path=tp))

    # --- Cross-file checks ---
    all_violations.extend(_check_cross_file_similarity(files))
    all_violations.extend(_check_worktree_isolation(files))

    # --- Optional: ground truth graph comparison ---
    if ground_truth_dir:
        all_violations.extend(
            _check_graph_stats_against_ground_truth(files, ground_truth_dir)
        )

    # Determine verdict
    critical_count = sum(1 for v in all_violations if v.severity == "critical")
    warning_count = sum(1 for v in all_violations if v.severity == "warning")

    if critical_count > 0:
        verdict: Literal["PASS", "FAIL", "DEGRADED"] = "FAIL"
    elif warning_count > 0:
        verdict = "DEGRADED"
    else:
        verdict = "PASS"

    summary_parts = [
        f"Checked {len(files)} observation files.",
        f"Found {critical_count} critical, {warning_count} warning, "
        f"{len(all_violations) - critical_count - warning_count} info violations.",
    ]
    if critical_count > 0:
        summary_parts.append(
            "FAIL: Agent execution integrity compromised. "
            "Results should NOT be used for baselines."
        )

    return IntegrityReport(
        batch_id=batch_id,
        total_files=len(files),
        files_checked=len(files),
        violations=all_violations,
        verdict=verdict,
        summary=" ".join(summary_parts),
    )


# ---------------------------------------------------------------------------
# Individual check implementations
# ---------------------------------------------------------------------------


def _check_session_duration(
    data: dict[str, Any], fp: str
) -> list[IntegrityViolation]:
    """Check that session duration is plausible."""
    violations: list[IntegrityViolation] = []
    metadata = data.get("session_metadata", {})
    started = metadata.get("started_at")
    completed = metadata.get("completed_at")

    if not started or not completed:
        violations.append(
            IntegrityViolation(
                check_name="session_duration_missing",
                severity="warning",
                file_path=fp,
                details="Missing started_at or completed_at in session_metadata",
                failure_mode=_classify_failure_mode("session_duration_missing"),
            )
        )
        return violations

    try:
        start_dt = datetime.fromisoformat(started)
        end_dt = datetime.fromisoformat(completed)
        duration = (end_dt - start_dt).total_seconds()

        if duration < MIN_SESSION_DURATION_SECONDS:
            violations.append(
                IntegrityViolation(
                    check_name="session_too_short",
                    severity="critical",
                    file_path=fp,
                    details=(
                        f"Session duration {duration:.1f}s < minimum "
                        f"{MIN_SESSION_DURATION_SECONDS}s. "
                        "Building BSKG + running queries cannot complete this fast."
                    ),
                    evidence={
                        "started_at": started,
                        "completed_at": completed,
                        "duration_seconds": duration,
                    },
                    failure_mode=_classify_failure_mode("session_too_short"),
                )
            )
    except (ValueError, TypeError) as e:
        violations.append(
            IntegrityViolation(
                check_name="session_timestamp_invalid",
                severity="warning",
                file_path=fp,
                details=f"Cannot parse session timestamps: {e}",
                failure_mode=_classify_failure_mode("session_timestamp_invalid"),
            )
        )

    return violations


def _check_graph_stats(
    data: dict[str, Any], fp: str
) -> list[IntegrityViolation]:
    """Check that graph stats are plausible."""
    violations: list[IntegrityViolation] = []
    stats = data.get("graph_stats", {})
    nodes = stats.get("nodes", 0)
    edges = stats.get("edges", 0)

    if nodes < MIN_PLAUSIBLE_NODES:
        violations.append(
            IntegrityViolation(
                check_name="graph_stats_implausible",
                severity="warning",
                file_path=fp,
                details=f"Graph has {nodes} nodes — below minimum {MIN_PLAUSIBLE_NODES}",
                evidence={"nodes": nodes, "edges": edges},
                failure_mode=_classify_failure_mode("graph_stats_implausible"),
            )
        )

    if nodes > 0 and edges == 0:
        violations.append(
            IntegrityViolation(
                check_name="graph_no_edges",
                severity="warning",
                file_path=fp,
                details=f"Graph has {nodes} nodes but 0 edges — implausible",
                evidence={"nodes": nodes, "edges": edges},
                failure_mode=_classify_failure_mode("graph_no_edges"),
            )
        )

    return violations


def _check_knowledge_leakage(
    data: dict[str, Any], fp: str
) -> list[IntegrityViolation]:
    """Check for project-specific terminology that shouldn't appear in isolated output."""
    violations: list[IntegrityViolation] = []
    # Serialize the entire data to check all fields
    text = json.dumps(data)

    leaked_found: list[str] = []
    for term in LEAKED_TERMS:
        if term.startswith("r") or "[" in term:
            # Regex pattern
            if re.search(term, text):
                leaked_found.append(term)
        elif term in text:
            leaked_found.append(term)

    if leaked_found:
        violations.append(
            IntegrityViolation(
                check_name="knowledge_leakage",
                severity="critical",
                file_path=fp,
                details=(
                    f"Found {len(leaked_found)} project-specific terms that a "
                    "context-isolated agent should NOT know. This indicates the agent "
                    "accessed CLAUDE.md, docs/, or VulnDocs, OR fabricated findings "
                    "using training data about the project."
                ),
                evidence={"leaked_terms": leaked_found},
                failure_mode=_classify_failure_mode("knowledge_leakage"),
            )
        )

    return violations


def _check_fabricated_identifiers(
    data: dict[str, Any], fp: str
) -> list[IntegrityViolation]:
    """Check for identifier patterns that look fabricated."""
    violations: list[IntegrityViolation] = []
    text = json.dumps(data)

    # Check for fabricated node IDs (function:<hex>)
    node_ids = FABRICATED_NODE_ID_PATTERN.findall(text)
    if node_ids:
        violations.append(
            IntegrityViolation(
                check_name="unverified_node_ids",
                severity="info",
                file_path=fp,
                details=(
                    f"Found {len(node_ids)} graph node IDs that need verification "
                    "against actual BSKG build output. If these don't match real "
                    "build output, the agent fabricated them."
                ),
                evidence={"node_ids": node_ids[:5]},
                failure_mode=_classify_failure_mode("unverified_node_ids"),
            )
        )

    # Check for fabricated build hashes
    build_hashes = FABRICATED_BUILD_HASH_PATTERN.findall(text)
    if build_hashes:
        violations.append(
            IntegrityViolation(
                check_name="unverified_build_hash",
                severity="warning",
                file_path=fp,
                details=(
                    f"Found {len(build_hashes)} build hash references. "
                    "These MUST be verified against actual `alphaswarm build-kg` output."
                ),
                evidence={"build_hashes": build_hashes[:3]},
                failure_mode=_classify_failure_mode("unverified_build_hash"),
            )
        )

    # Check for fabricated evidence references
    evidence_refs = FABRICATED_EVIDENCE_REF_PATTERN.findall(text)
    if evidence_refs:
        violations.append(
            IntegrityViolation(
                check_name="unverified_evidence_refs",
                severity="warning",
                file_path=fp,
                details=(
                    f"Found {len(evidence_refs)} evidence reference IDs (EVD-*). "
                    "These use the project's internal format and need verification."
                ),
                evidence={"evidence_refs": evidence_refs[:5]},
                failure_mode=_classify_failure_mode("unverified_evidence_refs"),
            )
        )

    return violations


def _check_finding_uniformity(
    data: dict[str, Any], fp: str
) -> list[IntegrityViolation]:
    """Check if all findings have suspiciously identical structure."""
    violations: list[IntegrityViolation] = []
    findings = data.get("findings", [])

    if len(findings) < 2:
        return violations

    # Check if all confidence values are identical
    confidences = [f.get("confidence") for f in findings if f.get("confidence")]
    if len(confidences) > 1 and len(set(confidences)) == 1:
        violations.append(
            IntegrityViolation(
                check_name="uniform_confidence",
                severity="info",
                file_path=fp,
                details=(
                    f"All {len(confidences)} findings have identical confidence "
                    f"({confidences[0]}). Real tool output produces varied scores."
                ),
                evidence={"confidence": confidences[0], "count": len(confidences)},
                failure_mode=_classify_failure_mode("uniform_confidence"),
            )
        )

    # Check if all severity values are identical
    severities = [f.get("severity") for f in findings if f.get("severity")]
    if len(severities) > 2 and len(set(severities)) == 1:
        violations.append(
            IntegrityViolation(
                check_name="uniform_severity",
                severity="info",
                file_path=fp,
                details=(
                    f"All {len(severities)} findings have identical severity "
                    f"('{severities[0]}'). While possible, this is unusual."
                ),
                failure_mode=_classify_failure_mode("uniform_severity"),
            )
        )

    return violations


def _check_query_count(
    data: dict[str, Any], fp: str
) -> list[IntegrityViolation]:
    """Check that queries_executed is plausible."""
    violations: list[IntegrityViolation] = []
    queries = data.get("queries_executed", 0)

    if queries == 0:
        violations.append(
            IntegrityViolation(
                check_name="zero_queries",
                severity="critical",
                file_path=fp,
                details=(
                    "queries_executed is 0. The agent was supposed to run "
                    "alphaswarm query commands but apparently ran none."
                ),
                failure_mode=_classify_failure_mode("zero_queries"),
            )
        )
    elif queries > MAX_PLAUSIBLE_QUERIES:
        violations.append(
            IntegrityViolation(
                check_name="excessive_queries",
                severity="warning",
                file_path=fp,
                details=f"queries_executed is {queries} — exceeds max plausible {MAX_PLAUSIBLE_QUERIES}",
                failure_mode=_classify_failure_mode("excessive_queries"),
            )
        )

    return violations


# ---------------------------------------------------------------------------
# Check 13: CLI Attempt State (transcript-based forensic detection)
# ---------------------------------------------------------------------------


# Message templates for CLI attempt state violations.
# Imported late to avoid circular imports with cli_attempt_state module.
_CLI_STATE_MESSAGES: dict | None = None


def _get_cli_state_messages() -> dict:
    """Lazy-load CLI state messages to avoid import-time dependency."""
    global _CLI_STATE_MESSAGES
    if _CLI_STATE_MESSAGES is None:
        from alphaswarm_sol.testing.evaluation.cli_attempt_state import CLIAttemptState

        _CLI_STATE_MESSAGES = {
            CLIAttemptState.NOT_ATTEMPTED: (
                "Agent never attempted CLI (alphaswarm query/build-kg). "
                "Likely used Python imports instead (FM-3). "
                "Transcript contains no alphaswarm Bash commands."
            ),
            CLIAttemptState.ATTEMPTED_FAILED: (
                "Agent attempted CLI but all queries failed or returned empty results. "
                "This may indicate CLI bugs (FM-1) rather than agent evasion."
            ),
            CLIAttemptState.TRANSCRIPT_UNAVAILABLE: (
                "JSONL transcript not found for this agent. "
                "Cannot verify CLI usage. Graceful degradation."
            ),
        }
    return _CLI_STATE_MESSAGES


def _check_cli_attempt_state(
    data: dict[str, Any],
    fp: str,
    transcript_path: Path | None,
) -> list[IntegrityViolation]:
    """Check 13: Forensic detection of CLI usage from JSONL transcript.

    Complements Plan 01's runtime delegate_guard prevention with post-session
    forensic verification. Detects FM-3 (Python import fallback) as critical.

    Args:
        data: Parsed observation JSON data (unused, but follows check API).
        fp: File path string for violation reporting.
        transcript_path: Path to the agent's JSONL transcript, or None.

    Returns:
        List of violations. Empty for ATTEMPTED_SUCCESS.
    """
    from alphaswarm_sol.testing.evaluation.cli_attempt_state import (
        CLIAttemptState,
        cli_attempt_severity,
        compute_cli_attempt_state,
    )

    violations: list[IntegrityViolation] = []
    state = compute_cli_attempt_state(transcript_path)

    if state == CLIAttemptState.ATTEMPTED_SUCCESS:
        return violations  # No violation

    # Downgrade TRANSCRIPT_UNAVAILABLE to info when agent ran in a worktree.
    # Worktree-isolated agents (Agent Teams teammates) structurally cannot
    # produce JSONL transcripts, so "unavailable" is expected, not a warning.
    severity = cli_attempt_severity(state)
    if (
        state == CLIAttemptState.TRANSCRIPT_UNAVAILABLE
        and data.get("session_metadata", {}).get("isolation") == "worktree"
    ):
        severity = "info"

    messages = _get_cli_state_messages()
    violations.append(
        IntegrityViolation(
            check_name="cli_attempt_state",
            severity=severity,
            file_path=fp,
            details=messages[state],
            evidence={
                "cli_attempt_state": state.value,
                "transcript_path": str(transcript_path) if transcript_path else None,
            },
            failure_mode=_classify_failure_mode("cli_attempt_state"),
        )
    )
    return violations


def _resolve_transcript_paths(observation_dir: Path) -> dict[str, Path]:
    """Resolve transcript paths from agent_stop observation events.

    Scans JSONL files in observation_dir for lines containing agent_stop
    events (written by obs_agent_stop.py hook). Extracts the
    agent_transcript_path and maps it by agent_id or observation file stem.

    Args:
        observation_dir: Directory containing observation files and events.

    Returns:
        Dict mapping observation file stem (e.g., "cal-01-attacker") to
        transcript Path. Empty dict if no agent_stop events found.
    """
    transcript_map: dict[str, Path] = {}

    # Look for JSONL event files in observation directory
    event_files = list(observation_dir.glob("*.jsonl"))
    for event_file in event_files:
        try:
            with open(event_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if record.get("event_type") != "agent_stop":
                        continue

                    data = record.get("data", {})
                    agent_id = data.get("agent_id", "")
                    transcript_path_str = data.get("agent_transcript_path", "")

                    if agent_id and transcript_path_str:
                        tp = Path(transcript_path_str)
                        # Map by agent_id (best match for observation files)
                        transcript_map[agent_id] = tp
        except OSError:
            continue

    return transcript_map


# ---------------------------------------------------------------------------
# Cross-file checks
# ---------------------------------------------------------------------------


def _check_cross_file_similarity(
    files: list[Path],
) -> list[IntegrityViolation]:
    """Check for suspiciously similar findings across different agents on same contract."""
    violations: list[IntegrityViolation] = []

    # Group by contract
    by_contract: dict[str, list[dict[str, Any]]] = {}
    for f in files:
        try:
            data = json.loads(f.read_text())
            contract_id = data.get("contract_id", "unknown")
            by_contract.setdefault(contract_id, []).append(data)
        except (json.JSONDecodeError, OSError):
            continue

    for contract_id, entries in by_contract.items():
        if len(entries) < 2:
            continue

        # Check if graph_stats are identical across all agents for same contract
        # This is actually EXPECTED (same contract = same graph), but the build_hash
        # and timestamp should differ between agents
        timestamps = {
            json.dumps(e.get("session_metadata", {}), sort_keys=True)
            for e in entries
        }

        if len(timestamps) == 1 and len(entries) > 1:
            violations.append(
                IntegrityViolation(
                    check_name="identical_timestamps",
                    severity="critical",
                    file_path=f"contract={contract_id}",
                    details=(
                        f"All {len(entries)} agents for contract {contract_id} have "
                        "identical session_metadata timestamps. This is impossible "
                        "if agents ran independently."
                    ),
                    evidence={
                        "contract_id": contract_id,
                        "agent_count": len(entries),
                        "unique_timestamps": len(timestamps),
                    },
                    failure_mode=_classify_failure_mode("identical_timestamps"),
                )
            )

        # Check if finding titles are too similar across agents
        all_titles: list[str] = []
        for entry in entries:
            for finding in entry.get("findings", []):
                title = finding.get("title", "")
                if title:
                    all_titles.append(title)

        if len(all_titles) > 2:
            # Simple overlap check: if >50% titles are substring-matches
            overlap = 0
            for i, t1 in enumerate(all_titles):
                for t2 in all_titles[i + 1 :]:
                    # Normalize and check significant overlap
                    t1_words = set(t1.lower().split())
                    t2_words = set(t2.lower().split())
                    if len(t1_words & t2_words) > len(t1_words | t2_words) * 0.7:
                        overlap += 1

            if overlap > len(all_titles) * 0.5:
                violations.append(
                    IntegrityViolation(
                        check_name="cross_agent_finding_similarity",
                        severity="warning",
                        file_path=f"contract={contract_id}",
                        details=(
                            f"High finding title overlap across agents for "
                            f"contract {contract_id}. Different agent types "
                            "should produce different perspectives."
                        ),
                        evidence={
                            "overlap_pairs": overlap,
                            "total_titles": len(all_titles),
                        },
                        failure_mode=_classify_failure_mode("cross_agent_finding_similarity"),
                    )
                )

    return violations


def _check_worktree_isolation(
    files: list[Path],
) -> list[IntegrityViolation]:
    """Check if git worktrees were actually created for isolated execution.

    Accepts either live worktrees OR session_metadata.isolation == 'worktree'
    in observation files as evidence. Worktrees may be cleaned up after agent
    shutdown but before validation runs.
    """
    violations: list[IntegrityViolation] = []

    # First check if observation files self-report worktree isolation
    obs_with_worktree_evidence = 0
    for f in files:
        try:
            data = json.loads(f.read_text())
            if data.get("session_metadata", {}).get("isolation") == "worktree":
                obs_with_worktree_evidence += 1
        except (json.JSONDecodeError, OSError):
            pass

    if obs_with_worktree_evidence == len(files) and len(files) > 0:
        # All observations self-report worktree isolation — accept this
        return violations

    try:
        result = subprocess.run(
            ["git", "worktree", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        worktree_lines = result.stdout.strip().split("\n")
        # Filter out the main worktree
        extra_worktrees = [
            line for line in worktree_lines
            if line.strip() and "detached HEAD" not in line and "bare" not in line
        ]

        if not extra_worktrees and len(files) > 0:
            violations.append(
                IntegrityViolation(
                    check_name="no_worktrees_found",
                    severity="critical",
                    file_path="git worktree list",
                    details=(
                        "No git worktrees found besides main. Agents were supposed "
                        "to run in isolated worktrees (isolation: 'worktree'). "
                        "Either worktrees were cleaned up, or isolation never worked. "
                        "Observation files in main repo suggest no real isolation."
                    ),
                    evidence={
                        "worktree_count": len(worktree_lines),
                        "observation_files": len(files),
                    },
                    failure_mode=_classify_failure_mode("no_worktrees_found"),
                )
            )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        violations.append(
            IntegrityViolation(
                check_name="worktree_check_failed",
                severity="warning",
                file_path="git",
                details="Could not run git worktree list to verify isolation",
                failure_mode=_classify_failure_mode("worktree_check_failed"),
            )
        )

    return violations


def _check_graph_stats_against_ground_truth(
    files: list[Path],
    ground_truth_dir: Path,
) -> list[IntegrityViolation]:
    """Compare reported graph stats against actual build output.

    Requires running `uv run alphaswarm build-kg` on each contract and
    saving the output to ground_truth_dir for comparison.
    """
    violations: list[IntegrityViolation] = []

    for f in files:
        try:
            data = json.loads(f.read_text())
            contract_id = data.get("contract_id", "unknown")
            reported_stats = data.get("graph_stats", {})

            gt_path = ground_truth_dir / f"{contract_id}-graph-stats.json"
            if not gt_path.exists():
                continue

            actual_stats = json.loads(gt_path.read_text())
            reported_nodes = reported_stats.get("nodes", 0)
            actual_nodes = actual_stats.get("nodes", 0)

            if actual_nodes > 0:
                deviation = abs(reported_nodes - actual_nodes) / actual_nodes
                if deviation > 0.3:  # >30% deviation
                    violations.append(
                        IntegrityViolation(
                            check_name="graph_stats_mismatch",
                            severity="critical",
                            file_path=str(f),
                            details=(
                                f"Reported {reported_nodes} nodes but actual build "
                                f"produced {actual_nodes} nodes ({deviation:.0%} deviation). "
                                "Agent likely fabricated graph stats."
                            ),
                            evidence={
                                "contract_id": contract_id,
                                "reported_nodes": reported_nodes,
                                "actual_nodes": actual_nodes,
                                "deviation": round(deviation, 2),
                            },
                            failure_mode=_classify_failure_mode("graph_stats_mismatch"),
                        )
                    )
        except (json.JSONDecodeError, OSError):
            continue

    return violations


# ---------------------------------------------------------------------------
# CLI Entrypoint (for running as post-session check)
# ---------------------------------------------------------------------------


def run_integrity_check(
    observation_dir: str = ".vrs/observations/plan12",
    batch_id: str = "batch-1",
    ground_truth_dir: str | None = None,
) -> IntegrityReport:
    """Run full integrity check suite and print results.

    Designed to be called from the evaluation pipeline after
    every Agent Teams session completes.
    """
    obs_path = Path(observation_dir)
    gt_path = Path(ground_truth_dir) if ground_truth_dir else None

    report = validate_batch(obs_path, batch_id, gt_path)

    # Log summary
    logger.info("Integrity check: %s (%s)", report.verdict, report.summary)
    for v in report.violations:
        log_fn = logger.error if v.severity == "critical" else logger.warning
        log_fn("[%s] %s: %s", v.severity.upper(), v.check_name, v.details)

    return report
