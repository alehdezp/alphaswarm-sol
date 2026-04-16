"""Evaluation Session Recorder — structured SQLite storage for teammate transcripts.

Parses teammate JSONL transcripts after each evaluation session and stores
structured records in a queryable SQLite database. Enables:
- "What calls were made?" → tool_calls table
- "Did it use build-kg?" → cli_attempts table
- "Did it write good task subjects?" → task_actions table
- "What went wrong across sessions?" → violations + FTS5 search

Architecture follows a "capture → structure → search" pipeline pattern
inspired by claude-mem (github.com/thedotmack/claude-mem). This module
handles the "capture" and "search" stages.

Everything uses Python stdlib sqlite3 — zero dependencies, zero API cost.
Storage: .vrs/evaluations/sessions.db

DC-2 enforcement: No imports from kg or vulndocs subpackages.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data records
# ---------------------------------------------------------------------------


@dataclass
class SessionMetadata:
    """Metadata about an evaluation session, provided by the caller."""

    teammate_name: str = ""
    agent_type: str = ""
    contract: str = ""
    workflow_id: str = ""
    verdict: str = ""  # PASS / DEGRADED / FAIL
    overall_score: float | None = None


@dataclass
class ToolCallRecord:
    """A single tool invocation."""

    id: int = 0
    session_id: str = ""
    sequence_num: int = 0
    tool_name: str = ""
    tool_input: str = ""  # JSON string
    tool_output_excerpt: str = ""  # first 500 chars
    timestamp: str = ""
    blocked: bool = False


@dataclass
class CLIAttemptRecord:
    """A build-kg or query CLI invocation."""

    id: int = 0
    session_id: str = ""
    command: str = ""
    full_bash_input: str = ""
    exit_code: int | None = None
    stdout_excerpt: str = ""  # first 1000 chars
    state: str = ""  # ATTEMPTED_SUCCESS / ATTEMPTED_FAILED / NOT_ATTEMPTED
    timestamp: str = ""


@dataclass
class TaskActionRecord:
    """A TaskCreate/TaskUpdate/TaskList/TaskGet invocation."""

    id: int = 0
    session_id: str = ""
    action: str = ""  # create / update / list / get
    task_subject: str = ""
    task_description: str = ""
    task_status: str = ""  # pending / in_progress / completed
    timestamp: str = ""


@dataclass
class SkillUsageRecord:
    """A Skill tool invocation."""

    id: int = 0
    session_id: str = ""
    skill_name: str = ""
    was_invoked: bool = False
    was_available: bool = True
    invocation_result: str = ""  # success / error / blocked


@dataclass
class ViolationRecord:
    """A detected integrity violation."""

    id: int = 0
    session_id: str = ""
    violation_type: str = ""  # knowledge_leakage / python_import / context_read / fabrication
    evidence: str = ""  # the tool call that triggered it
    severity: str = ""  # critical / warning / info
    timestamp: str = ""


@dataclass
class TimelineEvent:
    """A single event in a session timeline (union of all record types)."""

    timestamp: str = ""
    event_type: str = ""  # tool_call / cli_attempt / task_action / skill_usage / violation
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A single FTS5 search hit."""

    table_name: str = ""
    row_id: int = 0
    session_id: str = ""
    snippet: str = ""
    rank: float = 0.0


@dataclass
class PatternReport:
    """Aggregated patterns across multiple sessions."""

    session_count: int = 0
    most_common_violations: list[tuple[str, int]] = field(default_factory=list)
    tool_usage_distribution: dict[str, int] = field(default_factory=dict)
    cli_success_rate: float = 0.0
    cli_total: int = 0
    cli_successes: int = 0
    empty_task_subjects: int = 0
    total_task_creates: int = 0


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS eval_sessions (
    id TEXT PRIMARY KEY,
    teammate_name TEXT,
    agent_type TEXT,
    contract TEXT,
    workflow_id TEXT,
    start_time TEXT,
    end_time TEXT,
    duration_seconds REAL,
    verdict TEXT,
    overall_score REAL,
    transcript_path TEXT
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES eval_sessions(id),
    sequence_num INTEGER,
    tool_name TEXT,
    tool_input TEXT,
    tool_output_excerpt TEXT,
    timestamp TEXT,
    blocked INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cli_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES eval_sessions(id),
    command TEXT,
    full_bash_input TEXT,
    exit_code INTEGER,
    stdout_excerpt TEXT,
    state TEXT,
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS task_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES eval_sessions(id),
    action TEXT,
    task_subject TEXT,
    task_description TEXT,
    task_status TEXT,
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS skill_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES eval_sessions(id),
    skill_name TEXT,
    was_invoked INTEGER,
    was_available INTEGER,
    invocation_result TEXT
);

CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES eval_sessions(id),
    violation_type TEXT,
    evidence TEXT,
    severity TEXT,
    timestamp TEXT
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_name ON tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_cli_attempts_session ON cli_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_task_actions_session ON task_actions(session_id);
CREATE INDEX IF NOT EXISTS idx_violations_session ON violations(session_id);
CREATE INDEX IF NOT EXISTS idx_violations_type ON violations(violation_type);
CREATE INDEX IF NOT EXISTS idx_sessions_workflow ON eval_sessions(workflow_id);
"""

_FTS_SCHEMA_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS tool_calls_fts USING fts5(
    tool_name, tool_input, tool_output_excerpt,
    content='tool_calls', content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS task_actions_fts USING fts5(
    task_subject, task_description,
    content='task_actions', content_rowid='id'
);
"""

# Triggers to keep FTS in sync with content tables
_FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS tool_calls_ai AFTER INSERT ON tool_calls BEGIN
    INSERT INTO tool_calls_fts(rowid, tool_name, tool_input, tool_output_excerpt)
    VALUES (new.id, new.tool_name, new.tool_input, new.tool_output_excerpt);
END;

CREATE TRIGGER IF NOT EXISTS tool_calls_fts_delete AFTER DELETE ON tool_calls BEGIN
    INSERT INTO tool_calls_fts(tool_calls_fts, rowid, tool_name, tool_input, tool_output_excerpt)
    VALUES('delete', old.id, old.tool_name, old.tool_input, old.tool_output_excerpt);
END;

CREATE TRIGGER IF NOT EXISTS task_actions_ai AFTER INSERT ON task_actions BEGIN
    INSERT INTO task_actions_fts(rowid, task_subject, task_description)
    VALUES (new.id, new.task_subject, new.task_description);
END;

CREATE TRIGGER IF NOT EXISTS task_actions_fts_delete AFTER DELETE ON task_actions BEGIN
    INSERT INTO task_actions_fts(task_actions_fts, rowid, task_subject, task_description)
    VALUES('delete', old.id, old.task_subject, old.task_description);
