# Agent Teams Technical Research Report
**Date:** 2026-02-06
**Status:** MIGRATION COMPLETE (2026-02-09) — Legacy infrastructure fully removed
**Focus:** Claude Code Agent Teams capabilities, testing patterns, and migration from legacy infrastructure

> **NOTE (2026-02-09):** The legacy testing infrastructure referenced in this document has been fully deprecated and removed. This document is retained as historical research context.

---

## Executive Summary

Claude Code Agent Teams is an **experimental feature** (released February 6, 2026 with Opus 4.6) that enables multi-agent orchestration within Claude Code. Unlike legacy PTY-based isolation, Agent Teams provides **native orchestration** with inter-agent messaging, shared task lists with dependency management, and built-in coordination primitives.

**Key Finding:** Agent Teams fully replaces the legacy infrastructure for all orchestration and workflow testing. Programmatic testing uses `claude-code-controller` (npm v0.6.1) which reimplements the Agent Teams filesystem protocol. **Migration is now complete (2026-02-09).**

---

## 1. Technical Architecture

### Core Components

| Component | Role | Storage Location |
|-----------|------|-----------------|
| **Team Lead** | Main Claude Code session that creates team | Current session |
| **Teammates** | Separate Claude Code instances | Independent sessions |
| **Task List** | Shared work items with DAG dependencies | `~/.claude/tasks/{team-name}/` |
| **Mailbox** | Inter-agent messaging | `~/.claude/teams/{team-name}/inboxes/` |

### Execution Modes

#### In-Process Mode (Default)
- Works everywhere (VS Code, any terminal)
- Teammates hidden by default, use Shift+Up/Down to select
- No external setup needed

#### Split-Pane Mode
- Requires terminal multiplexer or iTerm2
- NOT supported: VS Code terminal, Windows Terminal, Ghostty
- Configuration: `{ "teammateMode": "terminal_multiplexer" }` (split panes)
- Auto-detection: Uses split panes if in a compatible terminal multiplexer

### Team Persistence
```
~/.claude/teams/{team-name}/
  config.json          # Team metadata, members array
  inboxes/
    team-lead.json     # Messages to leader
    {agent-name}.json  # Messages to teammates

~/.claude/tasks/{team-name}/
  {task-id}.json       # Individual task files
  manifest.json        # Task list metadata
```

---

## 2. Inter-Agent Communication

### Message Types (SendMessage Tool)

| Type | Usage | Cost |
|------|-------|------|
| `message` | Direct to one teammate | 1 delivery |
| `broadcast` | To ALL teammates | N deliveries (expensive) |
| `shutdown_request` | Request graceful shutdown | 1 delivery |
| `shutdown_response` | Approve/reject shutdown | 1 delivery |
| `plan_approval_response` | Approve/reject plan | 1 delivery |

### Delivery Model
- Automatic delivery (no polling)
- Queued if recipient is mid-turn
- UI shows notification when messages waiting
- Idle = waiting for input (normal, not error)

---

## 3. Task Management & Dependencies

### Task States
```
pending -> in_progress -> completed
              |
           deleted (permanent)
```

### DAG Support
- Tasks can explicitly block other tasks
- Automatic unblocking when blocking task completes
- File locking prevents race conditions
- Self-claiming or explicit assignment

### Dependencies
```javascript
TaskUpdate({
  taskId: "3",
  addBlockedBy: ["1", "2"]  // Task 3 waits for 1 and 2
})
```

---

## 4. Plan Approval & Delegate Mode

### Plan Approval
1. Teammate works in read-only plan mode
2. Sends plan approval request to lead
3. Lead approves or rejects with feedback
4. Once approved, teammate implements

### Delegate Mode
- Press Shift+Tab after creating team
- Lead restricted to coordination-only tools
- Lead CANNOT touch code directly
- Best for pure orchestration

---

## 5. Context & Permissions

### Permission Inheritance
- Teammates start with lead's permission settings
- Can change after spawning, not at spawn time
- `--dangerously-skip-permissions` applies to all

### Agent Memory (Persistent)
```yaml
---
name: vrs-attacker
memory: user  # or "project" or "local"
---
```

| Scope | Location | Use |
|-------|----------|-----|
| `user` | `~/.claude/agent-memory/<name>/` | Cross-project knowledge |
| `project` | `.claude/agent-memory/<name>/` | Project-specific, git-shareable |
| `local` | `.claude/agent-memory-local/<name>/` | Project-specific, not committed |

First 200 lines of MEMORY.md loaded into system prompt.

---

## 6. Token Costs

- Each teammate = separate Claude instance with own context
- ~5-7x tokens vs single session for 5-person team
- Broadcasting = N separate messages
- Average usage: $100-200/developer/month with Sonnet 4.5

### Worth it for:
- Research and review (parallel investigation)
- Adversarial debate (competing hypotheses)
- Multi-module features (separate ownership)

### NOT worth it for:
- Routine tasks (single session faster)
- Sequential work (coordination overhead)
- Same-file edits (conflict risk)

---

## 7. Programmatic Usage

### Headless CLI
```bash
claude -p "prompt" --output-format json --allowedTools "Read,Edit,Bash"
```

### GitHub Actions
```yaml
- uses: anthropics/claude-code-action@v1
  with:
    prompt: "Review PR for security issues"
    allowed-tools: "Read,Grep,Glob"
```

### Limitation
- CLI flag (`-p`) does NOT support Agent Teams (session-based feature)
- For multi-agent CI/CD, use `claude-code-controller` (npm v0.6.1)

---

## 8. Migration Patterns: Legacy Infrastructure -> Agent Teams

### Replace with Agent Teams:
- Multi-agent orchestration (attacker/defender/verifier)
- Parallel research/analysis
- Task dependency management (DAG vs manual coordination)

### Fully deprecated:
- All legacy infrastructure replaced by Agent Teams + `claude-code-controller` (npm v0.6.1)

### Comparison Table

| Aspect | Legacy PTY | Agent Teams |
|--------|------|-------------|
| Setup | External process management | Native Claude Code feature |
| Coordination | Manual file-based sync | Built-in messaging & tasks |
| Dependencies | Manual enforcement | DAG with auto-unblocking |
| Context sharing | File I/O or transcript parsing | Automatic message delivery |
| Visibility | Always visible (panes) | Choose in-process or split |
| Persistence | Session-based | Filesystem-backed teams |

---

## 9. Known Limitations (Feb 2026)

1. No session resumption for in-process teammates
2. Task status can lag
3. One team per session, no nested teams
4. Two teammates editing same file -> overwrites
5. Fixed leadership (no promotion)
6. Spawn-time permissions not configurable
7. Split-pane requires terminal multiplexer/iTerm2
8. Shutdown can be slow (finishes current request)

---

## 10. Sources

- Official Agent Teams Docs (code.claude.com/docs/en/agent-teams)
- Subagents Documentation (code.claude.com/docs/en/sub-agents)
- Headless/Programmatic Usage (code.claude.com/docs/en/headless)
- GitHub Actions Integration (code.claude.com/docs/en/github-actions)
- Community Setup Guide (marc0.dev)
- Claude Code Swarm Guide (gist.github.com)
