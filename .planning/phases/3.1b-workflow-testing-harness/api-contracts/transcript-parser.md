# API Contract: Transcript Parser Extensions

**Location:** `tests/workflow_harness/lib/transcript_parser.py`
**3.1b Plan:** 3.1b-02
**3.1c Consumers:** 3.1c-03 (Observation Parser), 3.1c-04 (Graph Value Scorer), 3.1c-05 (Debrief Protocol), 3.1c-07 (Reasoning Evaluator), 3.1c-08 (Evaluation Runner)

## Parse/Execute Boundary

- **3.1b parses:** Extracts tool calls, BSKG queries, raw messages from JSONL transcripts.
- **3.1c executes:** Scores graph query quality, evaluates reasoning between tool calls, runs debrief analysis.

---

## ToolCall Dataclass (Extended)

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ToolCall:
    """A single tool invocation extracted from a transcript.

    Attributes:
        tool_name: Tool identifier (Bash, Read, Grep, Task, Skill, etc.)
        tool_input: Full input parameters dict.
        tool_result: Truncated result string (first 500 chars), None if not yet available.
        index: Position in the sequence of tool calls (0-based).
        timestamp: ISO 8601 timestamp when tool call was made, or None if unavailable.
        duration_ms: Execution duration in milliseconds, or None if unavailable.
        content_block: Raw content block dict from the transcript record. Useful for
            accessing fields not captured in other attributes (e.g., tool_use_id).
    """

    tool_name: str
    tool_input: dict[str, Any] = field(default_factory=dict)
    tool_result: str | None = None
    index: int = 0
    timestamp: str | None = None      # NEW — ISO 8601, e.g. "2026-01-15T10:30:00Z"
    duration_ms: int | None = None     # NEW — milliseconds, computed from pre/post timestamps
    content_block: dict[str, Any] = field(default_factory=dict)  # NEW — raw block for extensibility
```

**Backward compatibility:** `timestamp`, `duration_ms`, and `content_block` all have
defaults (`None`, `None`, `dict()`). Existing code that constructs `ToolCall(tool_name=..., tool_input=..., tool_result=..., index=...)` continues to work unchanged.

**3.1c consumers:**
- 3.1c-03 uses `timestamp` and `duration_ms` for timing distributions.
- 3.1c-04 uses `tool_name` + `tool_input` for graph query identification.
- 3.1c-07 uses the full `ToolCall` in evaluation context.

**Failure modes:**
- `timestamp` is `None` when the transcript record lacks timing metadata (common in older transcripts). Consumers must handle `None`.
- `duration_ms` is `None` when pre/post timestamps are unavailable. Consumers should skip timing analysis for these calls.

---

## BSKGQuery Dataclass (New)

```python
@dataclass
class BSKGQuery:
    """A BSKG/graph query extracted from a Bash tool call.

    Extracted when a Bash tool call's command contains 'alphaswarm' and
    one of: 'query', 'build-kg', 'pattern:'.

    Attributes:
        command: Full shell command string (e.g., "uv run alphaswarm query 'functions without access control'").
        query_type: Classified type — one of "build-kg", "query", "pattern-query".
        query_text: The query string itself, extracted from the command.
            For build-kg: the target path. For query: the NL query text.
            For pattern-query: the pattern expression.
        result_snippet: First 2000 chars of the tool result. Longer than ToolCall.tool_result
            (500 chars) to preserve more graph output context.
        tool_call_index: Position of the originating ToolCall in the transcript (0-based).
        cited_in_conclusion: Heuristic boolean — True if any subsequent Write or SendMessage
            tool call references content from this query's result_snippet. Detection uses
            substring matching on first 200 chars of result_snippet against later tool_input.
    """

    command: str
    query_type: str                     # "build-kg" | "query" | "pattern-query"
    query_text: str
    result_snippet: str                 # First 2000 chars of result
    tool_call_index: int
    cited_in_conclusion: bool = False
