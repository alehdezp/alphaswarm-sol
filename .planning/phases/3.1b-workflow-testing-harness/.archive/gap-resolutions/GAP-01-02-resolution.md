# GAP-01 & GAP-02 Resolution: Multi-Agent Observation + Graph Query Extraction

**Date:** 2026-02-12
**Confidence:** HIGH (all designs grounded in verified codebase investigation)

---

## 1. Codebase Investigation Findings

### 1.1 EventStream (controller_events.py)

**File:** `./tests/workflow_harness/lib/controller_events.py`
**LOC:** 160

Key APIs relevant to multi-agent correlation:

| Method | Line | Returns | Use for GAP-01 |
|--------|------|---------|-----------------|
| `agents_spawned()` | L73 | `list[ControllerEvent]` | Enumerate all agents in a team |
| `agents_exited()` | L78 | `list[ControllerEvent]` | Verify clean lifecycle |
| `messages()` | L82 | `list[ControllerEvent]` | Cross-agent DM/broadcast events |
| `agent_by_type(type)` | L105 | `ControllerEvent | None` | Find specific agent (attacker, defender, verifier) |
| `events_for_agent(id)` | L113 | `list[ControllerEvent]` | All events for one agent |
| `events_between(start, end)` | L117 | `list[ControllerEvent]` | Events in a time window |
| `agent_ids()` | L97 | `set[str]` | Unique agent IDs |
| `agent_types()` | L102 | `set[str]` | Unique agent types |

The `ControllerEvent` dataclass (L17-33) has: `event_type`, `timestamp`, `agent_id`, `agent_type`, `data`.

**Key finding:** EventStream already provides the event-level building blocks for multi-agent correlation. What's missing is the *transcript-level* and *message-level* linking that `TeamObservation` would provide.

### 1.2 WorkspaceManager (workspace.py)

**File:** `./tests/workflow_harness/lib/workspace.py`
**LOC:** 222

Key APIs:

| Method | Line | Returns | Notes |
|--------|------|---------|-------|
| `get_transcript_paths(workspace)` | L139 | `dict[str, Path]` | Maps agent_id to JSONL path |
| `get_session_info(workspace)` | L129 | `dict` | Reads `.vrs/testing/session.json` |
| `setup(scenario_dir, extra_hooks)` | L50 | `Path` | Prepares workspace with hooks |

**Key finding:** `get_transcript_paths()` reads from hook-written `session.json` which captures `agent_id` and `agent_transcript_path` per SubagentStop/Stop event. It does NOT capture `agent_type` -- only `agent_id`. The mapping from agent_id to agent_type must come from either the EventStream (`agents_spawned()`) or the team config file.

### 1.3 TranscriptParser (transcript_parser.py)

**File:** `./tests/workflow_harness/lib/transcript_parser.py`
**LOC:** 225

Critical internals:

- `_records: list[dict[str, Any]]` (L57) -- the raw JSONL records. Stable internal attribute per context.md contract.
- `_tool_calls: list[ToolCall] | None` (L58) -- lazy-cached tool extraction.
- `_extract_tool_calls()` (L75-124) -- parses `tool_use` blocks from `assistant` records and matches them to `tool_result` blocks in `user` records via `tool_use_id`.
- `RESULT_TRUNCATE_LEN = 500` (L22) -- tool results are truncated to 500 chars.

**BSKG query detection (L181-199):**
```python
def has_bskg_query(self) -> bool:
    for tc in self.get_tool_calls():
        if tc.tool_name == "Bash":
            cmd = tc.tool_input.get("command", "")
            if "alphaswarm" in cmd and ("query" in cmd or "build-kg" in cmd):
                return True
    return False
```

This is a basic string match. It detects the presence of a query but extracts no structured data about query type, query text, result content, or citation.

**first_conclusion_index (L201-214):** Uses heuristic -- Write or SendMessage calls containing finding/verdict keywords. This is the "conclusion" side of the graph-citation correlation.

### 1.4 ToolCall Dataclass

**File:** `./tests/workflow_harness/lib/transcript_parser.py`
**Lines:** 26-39

```python
@dataclass
class ToolCall:
    tool_name: str
    tool_input: dict[str, Any] = field(default_factory=dict)
    tool_result: str | None = None
    index: int = 0
```

Currently 4 fields. Context.md plan says to add `timestamp` and `duration_ms` in 3.1b-02. GAP-02 needs the `tool_result` field to extract query results -- currently truncated to 500 chars.

### 1.5 Team Inbox File Format (Verified)

**Location:** `~/.claude/teams/{team_name}/inboxes/{agent_name}.json`

**Format:** JSON array of message objects. Each message has:

```json
{
  "from": "team-lead",
  "text": "...",            // Full message content (can be very large)
  "summary": "...",         // Optional, short summary
  "timestamp": "2026-02-08T01:33:46.473Z",  // ISO 8601
  "color": "blue",          // Optional
  "read": true              // Boolean
}
```

**Key findings from real data (`milestone-6-assessment/inboxes/graph-assessor.json`):**
- Messages from both team-lead and the agent itself appear in the agent's inbox.
- Task assignments appear as JSON-encoded strings inside the `text` field (e.g., `{"type":"task_assignment","taskId":"2",...}`).
- Shutdown requests also appear as JSON strings in `text`.
- The `from` field identifies the sender by agent name (not ID).
- No separate `to` field -- the file path determines the recipient.

**Team config:** `~/.claude/teams/{name}/config.json` contains `members[]` with `agentId`, `name`, `agentType`, `model`, `cwd`.

### 1.6 JSONL Transcript Record Format

Based on the docstring in `transcript_parser.py` (L1-11) and the parsing logic:

Records have a `type` field: `"user"`, `"assistant"`, `"progress"`, `"file-history-snapshot"`.

Structure:
```json
{
  "type": "assistant",
  "message": {
    "content": [
      {"type": "text", "text": "...reasoning text..."},
      {"type": "tool_use", "id": "toolu_xxx", "name": "Bash", "input": {"command": "uv run alphaswarm query \"pattern:weak-access-control\""}}
    ]
  }
}
```

Tool results in user records:
```json
{
  "type": "user",
  "message": {
    "content": [
      {"type": "tool_result", "tool_use_id": "toolu_xxx", "content": "...result text or [{\"type\":\"text\",\"text\":\"...\"}]..."}
    ]
  }
}
```

### 1.7 Existing Test Coverage

**File:** `./tests/workflow_harness/test_workspace.py`
**Tests:** 16 tests covering WorkspaceManager (all passing per context.md).