END;
"""


# ---------------------------------------------------------------------------
# SessionRecorder
# ---------------------------------------------------------------------------


class SessionRecorder:
    """Parse JSONL transcripts and store structured records in SQLite.

    Usage:
        recorder = SessionRecorder()
        session_id = recorder.record_session(transcript_path, metadata)
        calls = recorder.query_tool_calls(session_id)
        results = recorder.search("build-kg")
    """

    def __init__(self, db_path: str | Path = ".vrs/evaluations/sessions.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables, indexes, FTS, and triggers."""
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.executescript(_FTS_SCHEMA_SQL)
        self._conn.executescript(_FTS_TRIGGERS_SQL)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> SessionRecorder:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -------------------------------------------------------------------
    # Record a session
    # -------------------------------------------------------------------

    def record_session(
        self,
        transcript_path: str | Path,
        metadata: SessionMetadata,
        parsed_data: dict[str, Any] | None = None,
    ) -> str:
        """Parse a JSONL transcript and store all structured records.

        If parsed_data is provided (from TranscriptSessionExtractor), uses
        that directly. Otherwise, attempts a basic parse of the JSONL.

        Args:
            transcript_path: Path to the JSONL transcript file.
            metadata: Session metadata from the evaluation runner.
            parsed_data: Pre-parsed structured data (optional). Expected keys:
                tool_calls, cli_attempts, task_actions, skill_usage, violations,
                start_time, end_time, duration_seconds.

        Returns:
            The session_id for the recorded session.
        """
        session_id = str(uuid.uuid4())
        transcript_path = Path(transcript_path)

        if parsed_data is None:
            parsed_data = self._basic_parse(transcript_path)

        start_time = parsed_data.get("start_time", "")
        end_time = parsed_data.get("end_time", "")
        duration = parsed_data.get("duration_seconds", 0.0)

        # Insert session record
        self._conn.execute(
            """INSERT INTO eval_sessions
               (id, teammate_name, agent_type, contract, workflow_id,
                start_time, end_time, duration_seconds, verdict,
                overall_score, transcript_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                metadata.teammate_name,
                metadata.agent_type,
                metadata.contract,
                metadata.workflow_id,
                start_time,
                end_time,
                duration,
                metadata.verdict,
                metadata.overall_score,
                str(transcript_path),
            ),
        )

        # Insert tool calls
        for tc in parsed_data.get("tool_calls", []):
            tool_input = tc.get("tool_input", "")
            if not isinstance(tool_input, str):
                tool_input = json.dumps(tool_input)
            self._conn.execute(
                """INSERT INTO tool_calls
                   (session_id, sequence_num, tool_name, tool_input,
                    tool_output_excerpt, timestamp, blocked)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    tc.get("sequence_num", 0),
                    tc.get("tool_name", ""),
                    tool_input,
                    tc.get("tool_output_excerpt", ""),
                    tc.get("timestamp", ""),
                    1 if tc.get("blocked", False) else 0,
                ),
            )

        # Insert CLI attempts
        for cli in parsed_data.get("cli_attempts", []):
            self._conn.execute(
                """INSERT INTO cli_attempts
                   (session_id, command, full_bash_input, exit_code,
                    stdout_excerpt, state, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    cli.get("command", ""),
                    cli.get("full_bash_input", ""),
                    cli.get("exit_code"),
                    cli.get("stdout_excerpt", ""),
                    cli.get("state", ""),
                    cli.get("timestamp", ""),
                ),
            )

        # Insert task actions
        for ta in parsed_data.get("task_actions", []):
            self._conn.execute(
                """INSERT INTO task_actions
                   (session_id, action, task_subject, task_description,
                    task_status, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    ta.get("action", ""),
                    ta.get("task_subject", ""),
                    ta.get("task_description", ""),
                    ta.get("task_status", ""),
                    ta.get("timestamp", ""),
                ),
            )

        # Insert skill usage
        for su in parsed_data.get("skill_usage", []):
            self._conn.execute(
                """INSERT INTO skill_usage
                   (session_id, skill_name, was_invoked, was_available,
                    invocation_result)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    session_id,
                    su.get("skill_name", ""),
                    1 if su.get("was_invoked", False) else 0,
                    1 if su.get("was_available", True) else 0,
                    su.get("invocation_result", ""),
                ),
            )

        # Insert violations
        for v in parsed_data.get("violations", []):
            self._conn.execute(
                """INSERT INTO violations
                   (session_id, violation_type, evidence, severity, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    session_id,
                    v.get("violation_type", ""),
                    v.get("evidence", ""),
                    v.get("severity", ""),
                    v.get("timestamp", ""),
                ),
            )

        self._conn.commit()
        return session_id

    # -------------------------------------------------------------------
    # Query methods
    # -------------------------------------------------------------------

    def query_tool_calls(
        self, session_id: str, tool_name: str | None = None
    ) -> list[ToolCallRecord]:
        """Get tool calls for a session, optionally filtered by tool name."""
        if tool_name:
            rows = self._conn.execute(
                """SELECT * FROM tool_calls
                   WHERE session_id = ? AND tool_name = ?
                   ORDER BY sequence_num""",
                (session_id, tool_name),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT * FROM tool_calls
                   WHERE session_id = ?
                   ORDER BY sequence_num""",
                (session_id,),
            ).fetchall()
        return [self._row_to_tool_call(r) for r in rows]

    def query_cli_attempts(self, session_id: str) -> list[CLIAttemptRecord]:
        """Get all CLI (build-kg, query) attempts for a session."""
        rows = self._conn.execute(
            """SELECT * FROM cli_attempts
               WHERE session_id = ?
               ORDER BY timestamp""",
            (session_id,),
        ).fetchall()
        return [self._row_to_cli_attempt(r) for r in rows]

    def query_task_actions(self, session_id: str) -> list[TaskActionRecord]:
        """Get all task create/update actions for a session."""
        rows = self._conn.execute(
            """SELECT * FROM task_actions
               WHERE session_id = ?
               ORDER BY timestamp""",
            (session_id,),
        ).fetchall()
        return [self._row_to_task_action(r) for r in rows]

    def query_skill_usage(self, session_id: str) -> list[SkillUsageRecord]:
        """Get all skill usage records for a session."""
        rows = self._conn.execute(
            """SELECT * FROM skill_usage WHERE session_id = ?""",
            (session_id,),
        ).fetchall()
        return [self._row_to_skill_usage(r) for r in rows]

    def query_violations(
        self, session_id: str | None = None
    ) -> list[ViolationRecord]:
        """Get violations, optionally filtered by session."""
        if session_id:
            rows = self._conn.execute(
                "SELECT * FROM violations WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM violations ORDER BY id"
            ).fetchall()
        return [self._row_to_violation(r) for r in rows]

    def search(
        self, query: str, session_id: str | None = None
    ) -> list[SearchResult]:
        """FTS5 full-text search across tool calls and task actions.

        Args:
            query: FTS5 query string (supports AND, OR, NOT, prefix*).
                Hyphens are normalized to spaces so "build-kg" matches
                the tokenized form "build kg".
            session_id: Optional session filter.

        Returns:
            List of SearchResult sorted by relevance (rank).
        """
        # FTS5 default tokenizer splits on hyphens. Normalize so
        # "build-kg" searches for adjacent tokens "build" "kg".
        fts_query = query.replace("-", " ")
        results: list[SearchResult] = []

        # Search tool_calls_fts
        try:
            if session_id:
                rows = self._conn.execute(
                    """SELECT tc.id, tc.session_id,
                              snippet(tool_calls_fts, 1, '>>>', '<<<', '...', 40) as snip,
                              tool_calls_fts.rank
                       FROM tool_calls_fts
                       JOIN tool_calls tc ON tc.id = tool_calls_fts.rowid
                       WHERE tool_calls_fts MATCH ? AND tc.session_id = ?
                       ORDER BY tool_calls_fts.rank""",
                    (fts_query, session_id),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """SELECT tc.id, tc.session_id,
                              snippet(tool_calls_fts, 1, '>>>', '<<<', '...', 40) as snip,
                              tool_calls_fts.rank
                       FROM tool_calls_fts
                       JOIN tool_calls tc ON tc.id = tool_calls_fts.rowid
                       WHERE tool_calls_fts MATCH ?
                       ORDER BY tool_calls_fts.rank""",
                    (fts_query,),
                ).fetchall()

            for r in rows:
                results.append(SearchResult(
                    table_name="tool_calls",
                    row_id=r[0],
                    session_id=r[1],
                    snippet=r[2] or "",
                    rank=r[3] or 0.0,
                ))
        except sqlite3.OperationalError:
            pass  # FTS query syntax error — return partial results

        # Search task_actions_fts
        try:
            if session_id:
                rows = self._conn.execute(
                    """SELECT ta.id, ta.session_id,
                              snippet(task_actions_fts, 0, '>>>', '<<<', '...', 40) as snip,
                              task_actions_fts.rank
                       FROM task_actions_fts
                       JOIN task_actions ta ON ta.id = task_actions_fts.rowid
                       WHERE task_actions_fts MATCH ? AND ta.session_id = ?
                       ORDER BY task_actions_fts.rank""",
                    (fts_query, session_id),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """SELECT ta.id, ta.session_id,
                              snippet(task_actions_fts, 0, '>>>', '<<<', '...', 40) as snip,
                              task_actions_fts.rank
                       FROM task_actions_fts
                       JOIN task_actions ta ON ta.id = task_actions_fts.rowid
                       WHERE task_actions_fts MATCH ?
                       ORDER BY task_actions_fts.rank""",
                    (fts_query,),
                ).fetchall()

            for r in rows:
                results.append(SearchResult(
                    table_name="task_actions",
                    row_id=r[0],
                    session_id=r[1],
                    snippet=r[2] or "",
                    rank=r[3] or 0.0,
                ))
        except sqlite3.OperationalError:
            pass

        results.sort(key=lambda x: x.rank)
        return results

    def get_session_timeline(self, session_id: str) -> list[TimelineEvent]:
        """Chronological list of ALL events for a session."""
        events: list[TimelineEvent] = []

        # Tool calls
        for tc in self.query_tool_calls(session_id):
            events.append(TimelineEvent(
                timestamp=tc.timestamp,
                event_type="tool_call",
                summary=f"{tc.tool_name} (#{tc.sequence_num})",
                details={
                    "tool_name": tc.tool_name,
                    "blocked": tc.blocked,
                    "input_excerpt": tc.tool_input[:200] if tc.tool_input else "",
                },
            ))

        # CLI attempts
        for cli in self.query_cli_attempts(session_id):
            events.append(TimelineEvent(
                timestamp=cli.timestamp,
                event_type="cli_attempt",
                summary=f"CLI: {cli.command[:80]}",
                details={
                    "command": cli.command,
                    "state": cli.state,
                    "exit_code": cli.exit_code,
                },
            ))

        # Task actions
        for ta in self.query_task_actions(session_id):
            events.append(TimelineEvent(
                timestamp=ta.timestamp,
                event_type="task_action",
                summary=f"Task {ta.action}: {ta.task_subject[:60]}",
                details={
                    "action": ta.action,
                    "subject": ta.task_subject,
                    "status": ta.task_status,
                },
            ))

        # Violations
        for v in self.query_violations(session_id):
            events.append(TimelineEvent(
                timestamp=v.timestamp,
                event_type="violation",
                summary=f"[{v.severity}] {v.violation_type}",
                details={
                    "violation_type": v.violation_type,
                    "severity": v.severity,
                    "evidence": v.evidence[:200] if v.evidence else "",
                },
            ))

        # Sort by timestamp (empty timestamps go last)
        events.sort(key=lambda e: (e.timestamp == "", e.timestamp))
        return events

    def get_cross_session_patterns(
        self, workflow_id: str | None = None, last_n: int = 10
    ) -> PatternReport:
        """Aggregate patterns across recent sessions."""
        # Get recent session IDs
        if workflow_id:
            rows = self._conn.execute(
                """SELECT id FROM eval_sessions
                   WHERE workflow_id = ?
                   ORDER BY start_time DESC LIMIT ?""",
                (workflow_id, last_n),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT id FROM eval_sessions
                   ORDER BY start_time DESC LIMIT ?""",
                (last_n,),
            ).fetchall()

        session_ids = [r[0] for r in rows]
        if not session_ids:
            return PatternReport()

        # sqlite3 doesn't support array parameters; session_ids are DB-generated UUIDs
        placeholders = ",".join("?" for _ in session_ids)

        # Most common violations
        violation_rows = self._conn.execute(
            f"""SELECT violation_type, COUNT(*) as cnt
                FROM violations
                WHERE session_id IN ({placeholders})
                GROUP BY violation_type
                ORDER BY cnt DESC""",
            session_ids,
        ).fetchall()

        # Tool usage distribution
        tool_rows = self._conn.execute(
            f"""SELECT tool_name, COUNT(*) as cnt
                FROM tool_calls
                WHERE session_id IN ({placeholders})
                GROUP BY tool_name
                ORDER BY cnt DESC""",
            session_ids,
        ).fetchall()

        # CLI success rate
        cli_rows = self._conn.execute(
            f"""SELECT state, COUNT(*) as cnt
                FROM cli_attempts
                WHERE session_id IN ({placeholders})
                GROUP BY state""",
            session_ids,
        ).fetchall()
        cli_total = sum(r[1] for r in cli_rows)
        cli_successes = sum(r[1] for r in cli_rows if r[0] == "ATTEMPTED_SUCCESS")

        # Task subject quality
        task_rows = self._conn.execute(
            f"""SELECT task_subject
                FROM task_actions
                WHERE session_id IN ({placeholders})
                AND action = 'create'""",
            session_ids,
        ).fetchall()
        empty_subjects = sum(
            1 for r in task_rows if not r[0] or len(r[0].strip()) < 3
        )

        return PatternReport(
            session_count=len(session_ids),
            most_common_violations=[(r[0], r[1]) for r in violation_rows],
            tool_usage_distribution={r[0]: r[1] for r in tool_rows},
            cli_success_rate=(cli_successes / cli_total) if cli_total > 0 else 0.0,
            cli_total=cli_total,
            cli_successes=cli_successes,
            empty_task_subjects=empty_subjects,
            total_task_creates=len(task_rows),
        )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a session record by ID."""
        row = self._conn.execute(
            "SELECT * FROM eval_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def list_sessions(
        self, workflow_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """List recent sessions."""
        if workflow_id:
            rows = self._conn.execute(
                """SELECT * FROM eval_sessions
                   WHERE workflow_id = ?
                   ORDER BY start_time DESC LIMIT ?""",
                (workflow_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT * FROM eval_sessions
                   ORDER BY start_time DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # -------------------------------------------------------------------
    # Row converters
    # -------------------------------------------------------------------

    @staticmethod
    def _row_to_tool_call(row: sqlite3.Row) -> ToolCallRecord:
        return ToolCallRecord(
            id=row["id"],
            session_id=row["session_id"],
            sequence_num=row["sequence_num"],
            tool_name=row["tool_name"],
            tool_input=row["tool_input"] or "",
            tool_output_excerpt=row["tool_output_excerpt"] or "",
            timestamp=row["timestamp"] or "",
            blocked=bool(row["blocked"]),
        )

    @staticmethod
    def _row_to_cli_attempt(row: sqlite3.Row) -> CLIAttemptRecord:
        return CLIAttemptRecord(
            id=row["id"],
            session_id=row["session_id"],
            command=row["command"] or "",
            full_bash_input=row["full_bash_input"] or "",
            exit_code=row["exit_code"],
            stdout_excerpt=row["stdout_excerpt"] or "",
            state=row["state"] or "",
            timestamp=row["timestamp"] or "",
        )

    @staticmethod
    def _row_to_task_action(row: sqlite3.Row) -> TaskActionRecord:
        return TaskActionRecord(
            id=row["id"],
            session_id=row["session_id"],
            action=row["action"] or "",
            task_subject=row["task_subject"] or "",
            task_description=row["task_description"] or "",
            task_status=row["task_status"] or "",
            timestamp=row["timestamp"] or "",
        )

    @staticmethod
    def _row_to_skill_usage(row: sqlite3.Row) -> SkillUsageRecord:
        return SkillUsageRecord(
            id=row["id"],
            session_id=row["session_id"],
            skill_name=row["skill_name"] or "",
            was_invoked=bool(row["was_invoked"]),
            was_available=bool(row["was_available"]),
            invocation_result=row["invocation_result"] or "",
        )

    @staticmethod
    def _row_to_violation(row: sqlite3.Row) -> ViolationRecord:
        return ViolationRecord(
            id=row["id"],
            session_id=row["session_id"],
            violation_type=row["violation_type"] or "",
            evidence=row["evidence"] or "",
            severity=row["severity"] or "",
            timestamp=row["timestamp"] or "",
        )

    # -------------------------------------------------------------------
    # Basic JSONL parse fallback
    # -------------------------------------------------------------------

    def _basic_parse(self, transcript_path: Path) -> dict[str, Any]:
        """Minimal JSONL parse when no pre-parsed data is provided.

        Extracts tool calls and timestamps from the raw JSONL.
        For full extraction, use TranscriptSessionExtractor.
        """
        result: dict[str, Any] = {
            "tool_calls": [],
            "cli_attempts": [],
            "task_actions": [],
            "skill_usage": [],
            "violations": [],
            "start_time": "",
            "end_time": "",
            "duration_seconds": 0.0,
        }

        if not transcript_path.exists():
            return result

        records: list[dict[str, Any]] = []
        try:
            with open(transcript_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return result

        # Extract timestamps from first/last records
        timestamps: list[str] = []
        for r in records:
            ts = r.get("timestamp") or r.get("message", {}).get("timestamp")
            if ts and isinstance(ts, str):
                timestamps.append(ts)

        if timestamps:
            result["start_time"] = timestamps[0]
            result["end_time"] = timestamps[-1]
            try:
                start = datetime.fromisoformat(
                    timestamps[0].replace("Z", "+00:00")
                )
                end = datetime.fromisoformat(
                    timestamps[-1].replace("Z", "+00:00")
                )
                result["duration_seconds"] = (end - start).total_seconds()
            except (ValueError, TypeError):
                pass

        # Extract tool calls from assistant records
        seq_num = 0
        for record in records:
            if record.get("type") != "assistant":
                continue
            message = record.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue

            ts = record.get("timestamp") or message.get("timestamp")
            ts_str = str(ts) if ts and isinstance(ts, str) else ""

            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue

                tool_name = block.get("name", "unknown")
                tool_input = block.get("input", {})
                input_json = json.dumps(tool_input)[:2000]

                result["tool_calls"].append({
                    "sequence_num": seq_num,
                    "tool_name": tool_name,
                    "tool_input": input_json,
                    "tool_output_excerpt": "",
                    "timestamp": ts_str,
                    "blocked": False,
                })
                seq_num += 1

        return result