```

**Classification heuristic for `query_type`:**
- `"build-kg"`: command contains `"build-kg"`
- `"pattern-query"`: command contains `"pattern:"` after `"query"`
- `"query"`: command contains `"query"` (but not `"build-kg"`)

**`cited_in_conclusion` heuristic:**
1. Take first 200 chars of `result_snippet`.
2. For each subsequent ToolCall where `tool_name in {"Write", "SendMessage"}`:
   - Check if any substring of length >= 20 from the result appears in `json.dumps(tc.tool_input)`.
3. If any match found, `cited_in_conclusion = True`.

**Failure modes:**
- Command doesn't match any known query type: skip (don't create `BSKGQuery`).
- `result_snippet` is empty string when tool call had no result or errored.
- `cited_in_conclusion` is a best-effort heuristic. False negatives are expected when agents paraphrase results. 3.1c-04 uses this as a signal, not ground truth.

---

## TranscriptParser New Methods

```python
class TranscriptParser:
    # --- EXISTING (MUST NOT CHANGE SIGNATURES) ---
    def get_tool_calls(self) -> list[ToolCall]: ...
    def get_tool_sequence(self) -> list[str]: ...
    def get_bash_commands(self) -> list[str]: ...
    def has_tool_call(self, tool_name: str, **input_match: Any) -> bool: ...
    def first_tool_call(self, tool_name: str) -> ToolCall | None: ...
    def tool_calls_matching(self, tool_name: str, **input_match: Any) -> list[ToolCall]: ...
    def has_bskg_query(self) -> bool: ...
    def bskg_query_index(self) -> int | None: ...
    def first_conclusion_index(self) -> int | None: ...
    @property
    def record_count(self) -> int: ...
    @property
    def total_chars(self) -> int: ...
    @property
    def records(self) -> list[dict[str, Any]]:
        """Public read-only access to parsed JSONL records.

        Returns a copy to prevent mutation of internal state. This is the
        stable API for 3.1c-04 (Graph Value Scorer) to read raw records.
        Prefer this over accessing _records directly.
        """
        ...

    # --- NEW METHODS (3.1b-02 implements) ---

    def get_bskg_queries(self) -> list[BSKGQuery]:
        """Extract all BSKG queries from Bash tool calls.

        Scans all Bash tool calls for alphaswarm commands. For each match,
        creates a BSKGQuery with classified type and citation status.

        Returns:
            List of BSKGQuery in transcript order. Empty list if no
            BSKG queries found.
        """
        ...

    def graph_citation_rate(self) -> float | None:
        """Fraction of BSKG queries whose results were cited in conclusions.

        Returns:
            Float between 0.0 and 1.0 when BSKG queries exist.
            None when no BSKG queries were found (not applicable).
            This is a mechanical heuristic — 3.1c-04 uses it as one input
            to the full GraphValueScore.
        """
        ...

    def get_raw_messages(self) -> list[dict[str, Any]]:
        """Return all JSONL records as raw dicts.

        Provides full access to the underlying transcript data for callers
        that need fields not captured in ToolCall (e.g., text blocks between
        tool calls, system messages, progress events).

        Returns:
            List of raw record dicts in transcript order. Same as self._records
            but returned as a copy to prevent mutation.
        """
        ...

    def get_message_at(self, index: int) -> dict[str, Any]:
        """Return a single JSONL record by index.

        Args:
            index: 0-based position in the records list.

        Returns:
            The record dict at the given index.

        Raises:
            IndexError: If index is out of range.
        """
        ...

    def get_messages_between(self, start: int, end: int) -> list[dict[str, Any]]:
        """Return a slice of JSONL records.

        Args:
            start: Start index (inclusive, 0-based).
            end: End index (exclusive).

        Returns:
            List of record dicts in the [start, end) range.
            Returns empty list if start >= end or both out of range.

        Raises:
            IndexError: If start < 0 or end > record_count.
        """
        ...
```

**Backward compatibility:** All new methods are purely additive. No existing method
signature changes. `_records` remains a `list[dict[str, Any]]` attribute.

---

## Example Usage

```python
from pathlib import Path
from tests.workflow_harness.lib.transcript_parser import TranscriptParser, BSKGQuery

parser = TranscriptParser(Path("~/.claude/projects/abc/session.jsonl"))

# Existing usage — unchanged
tool_calls = parser.get_tool_calls()
assert parser.has_bskg_query()

# New: structured BSKG query extraction
queries = parser.get_bskg_queries()
for q in queries:
    print(f"[{q.query_type}] {q.query_text}")
    print(f"  Cited: {q.cited_in_conclusion}")

# New: graph citation rate (0.0 - 1.0)
rate = parser.graph_citation_rate()
print(f"Citation rate: {rate:.1%}")

# New: raw message access for 3.1c-04 text extraction
raw = parser.get_raw_messages()
msg = parser.get_message_at(5)
segment = parser.get_messages_between(3, 8)
```