No existing tests for OutputCollector (it doesn't exist yet). No tests for multi-agent observation correlation.

### 1.8 Assertions Module

**File:** `./tests/workflow_harness/lib/assertions.py`
**LOC:** 387, 9 categories.

Relevant: `assert_graph_first()` (L121-136) uses `bskg_query_index()` and `first_conclusion_index()` -- exactly the kind of check that GAP-02's `graph_citation_rate()` would improve.

---

## 2. GAP-01 Resolution: TeamObservation Model

### 2.1 Design Principles

1. **Extend, don't replace** -- `TeamObservation` wraps multiple `AgentObservation` objects. Single-agent scenarios still use `AgentObservation` directly.
2. **Data from two sources** -- Transcripts come from `WorkspaceManager.get_transcript_paths()`. Messages come from inbox files. Events come from `EventStream`.
3. **Lazy loading** -- Parse transcripts and inbox files on demand, not on construction.
4. **No new dependencies** -- Uses existing `TranscriptParser`, `EventStream`, stdlib `json`/`Path`.

### 2.2 Concrete Design

**File:** `tests/workflow_harness/lib/output_collector.py` (NEW, part of 3.1b-02 scope)

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .controller_events import EventStream
from .transcript_parser import TranscriptParser, ToolCall


@dataclass
class InboxMessage:
    """A single message from a team inbox file."""
    sender: str
    text: str
    timestamp: str  # ISO 8601
    summary: str = ""
    read: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> InboxMessage:
        return cls(
            sender=raw.get("from", "unknown"),
            text=raw.get("text", ""),
            timestamp=raw.get("timestamp", ""),
            summary=raw.get("summary", ""),
            read=raw.get("read", False),
        )

    @property
    def is_structured(self) -> bool:
        """True if the text field contains a JSON-encoded structured message."""
        text = self.text.strip()
        return text.startswith("{") and text.endswith("}")

    @property
    def structured_type(self) -> str | None:
        """Extract the 'type' from JSON-encoded text, or None."""
        if not self.is_structured:
            return None
        try:
            return json.loads(self.text).get("type")
        except (json.JSONDecodeError, AttributeError):
            return None


@dataclass
class AgentObservation:
    """Observation data for a single agent in a workflow run.

    Works for both single-agent and multi-agent (team) scenarios.
    """
    agent_id: str
    agent_type: str  # e.g., "attacker", "defender", "verifier", "main"
    transcript_path: Path | None = None

    # Lazy-loaded
    _transcript: TranscriptParser | None = field(default=None, repr=False)
    _inbox_messages: list[InboxMessage] | None = field(default=None, repr=False)

    @property
    def transcript(self) -> TranscriptParser | None:
        """Parse transcript on first access."""
        if self._transcript is None and self.transcript_path and self.transcript_path.exists():
            self._transcript = TranscriptParser(self.transcript_path)
        return self._transcript

    @property
    def tool_calls(self) -> list[ToolCall]:
        """All tool calls from the agent's transcript."""
        t = self.transcript
        return t.get_tool_calls() if t else []

    @property
    def tool_sequence(self) -> list[str]:
        """Ordered tool names from transcript."""
        t = self.transcript
        return t.get_tool_sequence() if t else []

    def load_inbox(self, inbox_path: Path) -> None:
        """Load messages from an inbox JSON file."""
        if not inbox_path.exists():
            self._inbox_messages = []
            return
        try:
            with open(inbox_path) as f:
                raw = json.load(f)
            if isinstance(raw, list):
                self._inbox_messages = [InboxMessage.from_dict(m) for m in raw]
            else:
                self._inbox_messages = []
        except (json.JSONDecodeError, OSError):
            self._inbox_messages = []

    @property
    def inbox_messages(self) -> list[InboxMessage]:
        return self._inbox_messages or []

    @property
    def messages_sent(self) -> list[InboxMessage]:
        """Messages this agent sent (appear in its own inbox with from=self)."""
        return [m for m in self.inbox_messages if m.sender == self.agent_id or m.sender == self.agent_type]

    @property
    def messages_received(self) -> list[InboxMessage]:
        """Messages this agent received from others."""
        return [m for m in self.inbox_messages if m.sender != self.agent_id and m.sender != self.agent_type]

    @property
    def has_bskg_query(self) -> bool:
        t = self.transcript
        return t.has_bskg_query() if t else False


@dataclass
class TeamObservation:
    """Correlated observations across a multi-agent team.

    Links individual AgentObservation objects and provides cross-agent
    analysis methods for evidence chains, agreement depth, and
    coordination patterns.
    """
    team_name: str
    agents: dict[str, AgentObservation] = field(default_factory=dict)  # keyed by agent_type
    event_stream: EventStream | None = None

    @classmethod
    def from_workspace(
        cls,
        team_name: str,
        transcript_paths: dict[str, Path],
        event_stream: EventStream | None = None,
        inbox_dir: Path | None = None,
        agent_type_map: dict[str, str] | None = None,
    ) -> TeamObservation:
        """Build TeamObservation from workspace data.

        Args:
            team_name: Name of the team (used for inbox directory lookup).
            transcript_paths: agent_id -> JSONL path (from WorkspaceManager.get_transcript_paths).
            event_stream: Optional controller EventStream for event-level data.
            inbox_dir: Path to ~/.claude/teams/{name}/inboxes/ (or None to skip inbox loading).
            agent_type_map: Optional agent_id -> agent_type mapping. If not provided,
                tries to infer from EventStream agents_spawned() events.
        """
        # Build agent_id -> agent_type mapping
        type_map = dict(agent_type_map or {})
        if event_stream and not type_map:
            for e in event_stream.agents_spawned():
                if e.agent_id and e.agent_type:
                    type_map[e.agent_id] = e.agent_type

        agents: dict[str, AgentObservation] = {}
        for agent_id, transcript_path in transcript_paths.items():
            agent_type = type_map.get(agent_id, agent_id)  # fallback to ID
            obs = AgentObservation(
                agent_id=agent_id,
                agent_type=agent_type,
                transcript_path=transcript_path,
            )
            # Load inbox if directory provided
            if inbox_dir and inbox_dir.is_dir():
                # Try agent_type.json first (e.g., "attacker.json"), then agent_id.json
                inbox_path = inbox_dir / f"{agent_type}.json"
                if not inbox_path.exists():
                    inbox_path = inbox_dir / f"{agent_id}.json"
                obs.load_inbox(inbox_path)
            agents[agent_type] = obs

        return cls(
            team_name=team_name,
            agents=agents,
            event_stream=event_stream,
        )

    # --- Cross-Agent Analysis Methods ---

    def evidence_chain(self, keyword: str) -> list[tuple[str, str]]:
        """Trace which agents mentioned a keyword and in what order.

        Returns a list of (agent_type, context_snippet) tuples ordered by
        the first appearance in each agent's transcript. This traces how
        a finding or concept flows through the team.

        Args:
            keyword: Term to search for (e.g., "reentrancy", a pattern ID,
                a function name).

        Returns:
            List of (agent_type, snippet) tuples where snippet is the text
            around the first occurrence. Empty list if keyword not found.
        """
        chain: list[tuple[str, str, float]] = []  # (type, snippet, timestamp)

        for agent_type, obs in self.agents.items():
            t = obs.transcript
            if t is None:
                continue
            # Search through raw records for the keyword
            for record in t._records:
                message = record.get("message", {})
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    text = block.get("text", "")
                    if keyword.lower() in text.lower():
                        # Extract a snippet around the keyword
                        idx = text.lower().index(keyword.lower())
                        start = max(0, idx - 80)
                        end = min(len(text), idx + len(keyword) + 80)
                        snippet = text[start:end].strip()
                        # Use record timestamp if available, or 0
                        ts = float(record.get("timestamp", 0))
                        chain.append((agent_type, snippet, ts))
                        break  # First occurrence per record
                    # Also check tool results
                    if block.get("type") == "tool_result":
                        result_text = str(block.get("content", ""))
                        if keyword.lower() in result_text.lower():
                            idx = result_text.lower().index(keyword.lower())
                            start = max(0, idx - 80)
                            end = min(len(result_text), idx + len(keyword) + 80)
                            snippet = result_text[start:end].strip()
                            ts = float(record.get("timestamp", 0))
                            chain.append((agent_type, snippet, ts))
                            break

        # Sort by timestamp, deduplicate by agent_type (keep first)
        chain.sort(key=lambda x: x[2])
        seen: set[str] = set()
        result: list[tuple[str, str]] = []
        for agent_type, snippet, _ in chain:
            if agent_type not in seen:
                seen.add(agent_type)
                result.append((agent_type, snippet))
        return result

    def agreement_depth(self) -> float:
        """How many rounds of genuine debate occurred before convergence.

        Measures agreement depth by counting cross-agent message exchanges
        that contain substantive content (not just task assignments or
        shutdown requests).

        Returns:
            A float representing the number of substantive cross-agent
            message exchanges per agent pair. Higher = more genuine debate.
            Returns 0.0 if no messages or single agent.
        """
        if len(self.agents) < 2:
            return 0.0

        # Count substantive messages across all agents
        substantive_count = 0
        for obs in self.agents.values():
            for msg in obs.inbox_messages:
                # Skip structured protocol messages (task assignments, shutdowns)
                if msg.is_structured and msg.structured_type in (
                    "task_assignment", "shutdown_request", "shutdown_response",
                    "idle_notification", "plan_approval_request", "plan_approval_response",
                ):
                    continue
                # Skip very short messages (acknowledgments)
                if len(msg.text) < 50:
                    continue
                substantive_count += 1

        # Normalize by number of agent pairs
        n = len(self.agents)
        pair_count = n * (n - 1) / 2  # combinations of 2
        if pair_count == 0:
            return 0.0

        return substantive_count / pair_count

    def message_flow(self) -> list[dict[str, str]]:
        """Ordered list of cross-agent messages for visualization.

        Returns dicts with: sender, recipient, summary, timestamp, type.
        Sorted by timestamp.
        """
        messages: list[dict[str, Any]] = []
        for agent_type, obs in self.agents.items():
            for msg in obs.inbox_messages:
                messages.append({
                    "recipient": agent_type,
                    "sender": msg.sender,
                    "summary": msg.summary or msg.text[:100],
                    "timestamp": msg.timestamp,
                    "type": msg.structured_type or "text",
                })
        messages.sort(key=lambda m: m.get("timestamp", ""))
        return messages

    def per_agent_graph_usage(self) -> dict[str, bool]:
        """Which agents used BSKG queries."""
        return {
            agent_type: obs.has_bskg_query
            for agent_type, obs in self.agents.items()
        }

    # --- Backward Compatibility ---

    @classmethod
    def single_agent(cls, agent_id: str, transcript_path: Path) -> TeamObservation:
        """Create a TeamObservation for a single-agent scenario.

        This preserves backward compatibility: single-agent scenarios
        produce a TeamObservation with one agent keyed as "main".
        """
        obs = AgentObservation(
            agent_id=agent_id,
            agent_type="main",
            transcript_path=transcript_path,
        )
        return cls(team_name="single", agents={"main": obs})
```

### 2.3 Integration with OutputCollector

The `OutputCollector.collect()` method detects team vs single-agent and returns the appropriate model:

```python
class OutputCollector:
    """Collects all observable output from a scenario run."""

    def __init__(self, workspace_manager: WorkspaceManager) -> None:
        self._mgr = workspace_manager

    def collect(
        self,
        workspace: Path,
        session_id: str,
        event_stream: EventStream | None = None,
        team_name: str | None = None,
    ) -> CollectedOutput:
        """Gather transcripts, output files, and build observation model.

        Auto-detects team vs single-agent based on transcript count.
        """
        transcript_paths = self._mgr.get_transcript_paths(workspace)

        # Build observation model
        if len(transcript_paths) > 1 or team_name:
            # Multi-agent: build TeamObservation
            inbox_dir = None
            if team_name:
                inbox_dir = Path.home() / ".claude" / "teams" / team_name / "inboxes"
            observation = TeamObservation.from_workspace(
                team_name=team_name or "unknown",
                transcript_paths=transcript_paths,
                event_stream=event_stream,
                inbox_dir=inbox_dir,
            )
        elif transcript_paths:
            # Single agent: wrap in TeamObservation.single_agent
            agent_id, path = next(iter(transcript_paths.items()))
            observation = TeamObservation.single_agent(agent_id, path)
        else:
            observation = TeamObservation(team_name="empty")

        return CollectedOutput(
            workspace=workspace,
            session_id=session_id,
            observation=observation,
            event_stream=event_stream,
            # ... other collected artifacts
        )


@dataclass
class CollectedOutput:
    """Everything collected from a scenario run."""
    workspace: Path
    session_id: str
    observation: TeamObservation
    event_stream: EventStream | None = None
    output_files: list[Path] = field(default_factory=list)
    hook_observations: list[Path] = field(default_factory=list)

    @property
    def is_team(self) -> bool:
        return len(self.observation.agents) > 1

    def summary(self) -> str:
        """Human-readable overview for evaluator reasoning."""
        lines = [
            f"Session: {self.session_id}",
            f"Workspace: {self.workspace}",
            f"Agents: {len(self.observation.agents)} ({', '.join(self.observation.agents.keys())})",
        ]
        for agent_type, obs in self.observation.agents.items():
            t = obs.transcript
            lines.append(f"\n--- {agent_type} ---")
            lines.append(f"  Transcript: {obs.transcript_path}")
            if t:
                lines.append(f"  Records: {t.record_count}")
                lines.append(f"  Tool calls: {len(t.get_tool_calls())}")
                lines.append(f"  BSKG query: {t.has_bskg_query()}")
            lines.append(f"  Inbox messages: {len(obs.inbox_messages)}")
        if self.observation.agents:
            lines.append(f"\nAgreement depth: {self.observation.agreement_depth():.2f}")
            graph_usage = self.observation.per_agent_graph_usage()
            lines.append(f"Graph usage: {graph_usage}")
        return "\n".join(lines)
```

---

## 3. GAP-02 Resolution: BSKGQuery Structured Extraction

### 3.1 Design Principles

1. **Parse from existing ToolCall data** -- query text comes from `tool_input["command"]`, results from `tool_result`.
2. **Query type classification** by prefix/pattern: `pattern:`, natural language, property queries.
3. **Citation detection** by searching subsequent text blocks for terms from the query result.
4. **500-char truncation awareness** -- `tool_result` is already truncated; `cited_in_conclusion` uses what's available.
5. **All new methods on TranscriptParser** -- no new classes needed beyond the `BSKGQuery` dataclass.

### 3.2 Concrete Design

**Added to:** `tests/workflow_harness/lib/transcript_parser.py`

```python
import re


@dataclass
class BSKGQuery:
    """A structured BSKG query extracted from a transcript.

    Attributes:
        command: The full Bash command string (e.g., 'uv run alphaswarm query "pattern:..."')
        query_text: The extracted query string (e.g., 'pattern:weak-access-control')
        query_type: Classification: "pattern", "nl" (natural language), "build-kg", "property"
        tool_call_index: Position of this Bash call in the tool call sequence
        result_snippet: First 500 chars of the command output (from tool_result)
        result_node_count: Number of graph nodes returned, if parseable from result
        cited_in_conclusion: Whether terms from the result appear in subsequent reasoning text
    """
    command: str
    query_text: str
    query_type: str  # "pattern" | "nl" | "build-kg" | "property"
    tool_call_index: int
    result_snippet: str = ""
    result_node_count: int = -1  # -1 = not parseable
    cited_in_conclusion: bool = False


# --- Query type classification ---

_PATTERN_QUERY_RE = re.compile(r"""["']pattern:([^"']+)["']""")
_PROPERTY_QUERY_RE = re.compile(r"""["']property:([^"']+)["']""")
# Match the query argument from: alphaswarm query "..."
_QUERY_ARG_RE = re.compile(r'alphaswarm\s+query\s+["\']([^"\']+)["\']')
# Match node count patterns in results like "Found 5 nodes" or "3 results"
_NODE_COUNT_RE = re.compile(r'(?:Found|Returned|Results?:?)\s*(\d+)\s*(?:nodes?|results?|matches?|functions?)', re.IGNORECASE)


class TranscriptParser:
    # ... existing methods preserved ...

    def get_bskg_queries(self) -> list[BSKGQuery]:
        """Extract all BSKG/graph queries with structured metadata.

        Parses Bash tool calls containing 'alphaswarm query' or 'alphaswarm build-kg'
        and classifies them by query type. Determines whether results were cited
        in subsequent reasoning text.

        Returns:
            List of BSKGQuery objects in order of invocation.
        """
        queries: list[BSKGQuery] = []
        all_calls = self.get_tool_calls()

        for tc in all_calls:
            if tc.tool_name != "Bash":
                continue
            cmd = tc.tool_input.get("command", "")
            if "alphaswarm" not in cmd:
                continue
            if "query" not in cmd and "build-kg" not in cmd:
                continue

            # Classify query type
            query_text, query_type = self._classify_query(cmd)

            # Extract result info
            result_snippet = tc.tool_result or ""
            node_count = self._parse_node_count(result_snippet)

            # Check citation: search text blocks AFTER this tool call
            # for terms from the result
            cited = self._check_citation(tc.index, result_snippet, all_calls)

            queries.append(BSKGQuery(
                command=cmd,
                query_text=query_text,
                query_type=query_type,
                tool_call_index=tc.index,
                result_snippet=result_snippet,
                result_node_count=node_count,
                cited_in_conclusion=cited,
            ))

        return queries

    def _classify_query(self, cmd: str) -> tuple[str, str]:
        """Classify a command into (query_text, query_type)."""
        if "build-kg" in cmd:
            return cmd.strip(), "build-kg"

        # Try pattern query
        m = _PATTERN_QUERY_RE.search(cmd)
        if m:
            return f"pattern:{m.group(1)}", "pattern"

        # Try property query
        m = _PROPERTY_QUERY_RE.search(cmd)
        if m:
            return f"property:{m.group(1)}", "property"

        # Try generic query argument extraction
        m = _QUERY_ARG_RE.search(cmd)
        if m:
            return m.group(1), "nl"  # Natural language query

        return cmd.strip(), "nl"  # Fallback

    def _parse_node_count(self, result: str) -> int:
        """Try to extract a node count from query results."""
        if not result:
            return -1
        m = _NODE_COUNT_RE.search(result)
        if m:
            return int(m.group(1))
        return -1

    def _check_citation(
        self, query_index: int, result_snippet: str, all_calls: list[ToolCall]
    ) -> bool:
        """Check if terms from the query result appear in subsequent reasoning.

        Searches text blocks in assistant records that appear AFTER the query's
        tool result for distinctive terms from the result.
        """
        if not result_snippet or len(result_snippet) < 20:
            return False

        # Extract distinctive terms from result (words > 5 chars, not common)
        common_words = {
            "function", "contract", "returns", "public", "private",
            "internal", "external", "modifier", "require", "assert",
            "string", "uint256", "address", "memory", "storage",
            "mapping", "struct", "event", "error", "import",
            "pragma", "solidity", "result", "found", "query",
        }
        result_lower = result_snippet.lower()
        words = set(re.findall(r'\b[a-zA-Z_]\w{5,}\b', result_lower))
        distinctive = words - common_words
        if not distinctive:
            return False

        # Get text AFTER this tool call from subsequent records
        subsequent_text = self._get_text_after_tool(query_index)
        if not subsequent_text:
            return False

        subsequent_lower = subsequent_text.lower()
        # Citation if >= 2 distinctive terms from result appear in subsequent text
        cited_count = sum(1 for term in distinctive if term in subsequent_lower)
        return cited_count >= 2

    def _get_text_after_tool(self, tool_index: int) -> str:
        """Extract assistant text blocks that appear after a given tool call index.

        Walks through _records after the tool result for the given index,
        collecting text blocks from assistant messages.
        """
        all_calls = self.get_tool_calls()
        if tool_index >= len(all_calls):
            return ""

        # Find the record index where the tool result appears
        target_id = None
        for record in self._records:
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            if record.get("type") == "assistant":
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        if block.get("name") == all_calls[tool_index].tool_name:
                            target_id = block.get("id")

        # Now collect text after the tool result
        past_result = False
        texts: list[str] = []
        for record in self._records:
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue

            if not past_result:
                # Look for the tool_result matching our tool
                if record.get("type") == "user":
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            if block.get("tool_use_id") == target_id:
                                past_result = True
                continue

            # Collect text from assistant messages after the tool result
            if record.get("type") == "assistant":
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))

        return "\n".join(texts)

    def get_text_between_tools(self, start_idx: int, end_idx: int) -> str:
        """Extract reasoning text between two tool call indices.

        Returns the concatenated text blocks from assistant records that
        appear between the tool_result of start_idx and the tool_use of end_idx.

        Args:
            start_idx: Index of the first tool call (text starts AFTER its result).
            end_idx: Index of the second tool call (text ends BEFORE its use).

        Returns:
            Concatenated text. Empty string if indices are invalid or no text found.
        """
        all_calls = self.get_tool_calls()
        if start_idx < 0 or end_idx >= len(all_calls) or start_idx >= end_idx:
            return ""

        # Find tool_use IDs for boundary matching
        start_call = all_calls[start_idx]
        end_call = all_calls[end_idx]

        # Walk records to find boundaries
        start_tool_id = None
        end_tool_id = None
        for record in self._records:
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            if record.get("type") == "assistant":
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        bid = block.get("id", "")
                        name = block.get("name", "")
                        inp = block.get("input", {})
                        # Match by index position in our tool call list
                        if name == start_call.tool_name and start_tool_id is None:
                            # Verify by checking if this is the Nth occurrence
                            start_tool_id = bid
                        if name == end_call.tool_name and bid != start_tool_id:
                            end_tool_id = bid

        if not start_tool_id:
            return ""

        # Collect text between start_tool_result and end_tool_use
        past_start = False
        texts: list[str] = []
        for record in self._records:
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue

            if not past_start:
                if record.get("type") == "user":
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            if block.get("tool_use_id") == start_tool_id:
                                past_start = True
                continue

            # Check if we've hit the end boundary
            if record.get("type") == "assistant":
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "tool_use" and block.get("id") == end_tool_id:
                            return "\n".join(texts)
                        if block.get("type") == "text":
                            texts.append(block.get("text", ""))

        return "\n".join(texts)

    def graph_citation_rate(self) -> float:
        """Fraction of BSKG queries whose results are cited in subsequent text.

        Returns 0.0 if no BSKG queries exist. A score of 1.0 means all
        query results were cited in subsequent reasoning.

        This is the key metric for distinguishing genuine graph usage
        (score > 0.5) from checkbox compliance (score < 0.3).
        """
        queries = self.get_bskg_queries()
        if not queries:
            return 0.0
        cited = sum(1 for q in queries if q.cited_in_conclusion)
        return cited / len(queries)
