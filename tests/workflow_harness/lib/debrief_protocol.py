"""4-Layer Debrief Protocol for agent self-assessment.

Implements a cascading debrief strategy:
1. SendMessage — disk-read path (CC orchestrator writes artifact, Python reads it)
2. Hook gate — TeammateIdle/TaskCompleted blocking hook (exit 2 to block)
3. Transcript analysis — parse agent's existing transcript
4. Skip — no debrief data available (lowest confidence)

Each layer is attempted in order; first successful layer wins.

Layer 1 contract: CC test orchestrators (Plans 09-11) call SendMessage during
teardown and serialize DebriefResponse to `.vrs/observations/{session_id}_debrief.json`.
This module reads the artifact from disk in live mode — it does NOT call SendMessage.

CONTRACT_VERSION: 05.2
CONSUMERS: [3.1c-07 (Evaluator), 3.1c-08 (Runner)]
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from alphaswarm_sol.testing.evaluation.models import DebriefResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Debrief quality classification
# ---------------------------------------------------------------------------


class DebriefStatus(str, Enum):
    """Quality classification for debrief results."""

    HIGH_CONFIDENCE = "high_confidence"      # Direct SendMessage response (disk-read)
    MEDIUM_CONFIDENCE = "medium_confidence"  # Hook gate observations (with answers)
    LOW_CONFIDENCE = "low_confidence"        # Transcript analysis or gate-no-answers
    NO_DATA = "no_data"                      # Skip layer (no debrief)


def classify_debrief(debrief: DebriefResponse) -> DebriefStatus:
    """Classify debrief quality based on layer used and answer content.

    Confidence fix: gate with no answers = LOW_CONFIDENCE (not MEDIUM).
    """
    if debrief.layer_used == "send_message":
        return DebriefStatus.HIGH_CONFIDENCE
    elif debrief.layer_used in ("send_message_malformed", "send_message_no_response"):
        return DebriefStatus.LOW_CONFIDENCE
    elif debrief.layer_used == "hook_gate":
        # Only MEDIUM if we actually got answers
        if len(debrief.answers) > 0 and any(
            a not in ("[No answer]", "[No debrief data available]", "")
            for a in debrief.answers
        ):
            return DebriefStatus.MEDIUM_CONFIDENCE
        return DebriefStatus.LOW_CONFIDENCE
    elif debrief.layer_used == "transcript_analysis":
        return DebriefStatus.LOW_CONFIDENCE
    else:
        return DebriefStatus.NO_DATA


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Full 10-question debrief (non-compacted sessions)
# Questions 1-7: Core debrief questions
# Questions 8-10: Intelligence-targeted signals for 3.1c.3 modules
FULL_DEBRIEF_QUESTIONS = [
    "What was your primary hypothesis?",
    "What BSKG queries informed your analysis?",
    "What surprised you in the results?",
    "What evidence supports your conclusion?",
    "What evidence contradicts your conclusion?",
    "What would you investigate further?",
    "Rate your confidence in the finding (1-5 with justification)",
    "Which graph query was most informative and why?",
    "Which query returned unhelpful results and what would you change?",
    "What information did you need that you could not get from the graph?",
]

# Short 3-question debrief (compacted sessions — P11-IMP-04)
SHORT_DEBRIEF_QUESTIONS = [
    "What was your primary conclusion?",
    "What key evidence supports it?",
    "Rate your confidence (1-5)",
]

# Legacy alias for backward compatibility
DEFAULT_DEBRIEF_QUESTIONS = FULL_DEBRIEF_QUESTIONS

LAYER_NAMES = ("send_message", "hook_gate", "transcript_analysis", "skip")


# ---------------------------------------------------------------------------
# Layer results
# ---------------------------------------------------------------------------


@dataclass
class LayerResult:
    """Result from attempting a single debrief layer."""

    layer_name: str
    success: bool
    answers: list[str] = field(default_factory=list)
    raw_response: str = ""
    confidence: float = 0.0
    error: str = ""
    delivery_status: str = "not_attempted"


# ---------------------------------------------------------------------------
# DebriefResponseValidator
# ---------------------------------------------------------------------------


def validate_debrief_response(raw: str) -> dict[str, Any]:
    """Validate and parse a raw debrief response string.

    Handles:
    - Fence-stripped JSON (```json ... ``` markers)
    - Malformed JSON -> layer_used="send_message_malformed"
    - Dead-agent / absent artifact -> caller sets layer_used="send_message_no_response"

    Returns:
        dict with parsed data or error sentinel.
    """
    if not raw or not raw.strip():
        return {
            "valid": False,
            "layer_used": "send_message_no_response",
            "error": "Empty or absent response",
        }

    # Strip fence markers (```json ... ```)
    stripped = raw.strip()
    if stripped.startswith("```"):
        # Remove opening fence (possibly ```json or ``` )
        first_newline = stripped.find("\n")
        if first_newline >= 0:
            stripped = stripped[first_newline + 1 :]
        else:
            stripped = stripped[3:]
    if stripped.rstrip().endswith("```"):
        stripped = stripped.rstrip()[:-3]

    stripped = stripped.strip()

    try:
        parsed = json.loads(stripped)
        return {
            "valid": True,
            "data": parsed,
            "layer_used": "send_message",
        }
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "layer_used": "send_message_malformed",
            "error": f"JSON parse error after fence-stripping: {e}",
        }


# ---------------------------------------------------------------------------
# Compaction-aware question selection (P11-IMP-04)
# ---------------------------------------------------------------------------


def get_debrief_questions(
    session_id: str,
    obs_dir: Path | None = None,
) -> tuple[list[str], bool]:
    """Select debrief questions based on compaction state.

    If `{session_id}.compacted` marker is present, returns the short 3-question
    debrief. Otherwise returns the full 7-question debrief.

    Returns:
        Tuple of (questions, compacted_flag).
    """
    if obs_dir is not None:
        marker = obs_dir / f"{session_id}.compacted"
        if marker.exists():
            return list(SHORT_DEBRIEF_QUESTIONS), True

    return list(FULL_DEBRIEF_QUESTIONS), False


# ---------------------------------------------------------------------------
# Individual layer implementations
# ---------------------------------------------------------------------------


def attempt_send_message_layer(
    _agent_name: str,
    _questions: list[str],
    *,
    session_id: str = "",
    obs_dir: Path | None = None,
    simulated: bool = True,
    **_kwargs: Any,
) -> LayerResult:
    """Layer 1: Disk-read debrief via serialized artifact.

    In live mode: CC test orchestrators (Plans 09-11) call SendMessage during
    teardown and write the debrief response to:
        .vrs/observations/{session_id}_debrief.json

    This function reads that artifact from disk. It does NOT call SendMessage.

    In simulated mode: always fails (no artifact to read).
    """
    if simulated:
        return LayerResult(
            layer_name="send_message",
            success=False,
            error="Simulated mode -- no live agent artifact to read",
            delivery_status="not_attempted",
        )

    if not session_id or obs_dir is None:
        return LayerResult(
            layer_name="send_message",
            success=False,
            error="Missing session_id or obs_dir for disk-read path",
            delivery_status="not_attempted",
        )

    artifact_path = obs_dir / f"{session_id}_debrief.json"

    if not artifact_path.exists():
        # Dead-agent detection (ADV-5-01): SendMessage may have returned
        # success but agent died before writing artifact
        logger.warning(
            "Debrief artifact not found at %s — dead agent or not yet written",
            artifact_path,
        )
        return LayerResult(
            layer_name="send_message_no_response",
            success=False,
            error=f"Artifact not found: {artifact_path}",
            confidence=0.0,
            delivery_status="phantom",
        )

    try:
        raw = artifact_path.read_text()
    except OSError as e:
        return LayerResult(
            layer_name="send_message_no_response",
            success=False,
            error=f"Failed to read artifact: {e}",
            delivery_status="phantom",
        )

    # Validate and parse the artifact
    result = validate_debrief_response(raw)

    if not result["valid"]:
        return LayerResult(
            layer_name=result["layer_used"],
            success=False,
            raw_response=raw[:2000],
            error=result.get("error", "Unknown parse error"),
            delivery_status="delivered" if raw.strip() else "phantom",
        )

    # Successfully parsed artifact
    data = result["data"]
    answers = data.get("answers", [])

    return LayerResult(
        layer_name="send_message",
        success=True,
        answers=answers,
        raw_response=raw[:2000],
        confidence=0.9,
        delivery_status="delivered",
    )


def attempt_hook_gate_layer(
    agent_name: str,
    _questions: list[str],
    *,
    obs_dir: Path | None = None,
    **_kwargs: Any,
) -> LayerResult:
    """Layer 2: Hook gate debrief via TeammateIdle/TaskCompleted blocking.

    Checks if observation data from debrief hooks is available.
    The debrief_gate.py and debrief_task_complete.py hooks record
    observations that can be used as debrief signals.
    """
    if obs_dir is None or not obs_dir.exists():
        return LayerResult(
            layer_name="hook_gate",
            success=False,
            error="No observations directory available",
            delivery_status="not_attempted",
        )

    # Look for debrief-related observations
    debrief_data = _extract_debrief_from_observations(obs_dir, agent_name)
    if not debrief_data:
        return LayerResult(
            layer_name="hook_gate",
            success=False,
            error="No debrief observations found for agent",
            delivery_status="not_attempted",
        )

    return LayerResult(
        layer_name="hook_gate",
        success=True,
        answers=debrief_data.get("answers", []),
        raw_response=json.dumps(debrief_data),
        confidence=0.6,
        delivery_status="delivered",
    )


def attempt_transcript_layer(
    _agent_name: str,
    questions: list[str],
    *,
    transcript_path: Path | None = None,
    **_kwargs: Any,
) -> LayerResult:
    """Layer 3: Transcript analysis debrief.

    Parses agent's transcript to infer answers to debrief questions.
    Lower confidence than direct debrief but always available if
    transcript exists.
    """
    if transcript_path is None or not transcript_path.exists():
        return LayerResult(
            layer_name="transcript_analysis",
            success=False,
            error="No transcript available",
            delivery_status="not_attempted",
        )

    try:
        transcript_text = transcript_path.read_text()
    except OSError as e:
        return LayerResult(
            layer_name="transcript_analysis",
            success=False,
            error=f"Failed to read transcript: {e}",
            delivery_status="not_attempted",
        )

    if not transcript_text.strip():
        return LayerResult(
            layer_name="transcript_analysis",
            success=False,
            error="Transcript is empty",
            delivery_status="not_attempted",
        )

    # Extract inferred answers from transcript content
    inferred = _infer_from_transcript(transcript_text, questions)

    return LayerResult(
        layer_name="transcript_analysis",
        success=True,
        answers=inferred,
        raw_response=transcript_text[:2000],  # Truncate for storage
        confidence=0.3,
        delivery_status="delivered",
    )


def attempt_skip_layer(
    _agent_name: str,
    questions: list[str],
    **_kwargs: Any,
) -> LayerResult:
    """Layer 4: Skip -- no debrief data available.

    Always succeeds with empty answers and zero confidence.
    Used as the final fallback.
    """
    return LayerResult(
        layer_name="skip",
        success=True,
        answers=["[No debrief data available]"] * len(questions),
        confidence=0.0,
        delivery_status="not_attempted",
    )


# ---------------------------------------------------------------------------
# Cascade orchestrator
# ---------------------------------------------------------------------------


LAYER_FUNCTIONS = [
    attempt_send_message_layer,
    attempt_hook_gate_layer,
    attempt_transcript_layer,
    attempt_skip_layer,
]


def run_debrief(
    agent_name: str,
    agent_type: str,
    questions: list[str] | None = None,
    obs_dir: Path | None = None,
    transcript_path: Path | None = None,
    simulated: bool = True,
    session_id: str = "",
) -> DebriefResponse:
    """Run the 4-layer debrief cascade for an agent.

    Attempts each layer in order (send_message -> hook_gate ->
    transcript_analysis -> skip). First successful layer wins.

    Compaction-aware: if no explicit questions provided, selects 3 vs 7
    based on {session_id}.compacted marker presence.

    Args:
        agent_name: Name of the agent being debriefed.
        agent_type: Role of the agent (attacker, defender, etc.).
        questions: Debrief questions. Defaults based on compaction state.
        obs_dir: Path to .vrs/observations/ directory.
        transcript_path: Path to agent's transcript file.
        simulated: Whether this is a simulated run (no live agents).
        session_id: Session identifier for disk-read path and compaction.

    Returns:
        DebriefResponse with debrief data from the first successful layer.
    """
    # Compaction-aware question selection
    compacted = False
    if questions is None:
        questions, compacted = get_debrief_questions(session_id, obs_dir)

    kwargs: dict[str, Any] = {
        "obs_dir": obs_dir,
        "transcript_path": transcript_path,
        "simulated": simulated,
        "session_id": session_id,
    }

    for layer_fn in LAYER_FUNCTIONS:
        result = layer_fn(agent_name, questions, **kwargs)
        if result.success:
            # Pad answers to match questions length
            answers = result.answers
            while len(answers) < len(questions):
                answers.append("[No answer]")
            answers = answers[: len(questions)]

            return DebriefResponse(
                agent_name=agent_name,
                agent_type=agent_type,
                layer_used=result.layer_name,
                questions=questions,
                answers=answers,
                confidence=result.confidence,
                raw_response=result.raw_response,
                compacted=compacted,
                delivery_status=result.delivery_status,
            )

    # Should never reach here (skip always succeeds), but just in case
    return DebriefResponse(
        agent_name=agent_name,
        agent_type=agent_type,
        layer_used="skip",
        questions=questions,
        answers=["[Debrief failed]"] * len(questions),
        confidence=0.0,
        compacted=compacted,
        delivery_status="not_attempted",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_debrief_from_observations(
    obs_dir: Path, agent_name: str
) -> dict[str, Any] | None:
    """Extract debrief-related data from observation JSONL files.

    Looks for task_completed and agent_stop events that might contain
    debrief information for the specified agent.
    """
    debrief_signals: list[dict[str, Any]] = []

    for jsonl_file in sorted(obs_dir.glob("*.jsonl")):
        try:
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    event_type = record.get("event_type", "")
                    data = record.get("data", {})

                    # Look for agent-specific debrief signals
                    if event_type == "task_completed":
                        debrief_signals.append(data)
                    elif event_type == "agent_stop":
                        if data.get("agent_id", "") == agent_name:
                            debrief_signals.append(data)
        except OSError:
            continue

    if not debrief_signals:
        return None

    # Aggregate signals into debrief data
    return {
        "agent_name": agent_name,
        "signals": debrief_signals,
        "answers": [],  # Hook gate can provide structured answers in future
    }


def _infer_from_transcript(transcript_text: str, questions: list[str]) -> list[str]:
    """Infer debrief answers from transcript content.

    Simple heuristic extraction -- looks for key phrases that map
    to debrief questions. In future, this could use LLM summarization.
    """
    answers = []
    lines = transcript_text.strip().split("\n")

    for question in questions:
        q_lower = question.lower()
        # Simple keyword matching for common debrief topics
        if "hypothesis" in q_lower or "conclusion" in q_lower:
            answer = _find_relevant_lines(
                lines, ["hypothesis", "conclusion", "strategy", "approach", "plan", "first"]
            )
        elif "bskg" in q_lower or "query" in q_lower or "queries" in q_lower:
            answer = _find_relevant_lines(
                lines, ["query", "bskg", "alphaswarm", "graph"]
            )
        elif "surprised" in q_lower:
            answer = _find_relevant_lines(
                lines, ["surprise", "unexpected", "surprising", "interesting"]
            )
        elif "evidence" in q_lower:
            answer = _find_relevant_lines(
                lines, ["evidence", "found", "vulnerability", "finding", "supports"]
            )
        elif "contradict" in q_lower:
            answer = _find_relevant_lines(
                lines, ["contradict", "against", "however", "but", "alternatively"]
            )
        elif "investigate" in q_lower or "further" in q_lower:
            answer = _find_relevant_lines(
                lines, ["investigate", "further", "next", "explore", "deeper"]
            )
        elif "confidence" in q_lower or "rate" in q_lower:
            answer = _find_relevant_lines(
                lines, ["confidence", "certain", "sure", "rating", "high", "medium", "low"]
            )
        elif "strategy" in q_lower:
            answer = _find_relevant_lines(
                lines, ["strategy", "approach", "plan", "first"]
            )
        elif "alternative" in q_lower:
            answer = _find_relevant_lines(
                lines, ["alternative", "hypothesis", "consider", "reject"]
            )
        elif "differently" in q_lower:
            answer = _find_relevant_lines(
                lines, ["differently", "improve", "next time", "better"]
            )
        else:
            answer = "[Could not infer from transcript]"

        answers.append(answer)

    return answers


def _find_relevant_lines(lines: list[str], keywords: list[str]) -> str:
    """Find lines containing any of the given keywords."""
    matches = []
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords):
            matches.append(line.strip())
            if len(matches) >= 3:
                break

    if matches:
        return " | ".join(matches)
    return "[No relevant content found in transcript]"
