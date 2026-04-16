# GAP-02: JSONL transcript location for Agent Teams teammates with worktree isolation

**Created by:** improve-phase
**Source:** P1-IMP-04
**Priority:** HIGH
**Status:** active
**depends_on:** []

## Question

Where do JSONL session transcripts appear for Agent Teams teammates spawned with `isolation: "worktree"`? Are they accessible to the orchestrator? If teammates run in separate processes with worktree isolation, does the transcript write path land in the teammate's worktree (inaccessible) or in a shared location?

## Context

The entire JSONL-parsing verification strategy (exit criterion 2) depends on JSONL being accessible per-teammate. If teammates produce separate JSONL streams that the orchestrator cannot read, the verification mechanism silently fails — no error, just a missing file. This is a silent failure mode, the most dangerous kind. This must be empirically confirmed before Plan 02 can specify a parser.

## Research Approach

1. Research Claude Code's JSONL transcript storage mechanism and file paths
2. Determine if transcripts follow the session binary or the working directory
3. Check if worktree isolation changes the transcript path
4. Identify the exact path format and whether orchestrator has read access

## Findings

**Confidence:** HIGH (cross-referenced official docs, blog posts, community tools, and project research file)

### 1. JSONL Transcript Storage Architecture

Claude Code stores JSONL session transcripts at a **fixed, user-level path**:

```
~/.claude/projects/{url-encoded-project-path}/{session-uuid}.jsonl
```

The project path in the directory name is URL-encoded: `/Users/alice/myproject` becomes `-Users-alice-myproject`. Each session gets its own JSONL file named by UUID. Files are append-only.

**Sources:** Official Claude Code docs (code.claude.com/docs/en/hooks), blog posts by Scott Chacon (gitbutler.com), Simon Willison, Yi Huang (Medium), and multiple community tools (claude-code-transcripts by simonw).

### 2. Transcript Path is Project-Scoped, Not CWD-Scoped

The transcript path is determined by the **project root** (the git repository root), not the current working directory. This is key for worktree isolation:

- A worktree created at `.claude/worktrees/{name}/` is still part of the same git repository
- Since **v2.1.63**, project configs and auto-memory are explicitly shared across git worktrees of the same repository
- The transcript for a teammate in a worktree would be stored under the project path that maps to **either** the main repo root OR the worktree path

### 3. SubagentStop Hook Provides Direct Transcript Path

The most reliable access method is NOT filesystem discovery but the **`SubagentStop` hook event**:

```json
{
  "session_id": "abc123",
  "agent_id": "teammate-uuid",
  "agent_transcript_path": "/Users/user/.claude/projects/-Users-user-project/{uuid}.jsonl",
  "last_assistant_message": "..."
}
```

The `agent_transcript_path` field (available since v2.0.42) provides the **exact filesystem path** to the teammate's transcript. The `last_assistant_message` field (v2.1.50+) provides the final response without even needing to parse the transcript.

### 4. Worktree Isolation Impact on Transcripts

Two scenarios depending on how Claude Code encodes the project path:

**Scenario A (likely):** Teammates in worktrees have transcripts at `~/.claude/projects/{encoded-worktree-path}/`, which is a different directory from the parent's `~/.claude/projects/{encoded-project-path}/`. The orchestrator CAN read these files because `~/.claude/projects/` is in the user's home directory, accessible regardless of working directory.

**Scenario B (also possible):** Since v2.1.63 shares project configs across worktrees, Claude Code may use the main repo root as the canonical project path, placing all worktree teammate transcripts in the same directory as the orchestrator's transcripts.

**In both scenarios, the orchestrator has read access.** The transcript files are in `~/.claude/projects/` which is always accessible.

### 5. Alternative Access: SubagentStop Hook Capture

Even if filesystem discovery is unreliable, the `SubagentStop` hook provides the path directly. The evaluation runner can register a SubagentStop hook that captures `agent_transcript_path` and writes it to a known location:

```json
{
  "SubagentStop": [{
    "hooks": [{
      "type": "command",
      "command": "cat | jq -r '.agent_transcript_path' >> /tmp/eval_transcripts.txt"
    }]
  }]
}
```

### 6. Retention Warning

Per Simon Willison: Claude Code has a default behavior of **deleting transcripts after 30 days**. Set `"cleanupPeriodDays": 99999` in `~/.claude/settings.json` to prevent this. Evaluation transcripts needed for post-session analysis must not be garbage collected.

## Recommendation

**Do:** JSONL transcripts ARE accessible to the orchestrator for Agent Teams teammates, even with worktree isolation. The access path is `~/.claude/projects/` (user-level, always readable). However, do NOT rely on filesystem discovery alone.

**Specific actions:**

1. **Primary access method:** Register a `SubagentStop` hook in the evaluation session that captures `agent_transcript_path` for each teammate. Write captured paths to `.vrs/observations/{session}/transcript_paths.json`. This eliminates filesystem guessing entirely.
2. **Fallback:** If `SubagentStop` hook is not triggered (crash, timeout), scan `~/.claude/projects/` for JSONL files modified during the evaluation window, filtered by session_id from task metadata.
3. **Preflight check for Plan 02:** Before the JSONL parser step, verify the transcript file exists at the captured path. If absent, set `CLIAttemptState = TRANSCRIPT_UNAVAILABLE` (per P1-IMP-09's fallback state).
4. **Retention guard:** Ensure `~/.claude/settings.json` has `"cleanupPeriodDays": 99999` before any evaluation run.
5. **Rewrite Assumption 2** to: "JSONL session transcripts for Agent Teams teammates are accessible via the `SubagentStop` hook's `agent_transcript_path` field (v2.0.42+). Transcripts are stored in `~/.claude/projects/{encoded-path}/` at the user level, readable by the orchestrator. Fallback: filesystem scan of `~/.claude/projects/` with timestamp filtering."

**Impacts:** Plan 02 (JSONL parser) is UNBLOCKED. The prerequisite is resolved: transcripts are accessible. Plan 02 Task 0 (preflight check) should verify `SubagentStop` hook integration before proceeding.