```

### 3.3 Implementation Notes

**Tool ID matching strategy:** The `_get_text_after_tool` and `get_text_between_tools` methods need to match tool calls to their positions in `_records`. The current `_extract_tool_calls()` method uses `block.get("id")` to create an `id_to_call` mapping (L102-103). The new methods should use the same ID-based matching rather than trying to match by name+input (which could be ambiguous).

**Refinement for production:** The `_check_citation` implementation above uses a heuristic (>=2 distinctive terms from result appear in subsequent text). This is a reasonable starting point but may need tuning based on real transcript data. The `common_words` set should be expanded based on actual Solidity transcript vocabulary.

**RESULT_TRUNCATE_LEN impact:** Since tool results are truncated to 500 chars (L22), `cited_in_conclusion` can only check against the first 500 chars of query output. For queries returning large result sets, this may miss citations of results that appeared after truncation. Mitigation: increase `RESULT_TRUNCATE_LEN` for BSKG queries specifically, or store full results when query type is detected.

**Recommended RESULT_TRUNCATE_LEN change:** Increase from 500 to 2000 for BSKG query results only:

```python
# In _extract_tool_calls(), after creating the ToolCall:
if tc.tool_name == "Bash" and "alphaswarm" in tc.tool_input.get("command", ""):
    # Use larger truncation for graph queries
    id_to_call[tool_id].tool_result = result_str[:2000]
