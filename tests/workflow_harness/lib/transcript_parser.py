"""Parse Claude Code JSONL transcripts for tool-level analysis.

Claude Code writes session transcripts as JSONL files:
- Main session: ~/.claude/projects/{encoded-path}/{session-uuid}.jsonl
- Subagents: subagents/agent-{id}.jsonl (relative to main session dir)

Record types: "user", "assistant", "progress", "file-history-snapshot"
Tool calls appear as content blocks with type "tool_use" in assistant records.
Tool results appear as content blocks with type "tool_result" in user records.

Reference: .planning/research/claude-code-hooks-mastery/.claude/hooks/subagent_stop.py
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


RESULT_TRUNCATE_LEN = 500
BSKG_RESULT_TRUNCATE_LEN = 2000

# Regex for BSKG node IDs: F-xxx-yyy, C-xxx-yyy, E-xxx-yyy
_BSKG_NODE_ID_RE = re.compile(r"[FCE]-\w+-\w+")


@dataclass
class BSKGQueryEvent:
    """A BSKG query event with timestamp and extracted node IDs.

    Used by GVS (3.1c-04) to assess graph utilization quality.
    Satisfies GVS Data Requirements: bskg_query_events[].timestamp,
    bskg_query_events[].node_ids.
    """

    timestamp: str | None
    command: str
    query_type: str
    node_ids: list[str] = field(default_factory=list)
    tool_call_index: int = 0


@dataclass
class ToolSequenceEntry:
    """A tool call with timestamp for sequence analysis.

    Satisfies GVS Data Requirements: tool_sequence_with_timestamps[].
    """

    tool_name: str
    timestamp: str | None
    index: int = 0


@dataclass
class SubagentSpawn:
    """A subagent lifecycle event extracted from Task tool calls.

    Extracted from Task tool calls in the transcript and optional
    subagent JSONL files on disk.
    """

    agent_id: str
    task_subject: str = ""
    spawn_index: int = 0
    transcript_path: Path | None = None
    tool_count: int = 0


@dataclass
class ObservationSummary:
    """Complete observation data extracted from a transcript.

    This is the primary evaluation data source (P13-IMP-08 Track A).
    TranscriptParser.to_observation_summary() is the sole producer.
    All list-typed fields default to [] (never None) for null-safety.

    Fields marked KNOWN_ABSENT return None when the data source cannot
    provide them (e.g., no BSKG queries in a non-audit session).
    """

    tool_counts: dict[str, int] = field(default_factory=dict)
    tool_sequences: list[ToolSequenceEntry] = field(default_factory=list)
    bskg_query_events: list[BSKGQueryEvent] = field(default_factory=list)
    tool_failures: list[dict[str, Any]] = field(default_factory=list)
    agent_lifecycle_events: list[dict[str, Any]] = field(default_factory=list)
    total_tool_calls: int = 0
    session_id: str | None = None
    data_quality: Any = None  # Populated by ObservationParser adapter
    parse_errors: int = 0


@dataclass
class ToolCall:
    """A single tool invocation extracted from a transcript.

    Attributes:
        tool_name: Tool identifier (Bash, Read, Grep, Task, Skill, etc.)
        tool_input: Full input parameters dict
        tool_result: Truncated result string (first 500 chars), None if not yet available
        index: Position in the sequence of tool calls (0-based)
        timestamp: ISO 8601 timestamp when tool call was made, or None if unavailable
        duration_ms: Execution duration in milliseconds, or None if unavailable
        content_block: Raw content block dict from the transcript record
    """

    tool_name: str
    tool_input: dict[str, Any] = field(default_factory=dict)
    tool_result: str | None = None
    index: int = 0
    timestamp: str | None = None
    duration_ms: int | None = None
    content_block: dict[str, Any] = field(default_factory=dict)


@dataclass
class BSKGQuery:
    """A BSKG/graph query extracted from a Bash tool call.

    Extracted when a Bash tool call's command contains 'alphaswarm' and
    one of: 'query', 'build-kg', 'vulndocs'.

    Attributes:
        command: Full shell command string.
        query_type: Classified type -- "build-kg", "query", "pattern-query", "vulndocs".
        query_text: The query string itself, extracted from the command.
        result_snippet: First 2000 chars of the tool result.
        tool_call_index: Position of the originating ToolCall in the transcript (0-based).
        cited_in_conclusion: Heuristic boolean -- True if subsequent Write or SendMessage
            tool calls reference content from this query's result_snippet.
    """

    command: str
    query_type: str
    query_text: str
    result_snippet: str
    tool_call_index: int
    cited_in_conclusion: bool = False


class TranscriptParser:
    """Parse a Claude Code JSONL transcript for tool-level analysis.

    Reads the JSONL file, extracts tool_use blocks from assistant messages,
    and provides query methods for assertions.

    Example:
        >>> parser = TranscriptParser(Path("session.jsonl"))
        >>> assert parser.has_tool_call("Bash")
        >>> seq = parser.get_tool_sequence()
        >>> assert "Bash" in seq
    """

    def __init__(self, jsonl_path: Path) -> None:
        self._path = jsonl_path
        self._records: list[dict[str, Any]] = []
        self._tool_calls: list[ToolCall] | None = None
        self._load()

    def _load(self) -> None:
        """Load and parse the JSONL file."""
        if not self._path.exists():
            return
        with open(self._path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    self._records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    def _extract_tool_calls(self) -> list[ToolCall]:
        """Extract all tool_use blocks from assistant records."""
        calls: list[ToolCall] = []
        # Map tool_use_id -> ToolCall for result matching
        id_to_call: dict[str, ToolCall] = {}
        # Map tool_use_id -> assistant record timestamp for duration calc
        id_to_timestamp: dict[str, str] = {}

        for record in self._records:
            record_type = record.get("type", "")
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue

            content = message.get("content")
            if not isinstance(content, list):
                continue

            # Extract record-level timestamp (ISO 8601)
            record_timestamp = record.get("timestamp") or message.get("timestamp")

            if record_type == "assistant":
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        ts = record_timestamp
                        if isinstance(ts, (int, float)):
                            ts = None  # Only accept string ISO 8601
                        tc = ToolCall(
                            tool_name=block.get("name", "unknown"),
                            tool_input=block.get("input", {}),
                            index=len(calls),
                            timestamp=str(ts) if ts else None,
                            content_block=dict(block),
                        )
                        calls.append(tc)
                        tool_id = block.get("id")
                        if tool_id:
                            id_to_call[tool_id] = tc
                            if ts:
                                id_to_timestamp[tool_id] = str(ts)

            elif record_type == "user":
                result_timestamp = record_timestamp
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_result":
                        tool_id = block.get("tool_use_id")
                        if tool_id and tool_id in id_to_call:
                            result_content = block.get("content", "")
                            if isinstance(result_content, list):
                                # Extract text from content blocks
                                texts = []
                                for part in result_content:
                                    if isinstance(part, dict) and part.get("type") == "text":
                                        texts.append(part.get("text", ""))
                                result_content = "\n".join(texts)
                            result_str = str(result_content)
                            id_to_call[tool_id].tool_result = result_str[:RESULT_TRUNCATE_LEN]

                            # Compute duration_ms from timestamps
                            if (
                                tool_id in id_to_timestamp
                                and result_timestamp
                                and isinstance(result_timestamp, str)
                            ):
                                duration = self._compute_duration_ms(
                                    id_to_timestamp[tool_id], str(result_timestamp)
                                )
                                if duration is not None:
                                    id_to_call[tool_id].duration_ms = duration

        return calls

    @staticmethod
    def _compute_duration_ms(start_iso: str, end_iso: str) -> int | None:
        """Compute duration in milliseconds between two ISO 8601 timestamps."""
        from datetime import datetime

        try:
            # Handle both with and without timezone
            start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
            delta = end - start
            ms = int(delta.total_seconds() * 1000)
            return ms if ms >= 0 else None
        except (ValueError, TypeError):
            return None

    def get_tool_calls(self) -> list[ToolCall]:
        """All tool calls in order of invocation."""
        if self._tool_calls is None:
            self._tool_calls = self._extract_tool_calls()
        return list(self._tool_calls)

    def get_tool_sequence(self) -> list[str]:
        """Ordered list of tool names invoked."""
        return [tc.tool_name for tc in self.get_tool_calls()]

    def get_bash_commands(self) -> list[str]:
        """Extract command strings from all Bash tool calls."""
        commands: list[str] = []
        for tc in self.get_tool_calls():
            if tc.tool_name == "Bash":
                cmd = tc.tool_input.get("command", "")
                if cmd:
                    commands.append(cmd)
        return commands

    def has_tool_call(self, tool_name: str, **input_match: Any) -> bool:
        """Check if a tool was called, optionally matching input fields.

        Args:
            tool_name: Exact tool name to match
            **input_match: Key-value pairs that must appear in tool_input
        """
        for tc in self.get_tool_calls():
            if tc.tool_name != tool_name:
                continue
            if not input_match:
                return True
            if all(tc.tool_input.get(k) == v for k, v in input_match.items()):
                return True
        return False

    def first_tool_call(self, tool_name: str) -> ToolCall | None:
        """First invocation of a given tool, or None."""
        for tc in self.get_tool_calls():
            if tc.tool_name == tool_name:
                return tc
        return None

    def tool_calls_matching(self, tool_name: str, **input_match: Any) -> list[ToolCall]:
        """All invocations of a tool, optionally filtered by input fields."""
        result: list[ToolCall] = []
        for tc in self.get_tool_calls():
            if tc.tool_name != tool_name:
                continue
            if not input_match or all(
                tc.tool_input.get(k) == v for k, v in input_match.items()
            ):
                result.append(tc)
        return result

    # --- Graph-first compliance helpers ---

    def has_bskg_query(self) -> bool:
        """Check if any BSKG/graph query was executed."""
        for tc in self.get_tool_calls():
            if tc.tool_name == "Bash":
                cmd = tc.tool_input.get("command", "")
                if "alphaswarm" in cmd and ("query" in cmd or "build-kg" in cmd or "vulndocs" in cmd):
                    return True
        return False

    def bskg_query_index(self) -> int | None:
        """Index of the first BSKG query tool call, or None."""
        for tc in self.get_tool_calls():
            if tc.tool_name == "Bash":
                cmd = tc.tool_input.get("command", "")
                if "alphaswarm" in cmd and ("query" in cmd or "build-kg" in cmd):
                    return tc.index
        return None

    def first_conclusion_index(self) -> int | None:
        """Index of the first tool call that looks like producing a conclusion.

        Heuristic: a Write or SendMessage call that contains finding/verdict language.
        """
        conclusion_tools = {"Write", "SendMessage"}
        conclusion_keywords = {"finding", "verdict", "vulnerability", "conclusion", "confirmed"}
        for tc in self.get_tool_calls():
            if tc.tool_name not in conclusion_tools:
                continue
            input_str = json.dumps(tc.tool_input).lower()
            if any(kw in input_str for kw in conclusion_keywords):
                return tc.index
        return None

    @property
    def records(self) -> list[dict[str, Any]]:
        """Public read-only access to parsed JSONL records.

        Returns a copy to prevent mutation of internal state. This is the
        stable API for 3.1c-04 (Graph Value Scorer) to read raw records.
        """
        return list(self._records)

    @property
    def record_count(self) -> int:
        """Number of JSONL records in the transcript."""
        return len(self._records)

    @property
    def total_chars(self) -> int:
        """Approximate total character count of the transcript."""
        return sum(len(json.dumps(r)) for r in self._records)

    # --- BSKGQuery extraction and new accessor methods ---

    def get_bskg_queries(self) -> list[BSKGQuery]:
        """Extract all BSKG queries from Bash tool calls.

        Scans all Bash tool calls for alphaswarm commands. For each match,
        creates a BSKGQuery with classified type and citation status.

        Returns:
            List of BSKGQuery in transcript order. Empty list if no
            BSKG queries found.
        """
        tool_calls = self.get_tool_calls()
        queries: list[BSKGQuery] = []

        for tc in tool_calls:
            if tc.tool_name != "Bash":
                continue
            cmd = tc.tool_input.get("command", "")
            if not cmd or "alphaswarm" not in cmd:
                continue

            query_type = self._classify_bskg_query_type(cmd)
            if query_type is None:
                continue

            query_text = self._extract_query_text(cmd, query_type)

            # Get full result (up to 2000 chars) -- need to look at raw records
            result_snippet = self._get_full_result_for_tool(tc, BSKG_RESULT_TRUNCATE_LEN)

            queries.append(BSKGQuery(
                command=cmd,
                query_type=query_type,
                query_text=query_text,
                result_snippet=result_snippet,
                tool_call_index=tc.index,
                cited_in_conclusion=False,  # Set below
            ))

        # Determine citation status
        self._compute_citations(queries, tool_calls)

        return queries

    @staticmethod
    def _classify_bskg_query_type(cmd: str) -> str | None:
        """Classify a command string into a BSKG query type.

        Returns None if the command is not a recognized BSKG query.
        """
        if "build-kg" in cmd:
            return "build-kg"
        if "vulndocs" in cmd:
            return "vulndocs"
        if "query" in cmd:
            if "pattern:" in cmd:
                return "pattern-query"
            return "query"
        return None

    @staticmethod
    def _extract_query_text(cmd: str, query_type: str) -> str:
        """Extract the query text from a command string based on type."""
        import re

        if query_type == "build-kg":
            # Extract path after build-kg
            match = re.search(r"build-kg\s+(\S+)", cmd)
            return match.group(1) if match else cmd

        if query_type in ("query", "pattern-query"):
            # Extract quoted string after query
            match = re.search(r"query\s+['\"](.+?)['\"]", cmd)
            if match:
                return match.group(1)
            # Fallback: text after query
            match = re.search(r"query\s+(\S+)", cmd)
            return match.group(1) if match else cmd

        if query_type == "vulndocs":
            # Extract subcommand and args
            match = re.search(r"vulndocs\s+(.*)", cmd)
            return match.group(1).strip() if match else cmd

        return cmd

    def _get_full_result_for_tool(self, tc: ToolCall, max_len: int) -> str:
        """Get the full result string for a tool call, up to max_len chars.

        Looks up the tool_result from raw records to get more than the
        standard 500-char truncation.
        """
        # If the content_block has an id, look up the full result in records
        tool_id = tc.content_block.get("id") if tc.content_block else None
        if not tool_id:
            return (tc.tool_result or "")[:max_len]

        for record in self._records:
            if record.get("type") != "user":
                continue
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result" and block.get("tool_use_id") == tool_id:
                    result_content = block.get("content", "")
                    if isinstance(result_content, list):
                        texts = []
                        for part in result_content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                texts.append(part.get("text", ""))
                        result_content = "\n".join(texts)
                    return str(result_content)[:max_len]

        return (tc.tool_result or "")[:max_len]

    @staticmethod
    def _compute_citations(
        queries: list[BSKGQuery], tool_calls: list[ToolCall]
    ) -> None:
        """Determine which BSKG queries were cited in subsequent conclusions.

        Heuristic: Take first 200 chars of result_snippet. For each subsequent
        Write or SendMessage tool call, check if any substring of length >= 20
        from the result appears in the tool_input.
        """
        conclusion_tools = {"Write", "SendMessage"}

        for query in queries:
            if not query.result_snippet:
                continue
            # Take first 200 chars as reference
            ref = query.result_snippet[:200]
            if len(ref) < 20:
                continue

            # Check subsequent tool calls for citation
            for tc in tool_calls:
                if tc.index <= query.tool_call_index:
                    continue
                if tc.tool_name not in conclusion_tools:
                    continue
                input_str = json.dumps(tc.tool_input)
                # Check for substring matches of length >= 20
                for i in range(0, len(ref) - 19):
                    chunk = ref[i : i + 20]
                    if chunk in input_str:
                        query.cited_in_conclusion = True
                        break
                if query.cited_in_conclusion:
                    break

    def get_text_between_tools(self, start_tool: str, end_tool: str) -> list[str]:
        """Extract assistant text content between two tool calls.

        Finds all (start_tool, end_tool) pairs in the transcript and returns
        the text from assistant messages between them. Used by debrief fallback
        (layer 4) to extract reasoning from transcript when interactive debrief
        is unavailable.

        Args:
            start_tool: Tool name marking the start boundary.
            end_tool: Tool name marking the end boundary.

        Returns:
            List of concatenated text strings, one per (start, end) pair found.
            Empty list if no matching pairs exist.
        """
        tool_calls = self.get_tool_calls()
        results: list[str] = []

        i = 0
        while i < len(tool_calls):
            if tool_calls[i].tool_name != start_tool:
                i += 1
                continue
            # Found start_tool — look for end_tool after it
            start_idx = tool_calls[i].index
            for j in range(i + 1, len(tool_calls)):
                if tool_calls[j].tool_name == end_tool:
                    end_idx = tool_calls[j].index
                    # Extract text from assistant records between these indices
                    text_parts: list[str] = []
                    # Walk raw records and find assistant text between the
                    # record containing start_tool and the one containing end_tool
                    in_range = False
                    for record in self._records:
                        if record.get("type") != "assistant":
                            continue
                        content = record.get("message", {}).get("content")
                        if not isinstance(content, list):
                            continue
                        # Check if this record has tool calls matching our range
                        record_tool_indices = []
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                # Find the index of this tool call
                                block_id = block.get("id")
                                for tc in tool_calls:
                                    if tc.content_block.get("id") == block_id:
                                        record_tool_indices.append(tc.index)
                                        break
                        if any(idx == start_idx for idx in record_tool_indices):
                            in_range = True
                            continue  # Skip the record with start_tool itself
                        if any(idx == end_idx for idx in record_tool_indices):
                            in_range = False
                            break
                        if in_range:
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text = block.get("text", "").strip()
                                    if text:
                                        text_parts.append(text)
                    if text_parts:
                        results.append("\n".join(text_parts))
                    i = j + 1
                    break
            else:
                # No end_tool found after this start_tool
                i += 1

        return results

    def graph_citation_rate(self) -> float | None:
        """Fraction of BSKG queries whose results were cited in conclusions.

        Returns:
            Float between 0.0 and 1.0 when BSKG queries exist.
            None when no BSKG queries were found (not applicable).
        """
        queries = self.get_bskg_queries()
        if not queries:
            return None
        cited = sum(1 for q in queries if q.cited_in_conclusion)
        return cited / len(queries)

    def get_raw_messages(self) -> list[dict[str, Any]]:
        """Return all JSONL records as raw dicts.

        Returns:
            List of raw record dicts in transcript order. Returns a copy
            to prevent mutation of internal state.
        """
        return list(self._records)

    def get_message_at(self, index: int) -> dict[str, Any]:
        """Return a single JSONL record by index.

        Args:
            index: 0-based position in the records list.

        Returns:
            The record dict at the given index.

        Raises:
            IndexError: If index is out of range.
        """
        return self._records[index]

    # --- ObservationSummary extraction (P13-IMP-08 Track A) ---

    def to_observation_summary(self) -> ObservationSummary:
        """Extract a complete ObservationSummary from this transcript.

        This is the PRIMARY evaluation data source. All observation data
        that was previously collected by passive hooks is now extracted
        here from the JSONL transcript directly.

        Returns:
            ObservationSummary with all list-typed fields as [] (never None).
        """
        tool_calls = self.get_tool_calls()
        seq = self.get_tool_sequence()
        counts = dict(Counter(seq))

        # Build tool_sequence_with_timestamps
        tool_sequences: list[ToolSequenceEntry] = [
            ToolSequenceEntry(
                tool_name=tc.tool_name,
                timestamp=tc.timestamp,
                index=tc.index,
            )
            for tc in tool_calls
        ]

        # Extract BSKG query events with node IDs
        bskg_events: list[BSKGQueryEvent] = []
        for tc in tool_calls:
            if tc.tool_name != "Bash":
                continue
            cmd = tc.tool_input.get("command", "")
            if not cmd or "alphaswarm" not in cmd:
                continue
            query_type = self._classify_bskg_query_type(cmd)
            if query_type is None:
                continue
            # Extract BSKG node IDs from tool result
            node_ids: list[str] = []
            result_text = self._get_full_result_for_tool(tc, BSKG_RESULT_TRUNCATE_LEN)
            if result_text:
                node_ids = list(set(_BSKG_NODE_ID_RE.findall(result_text)))
            bskg_events.append(BSKGQueryEvent(
                timestamp=tc.timestamp,
                command=cmd,
                query_type=query_type,
                node_ids=node_ids,
                tool_call_index=tc.index,
            ))

        # Extract tool failures (tool_result with is_error: true)
        tool_failures: list[dict[str, Any]] = []
        for record in self._records:
            if record.get("type") != "user":
                continue
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result" and block.get("is_error", False):
                    tool_failures.append({
                        "tool_use_id": block.get("tool_use_id", ""),
                        "content": str(block.get("content", ""))[:500],
                    })

        # Extract agent lifecycle events (Task tool calls)
        agent_events: list[dict[str, Any]] = []
        for tc in tool_calls:
            if tc.tool_name == "Task":
                agent_events.append({
                    "type": "task_spawn",
                    "index": tc.index,
                    "timestamp": tc.timestamp,
                    "subject": tc.tool_input.get("subject", ""),
                })

        # Extract session_id from first record
        session_id: str | None = None
        for record in self._records:
            sid = record.get("sessionId") or record.get("session_id")
            if sid:
                session_id = str(sid)
                break

        return ObservationSummary(
            tool_counts=counts,
            tool_sequences=tool_sequences,
            bskg_query_events=bskg_events,
            tool_failures=tool_failures,
            agent_lifecycle_events=agent_events,
            total_tool_calls=len(tool_calls),
            session_id=session_id,
        )

    def get_subagent_spawns(self) -> list[SubagentSpawn]:
        """Extract subagent lifecycle from Task tool calls and filesystem.

        Combines two data sources:
        1. Task tool calls in the transcript (spawn events)
        2. Filesystem glob of subagents/agent-*.jsonl (transcript files)

        Returns:
            List of SubagentSpawn with populated fields. Empty list if
            no subagent activity detected.
        """
        tool_calls = self.get_tool_calls()
        spawns: list[SubagentSpawn] = []

        # Extract Task tool calls as spawn events
        task_calls = [tc for tc in tool_calls if tc.tool_name == "Task"]

        # Check for subagent JSONL files relative to main transcript
        subagent_dir = self._path.parent / self._path.stem / "subagents"
        subagent_files: dict[str, Path] = {}
        if subagent_dir.is_dir():
            for f in sorted(subagent_dir.glob("agent-*.jsonl")):
                # Extract agent ID from filename: agent-{id}.jsonl
                agent_id = f.stem  # e.g., "agent-a615e5db9fd8c5fe6"
                subagent_files[agent_id] = f

        # Also check sibling subagents dir (common CC layout):
        # ~/.claude/projects/.../session-id/subagents/agent-*.jsonl
        sibling_subagent_dir = self._path.parent / (self._path.stem.split(".")[0]) / "subagents"
        if sibling_subagent_dir != subagent_dir and sibling_subagent_dir.is_dir():
            for f in sorted(sibling_subagent_dir.glob("agent-*.jsonl")):
                agent_id = f.stem
                if agent_id not in subagent_files:
                    subagent_files[agent_id] = f

        # Build spawns from Task calls
        for idx, tc in enumerate(task_calls):
            subject = tc.tool_input.get("subject", "")
            # Try to extract agent_id from tool result
            agent_id = f"task-{idx}"
            if tc.tool_result:
                # Look for agent ID patterns in result
                match = re.search(r"agent-[a-f0-9]+", tc.tool_result)
                if match:
                    agent_id = match.group(0)

            # Find matching transcript file
            transcript_path: Path | None = None
            tool_count = 0
            if agent_id in subagent_files:
                transcript_path = subagent_files[agent_id]
                # Count tool calls in subagent transcript
                try:
                    with open(transcript_path) as f:
                        for line in f:
                            line_stripped = line.strip()
                            if not line_stripped:
                                continue
                            try:
                                r = json.loads(line_stripped)
                                if r.get("type") == "assistant":
                                    msg = r.get("message", {})
                                    ct = msg.get("content", [])
                                    if isinstance(ct, list):
                                        for b in ct:
                                            if isinstance(b, dict) and b.get("type") == "tool_use":
                                                tool_count += 1
                            except json.JSONDecodeError:
                                continue
                except OSError:
                    pass

            spawns.append(SubagentSpawn(
                agent_id=agent_id,
                task_subject=subject,
                spawn_index=tc.index,
                transcript_path=transcript_path,
                tool_count=tool_count,
            ))

        # Add subagent files not linked to Task calls
        seen_ids = {s.agent_id for s in spawns}
        for agent_id, filepath in subagent_files.items():
            if agent_id not in seen_ids:
                spawns.append(SubagentSpawn(
                    agent_id=agent_id,
                    transcript_path=filepath,
                ))

        return spawns

    def get_messages_between(self, start: int, end: int) -> list[dict[str, Any]]:
        """Return a slice of JSONL records.

        Args:
            start: Start index (inclusive, 0-based).
            end: End index (exclusive).

        Returns:
            List of record dicts in the [start, end) range.
            Returns empty list if start >= end.

        Raises:
            IndexError: If start < 0 or end > record_count.
        """
        if start < 0:
            raise IndexError(f"start index {start} is negative")
        if end > len(self._records):
            raise IndexError(f"end index {end} exceeds record count {len(self._records)}")
        if start >= end:
            return []
        return list(self._records[start:end])
