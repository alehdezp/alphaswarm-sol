"""Heuristic reasoning timeline extraction from JSONL transcripts.

Extracts structured reasoning events and tool sequences from agent session
transcripts. This is a ~70% accuracy heuristic extractor -- the LLM-based
refinement layer lives in 3.1c.3-02 (reasoning decomposer).

Populates the observation schema v1 `reasoning` section:
  reasoning.timeline -> list[ReasoningEvent]
  reasoning.tool_sequence -> list[{tool, subtype, index, ts}]

Downstream consumers:
  - 3.1c.3-02: Reasoning decomposer (adds LLM scoring on top of this extraction)
  - 3.1c.3-06: Behavioral fingerprinter (uses tool sequences as core input)
  - 3.1c.3-10: Recommendation engine (maps failures to reasoning steps)

Uses TranscriptParser from tests.workflow_harness.lib.transcript_parser as the
primary parsing mechanism (Decision D-2).

DC-2 enforcement: No imports from alphaswarm_sol.kg or alphaswarm_sol.vulndocs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


# --- ReasoningEvent dataclass ---

MoveType = Literal[
    "hypothesis",
    "query_formulation",
    "query_execution",
    "result_interpretation",
    "evidence_integration",
    "conclusion",
]


@dataclass
class ReasoningEvent:
    """A single reasoning move extracted from a JSONL transcript.

    Each event represents one step in the agent's reasoning process,
    classified heuristically into one of 6 move types. The 6 types
    map to the 7-move reasoning decomposition (TESTING-PHILOSOPHY.md)
    minus SELF_CRITIQUE (which requires LLM assessment, not heuristic).

    Attributes:
        timestamp: ISO 8601 timestamp from the transcript record, or None.
        move_type: One of 6 reasoning move categories.
        content_snippet: First 200 characters of the relevant text.
        tool_call_id: ID of the associated tool call, or None for text-only events.
        references_prior_event: Index of the event this builds on (back-reference).
    """

    timestamp: str | None
    move_type: MoveType
    content_snippet: str
    tool_call_id: str | None
    references_prior_event: int | None


_SNIPPET_MAX = 200


def extract_reasoning_timeline(transcript_path: Path | None) -> list[ReasoningEvent]:
    """Heuristic classifier decomposing JSONL into ReasoningEvent sequences.

    Classification rules (heuristic, ~70% accuracy):
    - Text before first tool call -> hypothesis
    - Bash commands with 'alphaswarm query' -> query_formulation + query_execution
    - Text immediately after tool_result -> result_interpretation
    - Text referencing multiple prior results -> evidence_integration
    - Final structured output / last assistant message -> conclusion

    3.1c.3-02 can refine with LLM-based classification.

    Args:
        transcript_path: Path to JSONL transcript file, or None.

    Returns:
        List of ReasoningEvent in transcript order. Empty list for
        None/missing/empty transcripts (graceful degradation).
    """
    if transcript_path is None or not transcript_path.exists():
        return []

    if transcript_path.stat().st_size == 0:
        return []

    from tests.workflow_harness.lib.transcript_parser import TranscriptParser

    try:
        parser = TranscriptParser(transcript_path)
    except Exception:
        return []

    tool_calls = parser.get_tool_calls()
    records = parser.records

    events: list[ReasoningEvent] = []

    # Track state for classification
    first_tool_index: int | None = None
    if tool_calls:
        first_tool_index = tool_calls[0].index

    # Build a set of tool_use IDs for quick lookup
    tool_use_ids: set[str] = set()
    for tc in tool_calls:
        block_id = tc.content_block.get("id")
        if block_id:
            tool_use_ids.add(block_id)

    # Track which tool_result IDs we've seen (for result_interpretation detection)
    last_was_tool_result = False
    last_query_event_index: int | None = None
    seen_results_count = 0

    for record in records:
        record_type = record.get("type", "")
        message = record.get("message", {})
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue

        timestamp = record.get("timestamp") or message.get("timestamp")
        if isinstance(timestamp, (int, float)):
            timestamp = None
        elif timestamp is not None:
            timestamp = str(timestamp)

        if record_type == "assistant":
            # Process text blocks and tool_use blocks
            for block in content:
                if not isinstance(block, dict):
                    continue

                if block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if not text:
                        continue

                    snippet = text[:_SNIPPET_MAX]

                    if first_tool_index is not None and not tool_calls:
                        # Edge case: tool_calls empty but first_tool_index set
                        move_type: MoveType = "hypothesis"
                    elif first_tool_index is None:
                        # No tool calls at all -- everything is hypothesis/conclusion
                        move_type = "conclusion"
                    elif len(events) == 0 or (
                        not any(
                            e.move_type in ("query_execution", "result_interpretation")
                            for e in events
                        )
                    ):
                        # Text before any tool execution -> hypothesis
                        move_type = "hypothesis"
                    elif last_was_tool_result:
                        # Text immediately after a tool result -> result_interpretation
                        move_type = "result_interpretation"
                        last_was_tool_result = False
                    elif seen_results_count >= 2:
                        # Text after multiple results -> evidence_integration
                        move_type = "evidence_integration"
                    else:
                        # Default: hypothesis for early text, evidence_integration for later
                        move_type = "hypothesis"

                    ref = last_query_event_index if move_type == "result_interpretation" else None

                    events.append(ReasoningEvent(
                        timestamp=timestamp,
                        move_type=move_type,
                        content_snippet=snippet,
                        tool_call_id=None,
                        references_prior_event=ref,
                    ))

                elif block.get("type") == "tool_use":
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})
                    tool_id = block.get("id")
                    cmd = tool_input.get("command", "") if isinstance(tool_input, dict) else ""

                    if tool_name == "Bash" and "alphaswarm" in cmd and (
                        "query" in cmd or "build-kg" in cmd
                    ):
                        # Query formulation: the agent is constructing a CLI query
                        snippet = cmd[:_SNIPPET_MAX]
                        events.append(ReasoningEvent(
                            timestamp=timestamp,
                            move_type="query_formulation",
                            content_snippet=snippet,
                            tool_call_id=tool_id,
                            references_prior_event=None,
                        ))
                        # Immediately followed by query_execution
                        last_query_event_index = len(events) - 1
                        events.append(ReasoningEvent(
                            timestamp=timestamp,
                            move_type="query_execution",
                            content_snippet=snippet,
                            tool_call_id=tool_id,
                            references_prior_event=len(events) - 1,
                        ))

        elif record_type == "user":
            # Check for tool_result blocks
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    last_was_tool_result = True
                    seen_results_count += 1

    # Reclassify the last text event as "conclusion" if it exists
    # and was classified as something else
    if events:
        # Find last text event (non-tool)
        for i in range(len(events) - 1, -1, -1):
            if events[i].tool_call_id is None and events[i].move_type not in (
                "query_formulation", "query_execution"
            ):
                events[i] = ReasoningEvent(
                    timestamp=events[i].timestamp,
                    move_type="conclusion",
                    content_snippet=events[i].content_snippet,
                    tool_call_id=events[i].tool_call_id,
                    references_prior_event=events[i].references_prior_event,
                )
                break

    return events


def extract_tool_sequence(transcript_path: Path | None) -> list[dict]:
    """Extract ordered tool type sequence from transcript.

    Each entry classifies the tool call by subtype for behavioral
    fingerprinting (3.1c.3-06).

    Subtypes:
    - Bash + "build-kg" -> "build-kg"
    - Bash + "query" -> "query"
    - Read -> "read-file"
    - Other -> "other"

    Args:
        transcript_path: Path to JSONL transcript file, or None.

    Returns:
        List of dicts [{tool, subtype, index, ts}] in transcript order.
        Empty list for None/missing/empty transcripts (graceful degradation).
    """
    if transcript_path is None or not transcript_path.exists():
        return []

    if transcript_path.stat().st_size == 0:
        return []

    from tests.workflow_harness.lib.transcript_parser import TranscriptParser

    try:
        parser = TranscriptParser(transcript_path)
    except Exception:
        return []

    tool_calls = parser.get_tool_calls()
    sequence: list[dict] = []

    for tc in tool_calls:
        subtype = _classify_tool_subtype(tc.tool_name, tc.tool_input)
        sequence.append({
            "tool": tc.tool_name,
            "subtype": subtype,
            "index": tc.index,
            "ts": tc.timestamp,
        })

    return sequence


def _classify_tool_subtype(tool_name: str, tool_input: dict) -> str:
    """Classify a tool call into a behavioral subtype.

    Args:
        tool_name: The tool name (Bash, Read, Write, etc.).
        tool_input: The tool input parameters dict.

    Returns:
        Subtype string for behavioral fingerprinting.
    """
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if "build-kg" in cmd:
            return "build-kg"
        if "alphaswarm" in cmd and "query" in cmd:
            return "query"
        return "other"

    if tool_name == "Read":
        return "read-file"

    return "other"