else:
    id_to_call[tool_id].tool_result = result_str[:RESULT_TRUNCATE_LEN]
```

---

## 4. Integration Plan: Fitting into 3.1b-02

### 4.1 What 3.1b-02 Currently Covers (from context.md)

- Part A: TranscriptParser extensions (2 new ToolCall fields, 3 new methods)
- Part B: OutputCollector (NEW)

### 4.2 GAP-01/02 Additions to 3.1b-02 Scope

| Addition | Part | Effort | Rationale |
|----------|------|--------|-----------|
| `BSKGQuery` dataclass | A (parser) | Small | 7-field dataclass, ~15 LOC |
| `get_bskg_queries()` | A (parser) | Medium | Core extraction logic, ~40 LOC |
| `_classify_query()` | A (parser) | Small | Regex-based classification, ~20 LOC |
| `_parse_node_count()` | A (parser) | Small | Single regex, ~8 LOC |
| `_check_citation()` | A (parser) | Medium | Heuristic citation detection, ~30 LOC |
| `_get_text_after_tool()` | A (parser) | Medium | Record traversal, ~35 LOC |
| `get_text_between_tools()` | A (parser) | Medium | Record traversal, ~40 LOC |
| `graph_citation_rate()` | A (parser) | Small | Aggregation over queries, ~8 LOC |
| `InboxMessage` dataclass | B (collector) | Small | 6-field dataclass, ~30 LOC |
| `AgentObservation` dataclass | B (collector) | Medium | Per-agent wrapper, ~60 LOC |
| `TeamObservation` class | B (collector) | Medium | Cross-agent correlation, ~120 LOC |
| `OutputCollector` updates | B (collector) | Small | Team detection logic, ~30 LOC |
| `CollectedOutput` dataclass | B (collector) | Small | Container + summary, ~40 LOC |

**Total addition:** ~480 LOC across parser and collector.

### 4.3 Modified Scope Summary

**3.1b-02 Part A (TranscriptParser):**
- Original: 2 new ToolCall fields (`timestamp`, `duration_ms`), 3 new methods (`get_raw_messages`, `get_message_at`, `get_messages_between`)
- Added (GAP-02): `BSKGQuery` dataclass, `get_bskg_queries()`, `get_text_between_tools()`, `graph_citation_rate()`, plus 3 private helper methods

**3.1b-02 Part B (OutputCollector):**
- Original: `OutputCollector.collect()` and `CollectedOutput`
- Added (GAP-01): `InboxMessage`, `AgentObservation`, `TeamObservation`, auto-detection of team vs single-agent

### 4.4 Files Modified

| File | Action | GAP |
|------|--------|-----|
| `tests/workflow_harness/lib/transcript_parser.py` | Add BSKGQuery, 3 public methods, 3 private helpers | GAP-02 |
| `tests/workflow_harness/lib/output_collector.py` | NEW: InboxMessage, AgentObservation, TeamObservation, OutputCollector, CollectedOutput | GAP-01 |
| `tests/workflow_harness/lib/__init__.py` | Export new classes | Both |
| `tests/workflow_harness/test_transcript_parser.py` | New tests for BSKG extraction | GAP-02 |
| `tests/workflow_harness/test_output_collector.py` | New tests for team observation | GAP-01 |

---

## 5. Test Strategy

### 5.1 GAP-01 Tests (TeamObservation)

**Fixture: 2-agent team with cross-agent messages**

Create a fixture directory with:
- Two JSONL transcripts (attacker.jsonl, verifier.jsonl)
- Two inbox files (attacker.json, verifier.json)
- An EventStream with agent:spawned events for both

```python
# tests/workflow_harness/test_output_collector.py

class TestTeamObservation:

    @pytest.fixture
    def team_fixture(self, tmp_path: Path) -> dict:
        """Create a 2-agent team fixture with transcripts and inbox."""
        # Attacker transcript: runs alphaswarm query, finds reentrancy
        attacker_jsonl = tmp_path / "attacker.jsonl"
        attacker_jsonl.write_text("\n".join([
            json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "text", "text": "I will query the graph for reentrancy patterns."},
                    {"type": "tool_use", "id": "t1", "name": "Bash",
                     "input": {"command": 'uv run alphaswarm query "pattern:reentrancy-001"'}}
                ]}
            }),
            json.dumps({
                "type": "user",
                "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "t1",
                     "content": "Found 3 nodes matching pattern:reentrancy-001\nNode: withdraw() at line 45"}
                ]}
            }),
            json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "text", "text": "The graph shows withdraw() has reentrancy. Sending finding to verifier."},
                    {"type": "tool_use", "id": "t2", "name": "SendMessage",
                     "input": {"recipient": "verifier", "content": "Found reentrancy in withdraw() at line 45"}}
                ]}
            }),
        ]))

        # Verifier transcript: receives finding, evaluates
        verifier_jsonl = tmp_path / "verifier.jsonl"
        verifier_jsonl.write_text("\n".join([
            json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "text", "text": "Evaluating reentrancy finding in withdraw(). Checking for guards."},
                    {"type": "tool_use", "id": "v1", "name": "Bash",
                     "input": {"command": 'uv run alphaswarm query "functions with reentrancy guards"'}}
                ]}
            }),
            json.dumps({
                "type": "user",
                "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "v1",
                     "content": "Found 0 nodes with reentrancy guards in withdraw()"}
                ]}
            }),
            json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "text", "text": "Confirmed: withdraw() has no reentrancy guard. Verdict: VULNERABLE."}
                ]}
            }),
        ]))

        # Inbox files
        inbox_dir = tmp_path / "inboxes"
        inbox_dir.mkdir()
        (inbox_dir / "attacker.json").write_text(json.dumps([
            {"from": "team-lead", "text": "Investigate reentrancy in VulnerableVault.sol",
             "timestamp": "2026-02-12T10:00:00Z", "read": True},
        ]))
        (inbox_dir / "verifier.json").write_text(json.dumps([
            {"from": "attacker", "text": "Found reentrancy in withdraw() at line 45. Evidence: graph node N123.",
             "timestamp": "2026-02-12T10:01:00Z", "read": True},
            {"from": "team-lead", "text": "Please verify the attacker's reentrancy finding.",
             "timestamp": "2026-02-12T10:00:30Z", "read": True},
        ]))

        # EventStream data
        events = [
            {"type": "agent:spawned", "agent_id": "a1", "agent_type": "attacker", "timestamp": 1000},
            {"type": "agent:spawned", "agent_id": "a2", "agent_type": "verifier", "timestamp": 1001},
            {"type": "agent:exited", "agent_id": "a1", "agent_type": "attacker", "timestamp": 1100},
            {"type": "agent:exited", "agent_id": "a2", "agent_type": "verifier", "timestamp": 1110},
        ]

        return {
            "transcript_paths": {"a1": attacker_jsonl, "a2": verifier_jsonl},
            "inbox_dir": inbox_dir,
            "events": events,
        }

    def test_from_workspace_creates_agents(self, team_fixture):
        stream = EventStream(team_fixture["events"])
        team = TeamObservation.from_workspace(
            team_name="test-team",
            transcript_paths=team_fixture["transcript_paths"],
            event_stream=stream,
            inbox_dir=team_fixture["inbox_dir"],
        )
        assert "attacker" in team.agents
        assert "verifier" in team.agents
        assert len(team.agents) == 2

    def test_evidence_chain_traces_keyword(self, team_fixture):
        stream = EventStream(team_fixture["events"])
        team = TeamObservation.from_workspace(
            team_name="test-team",
            transcript_paths=team_fixture["transcript_paths"],
            event_stream=stream,
        )
        chain = team.evidence_chain("reentrancy")
        # Both agents mention reentrancy
        agent_types = [c[0] for c in chain]
        assert "attacker" in agent_types
        assert "verifier" in agent_types

    def test_evidence_chain_empty_for_unknown_keyword(self, team_fixture):
        stream = EventStream(team_fixture["events"])
        team = TeamObservation.from_workspace(
            team_name="test-team",
            transcript_paths=team_fixture["transcript_paths"],
            event_stream=stream,
        )
        chain = team.evidence_chain("nonexistent-keyword-xyz")
        assert chain == []

    def test_agreement_depth_nonzero_with_messages(self, team_fixture):
        stream = EventStream(team_fixture["events"])
        team = TeamObservation.from_workspace(
            team_name="test-team",
            transcript_paths=team_fixture["transcript_paths"],
            event_stream=stream,
            inbox_dir=team_fixture["inbox_dir"],
        )
        depth = team.agreement_depth()
        assert depth > 0.0  # Has substantive messages

    def test_agreement_depth_zero_for_single_agent(self, tmp_path):
        jsonl = tmp_path / "main.jsonl"
        jsonl.write_text('{"type": "assistant", "message": {"content": []}}\n')
        team = TeamObservation.single_agent("main-id", jsonl)
        assert team.agreement_depth() == 0.0

    def test_per_agent_graph_usage(self, team_fixture):
        stream = EventStream(team_fixture["events"])
        team = TeamObservation.from_workspace(
            team_name="test-team",
            transcript_paths=team_fixture["transcript_paths"],
            event_stream=stream,
        )
        usage = team.per_agent_graph_usage()
        assert usage["attacker"] is True
        assert usage["verifier"] is True

    def test_single_agent_backward_compat(self, tmp_path):
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text("\n".join([
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "x1", "name": "Bash", "input": {"command": "echo hello"}}
            ]}}),
        ]))
        team = TeamObservation.single_agent("sess-123", jsonl)
        assert "main" in team.agents
        assert team.agents["main"].tool_calls[0].tool_name == "Bash"
        assert team.team_name == "single"

    def test_message_flow_ordered(self, team_fixture):
        stream = EventStream(team_fixture["events"])
        team = TeamObservation.from_workspace(
            team_name="test-team",
            transcript_paths=team_fixture["transcript_paths"],
            event_stream=stream,
            inbox_dir=team_fixture["inbox_dir"],
        )
        flow = team.message_flow()
        assert len(flow) > 0
        # Messages should be sorted by timestamp
        timestamps = [m["timestamp"] for m in flow]
        assert timestamps == sorted(timestamps)
```

### 5.2 GAP-02 Tests (BSKGQuery Extraction)

```python
# tests/workflow_harness/test_transcript_bskg.py

class TestBSKGQueryExtraction:

    def _make_parser(self, records: list[dict], tmp_path: Path) -> TranscriptParser:
        """Helper: write records to JSONL and create parser."""
        jsonl = tmp_path / "test.jsonl"
        jsonl.write_text("\n".join(json.dumps(r) for r in records))
        return TranscriptParser(jsonl)

    def test_pattern_query_classified(self, tmp_path):
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "pattern:weak-access-control"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": "Found 5 nodes matching pattern:weak-access-control"}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        queries = parser.get_bskg_queries()
        assert len(queries) == 1
        assert queries[0].query_type == "pattern"
        assert queries[0].query_text == "pattern:weak-access-control"

    def test_nl_query_classified(self, tmp_path):
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "functions without access control"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "Found 2 results"}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        queries = parser.get_bskg_queries()
        assert len(queries) == 1
        assert queries[0].query_type == "nl"
        assert queries[0].query_text == "functions without access control"

    def test_build_kg_classified(self, tmp_path):
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "uv run alphaswarm build-kg contracts/"}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "Built graph with 42 nodes"}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        queries = parser.get_bskg_queries()
        assert len(queries) == 1
        assert queries[0].query_type == "build-kg"

    def test_no_queries_returns_empty(self, tmp_path):
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "ls -la"}}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        assert parser.get_bskg_queries() == []

    def test_cited_in_conclusion_true(self, tmp_path):
        """Query result terms appear in subsequent reasoning text."""
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "pattern:reentrancy-001"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": "Found 3 nodes matching reentrancy-001\nNode: withdrawFunds() at VulnerableVault.sol:45\nBehavior: TRANSFERS_VALUE_OUT before WRITES_USER_BALANCE"}
            ]}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "The graph reveals that withdrawFunds() in VulnerableVault performs TRANSFERS_VALUE_OUT before WRITES_USER_BALANCE, confirming the classic reentrancy pattern."}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        queries = parser.get_bskg_queries()
        assert len(queries) == 1
        assert queries[0].cited_in_conclusion is True

    def test_cited_in_conclusion_false(self, tmp_path):
        """Query runs but result is completely ignored in subsequent text."""
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "pattern:reentrancy-001"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": "Found 3 nodes matching reentrancy-001\nNode: withdrawFunds() at VulnerableVault.sol:45"}
            ]}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "Based on my general knowledge of Solidity, I believe there might be issues with this contract. Let me write up my findings."}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        queries = parser.get_bskg_queries()
        assert len(queries) == 1
        assert queries[0].cited_in_conclusion is False

    def test_graph_citation_rate_all_cited(self, tmp_path):
        records = [
            # Query 1 - cited
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "pattern:reentrancy-001"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": "Found withdrawFunds with TRANSFERS_VALUE_OUT before WRITES_USER_BALANCE pattern"}
            ]}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "The withdrawFunds function shows TRANSFERS_VALUE_OUT occurring before the balance update."}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        rate = parser.graph_citation_rate()
        assert rate == 1.0

    def test_graph_citation_rate_zero_for_no_queries(self, tmp_path):
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "No graph queries here."}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        assert parser.graph_citation_rate() == 0.0

    def test_graph_citation_rate_checkbox_compliance(self, tmp_path):
        """Low rate: queries run but results ignored."""
        records = [
            # Query 1 - not cited
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "pattern:reentrancy-001"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": "Found withdrawFunds with TRANSFERS_VALUE_OUT pattern in VulnerableVault"}
            ]}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "I think this contract might have some issues. Let me continue analysis."}
            ]}},
            # Query 2 - not cited
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t2", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "functions without access control"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t2",
                 "content": "Found setOwner and changeAdmin functions missing onlyOwner modifier"}
            ]}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "After careful consideration, there are vulnerabilities in this code."}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        rate = parser.graph_citation_rate()
        assert rate < 0.3  # Checkbox compliance: queries run but ignored

    def test_result_node_count_parsed(self, tmp_path):
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "pattern:reentrancy-001"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": "Found 5 nodes matching pattern:reentrancy-001"}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        queries = parser.get_bskg_queries()
        assert queries[0].result_node_count == 5

    def test_get_text_between_tools(self, tmp_path):
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "uv run alphaswarm build-kg contracts/"}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "Built 42 nodes"}
            ]}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "The graph is built. Now I will query for vulnerabilities."}
            ]}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t2", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "pattern:reentrancy"'}}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        text = parser.get_text_between_tools(0, 1)
        assert "graph is built" in text
        assert "query for vulnerabilities" in text

    def test_multiple_queries_extracted(self, tmp_path):
        records = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "uv run alphaswarm build-kg contracts/"}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "Built graph"}
            ]}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t2", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "pattern:reentrancy-001"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t2", "content": "Found 3 nodes"}
            ]}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t3", "name": "Bash",
                 "input": {"command": 'uv run alphaswarm query "property:has-external-call"'}}
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t3", "content": "Found 2 nodes"}
            ]}},
        ]
        parser = self._make_parser(records, tmp_path)
        queries = parser.get_bskg_queries()
        assert len(queries) == 3
        assert queries[0].query_type == "build-kg"
        assert queries[1].query_type == "pattern"
        assert queries[2].query_type == "property"
```

### 5.3 Fixture Data Strategy

| Fixture | Purpose | Agent Count | Has BSKG | Has Messages |
|---------|---------|-------------|----------|--------------|
| `single_agent_health_check` | Backward compat | 1 | No | No |
| `single_agent_with_graph` | GAP-02 basic | 1 | Yes (2 queries) | No |
| `two_agent_debate` | GAP-01 core | 2 (attacker, verifier) | Yes (both agents) | Yes (finding + verdict) |
| `checkbox_compliance` | GAP-02 scoring | 1 | Yes (queries run, results ignored) | No |
| `genuine_graph_use` | GAP-02 scoring | 1 | Yes (queries run, results cited) | No |
| `empty_transcript` | Edge case | 0 | No | No |

All fixtures use synthetic JSONL data following the verified record format from section 1.6. No real transcript files are required (avoiding privacy/size issues).

---

## 6. Risk Assessment

### 6.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| `_records` internal attribute changes in future refactor | HIGH -- breaks all `_get_text_after_tool` and `evidence_chain` methods | LOW -- context.md explicitly contracts `_records` as stable | Document dependency; add API_VERSION check |
| Tool result truncation (500 chars) misses citation evidence | MEDIUM -- false negatives on `cited_in_conclusion` | MEDIUM -- queries often return >500 chars | Increase to 2000 for BSKG queries; document limitation |
| Inbox file format changes across Claude Code versions | MEDIUM -- `InboxMessage.from_dict` breaks | LOW -- JSON schema has been stable across observed versions | Defensive parsing with `.get()` defaults |
| `_check_citation` heuristic too loose or too strict | MEDIUM -- inaccurate graph_citation_rate | MEDIUM -- tuning needed against real data | Start conservative (>=2 terms); make threshold configurable |
| Record timestamp field not always present | LOW -- `evidence_chain` ordering degrades | MEDIUM -- some records lack timestamps | Fall back to record order when timestamps are 0 |

### 6.2 Design Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| `TeamObservation.from_workspace` requires `agent_type_map` when EventStream unavailable | LOW -- fallback uses agent_id as type | Document: pass explicit map when EventStream is not available |
| Large inbox files (50KB+) loaded fully into memory | LOW -- we only load per-agent files | Acceptable: largest observed is 50KB |
| `get_text_between_tools` index matching by tool name is fragile when multiple calls to same tool | MEDIUM | Use tool_use_id tracking internally (already available in `_extract_tool_calls`) |

### 6.3 Dependencies

| Dependency | Status | Risk |
|------------|--------|------|
| `TranscriptParser._records` stability | Contracted in context.md | LOW |
| `WorkspaceManager.get_transcript_paths()` | Exists, tested | NONE |
| `EventStream.agents_spawned()` | Exists, tested | NONE |
| Inbox file at `~/.claude/teams/{name}/inboxes/` | Verified empirically | LOW |
| `ToolCall.tool_result` populated | Exists in current implementation | NONE |

### 6.4 Confidence Assessment

| Component | Confidence | Rationale |
|-----------|------------|-----------|
| `AgentObservation` design | HIGH | Simple wrapper over verified APIs |
| `TeamObservation.from_workspace` | HIGH | Uses existing `get_transcript_paths` + `EventStream` |
| `TeamObservation.evidence_chain` | MEDIUM | Record traversal logic is correct but may need tuning for edge cases |
| `TeamObservation.agreement_depth` | MEDIUM | Heuristic; substantive message threshold (50 chars, skip structured) needs validation |
| `BSKGQuery` extraction | HIGH | Regex patterns match known command formats |
| `_classify_query` | HIGH | Well-defined prefix patterns |
| `_check_citation` | MEDIUM | Heuristic approach; threshold needs real-data tuning |
| `graph_citation_rate` | HIGH | Simple aggregation over well-defined `cited_in_conclusion` |
| `get_text_between_tools` | MEDIUM | Tool ID matching logic needs careful implementation to handle multiple calls to same tool |
| Inbox parsing | HIGH | Verified against real inbox files |

---

## 7. Summary of Decisions

1. **TeamObservation lives in `output_collector.py`** alongside CollectedOutput, not in a separate module. This keeps the data model cohesive.

2. **Single-agent scenarios produce TeamObservation too** via `TeamObservation.single_agent()`. This means downstream code always works with one type, simplifying 3.1c consumers.

3. **BSKGQuery methods are added directly to TranscriptParser** (not a subclass or mixin), following the extension pattern documented in GAP-04. Python-idiomatic direct addition.

4. **Citation detection uses a 2-term heuristic** (>=2 distinctive terms from result appear in subsequent text). This is conservative and can be tuned upward later.

5. **Inbox messages are loaded lazily** via `AgentObservation.load_inbox()`, not on construction. This avoids filesystem dependencies when inbox data isn't needed.

6. **`RESULT_TRUNCATE_LEN` should be increased to 2000 for BSKG queries** to improve citation detection accuracy. This is a minimal change in `_extract_tool_calls()`.

7. **All designs are backward-compatible**: existing `has_bskg_query()`, `bskg_query_index()`, `first_conclusion_index()` remain unchanged. New methods are additive.
