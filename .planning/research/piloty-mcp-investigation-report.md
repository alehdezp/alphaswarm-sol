# Piloty MCP Investigation Report

**Date:** 2026-02-04
**Status:** SUPERSEDED (2026-02-09) — Migration completed using Agent Teams + claude-code-controller instead
**Purpose:** Historical evaluation for VRS testing framework migration from legacy CLI infrastructure

> **NOTE (2026-02-09):** This investigation was superseded by the Agent Teams + `claude-code-controller` migration. Piloty was not adopted. The legacy testing infrastructure has been fully removed. This document is retained as historical research context.

---

## Executive Summary

Piloty is a **purpose-built PTY session manager with Claude Code integration**. It offers significant advantages over legacy CLI for our testing workflows, but has several bugs and gaps that need addressing.

**Verdict:** ✅ **Recommended for adoption** with bug fixes and enhancements

---

## Tool Inventory & Test Results

### 1. Session Management

| Tool | Status | Notes |
|------|--------|-------|
| `run` | ✅ Works | Executes commands, returns clean `screen` output |
| `list_sessions` | ✅ Works | Lists all active sessions with transcript paths |
| `terminate` | ✅ Works | Cleanly terminates sessions |
| `get_metadata` | ❌ **BUG** | `'PTY' object has no attribute '_proc'` |
| `configure_session` | ✅ Works | Accepts `tag` and `prompt_regex` |

### 2. Input Methods

| Tool | Status | Notes |
|------|--------|-------|
| `run` | ✅ Works | Adds newline automatically |
| `send_input` | ✅ Works | No newline added - for raw input |
| `send_control` | ✅ Works | Ctrl+C tested, interrupts processes |
| `send_password` | ⚠️ Untested | Should work (similar pattern) |
| `send_claude` | ❌ **BUG** | `string index out of range` |

### 3. Output Methods

| Tool | Status | Notes |
|------|--------|-------|
| `read` / `get_screen` | ✅ Works | Returns clean VT100-rendered screen |
| `get_scrollback` | ✅ Works | Returns raw scrollback with escapes |
| `poll_output` | ✅ Works | For async output polling |
| `transcript` | ✅ Works | Returns transcript file path |
| `clear_scrollback` | ✅ Works | Clears transcript |

### 4. State Detection

| Tool | Status | Notes |
|------|--------|-------|
| `expect_prompt` | ⚠️ **Issues** | Times out even with visible prompt; custom regex doesn't help |

### 5. Claude Code Integration (CRITICAL)

| Tool | Status | Notes |
|------|--------|-------|
| `start_claude` | ✅ **Excellent** | Auto-generates UUID, waits for ready, returns JSONL path |
| `send_claude` | ❌ **BUG** | `string index out of range` after session starts |
| `get_workflow_summary` | ✅ **Excellent** | PWF format with 87% token reduction |
| `get_subagent_results` | ✅ Works | Returns empty when no subagents (correct) |

### 6. Signals

| Tool | Status | Notes |
|------|--------|-------|
| `send_signal` | ❌ **BUG** | `'PTY' object has no attribute '_proc'` |

---

## Detailed Findings

### 🟢 Strengths (Why Migrate)

#### 1. `start_claude` is Purpose-Built for Our Use Case
```json
{
  "session_id": "piloty-claude-test",
  "claude_session_uuid": "92b6f832-bf91-4a80-b8b0-76b11b2b5f2c",
  "jsonl_path": "/Users/.../.claude/projects/.../92b6f832-bf91-4a80-b8b0-76b11b2b5f2c.jsonl",
  "subagents_dir": "/Users/.../.claude/projects/.../92b6f832-bf91-4a80-b8b0-76b11b2b5f2c/subagents",
  "status": "ready"
}
```
- **Auto-generates deterministic session UUID** → No manual tracking
- **Waits for Claude to be ready** → No fragile sleep hacks
- **Returns JSONL path directly** → Immediate transcript access
- **Returns subagents directory** → First-class subagent support

#### 2. `get_workflow_summary` is Transformative
```
# PWF format (87% token reduction)
U|What is 2+2? Answer in one word.
A|Four.
```
- **Four formats:** PWF, TOON, YAML, JSON
- **Built-in stats:** turn_count, subagent_count, error_count, token_usage
- **Configurable extraction:** tools, subagents, errors, user prompts, assistant text

#### 3. Clean Screen Output
```
screen: "Mac% echo 'hello'\nhello\nMac%"
```
- VT100-rendered, no escape sequences
- Ready for regex parsing and validation

#### 4. State Persistence
- Session state persists across `run` calls
- Environment variables, working directory maintained
- Matches legacy PTY behavior

---

### 🔴 Bugs (Must Fix)

#### BUG-1: `_proc` Attribute Missing
**Affected tools:** `get_metadata`, `send_signal`
**Error:** `'PTY' object has no attribute '_proc'`
**Impact:** Can't get PID, can't send signals
**Priority:** HIGH (needed for process management)

#### BUG-2: `send_claude` String Index Error
**Error:** `string index out of range`
**Context:** Occurs after `start_claude` returns successfully
**Impact:** Can't send commands to Claude Code sessions reliably
**Priority:** CRITICAL (blocks Claude Code automation)

#### BUG-3: `expect_prompt` Unreliable
**Behavior:** Times out even when prompt is visible
**Custom regex:** Doesn't help (`Mac%|\\$|#|>`)
**Impact:** Can't reliably wait for command completion
**Priority:** HIGH (needed for synchronization)

---

### 🟡 Gaps (Enhancement Requests)

#### GAP-1: No Session Naming Pattern Enforcement
**VRS Need:** `vrs-demo-{workflow}-{timestamp}` pattern
**Current:** Any string accepted
**Request:** Add `session_name_pattern` config option with validation

#### GAP-2: No Automatic Anti-Fabrication Checks
**VRS Need:** Detect fabricated transcripts (< 50 lines, < 5s duration, missing tool markers)
**Current:** Returns raw data only
**Request:** Add `validate_transcript()` tool with configurable thresholds:
```python
validate_transcript(
    min_lines=50,
    min_duration_sec=5,
    required_markers=["alphaswarm", "slither"],
    forbid_perfect_metrics=True
)
```

#### GAP-3: No Duration Tracking
**VRS Need:** Verify test ran for minimum time
**Current:** No timestamps in output
**Request:** Add `start_time`, `end_time`, `duration_sec` to session metadata

#### GAP-4: No Pane/Window Isolation Metadata
**VRS Need:** Record `session_label` and `pane_id` for manifest
**Current:** Only `session_id`
**Request:** Add `pane_id`, `window_id`, `created_at` to metadata

#### GAP-5: Scrollback Cleanup
**Current:** `get_scrollback` returns raw escape sequences
**Request:** Option for clean scrollback (like `get_screen`)

#### GAP-6: No Tool Marker Detection
**VRS Need:** Verify specific tools were invoked
**Current:** Manual regex on transcript
**Request:** `detect_tool_markers(transcript, patterns)` helper

#### GAP-7: PWF Format Missing Assistant Text
**Observation:** PWF includes assistant text, but TOON/YAML/JSON don't consistently
**Request:** Ensure `include_assistant_text=true` works across all formats

---

## Migration Impact Analysis

### What Piloty Replaces

| legacy CLI Pattern | Piloty Equivalent | Improvement |
|-----------------|-------------------|-------------|
| `legacy CLI launch "zsh"` | `run(session_id, "zsh")` | Same |
| `legacy CLI send "claude"` | `start_claude()` | **Much better** - waits for ready |
| `legacy CLI send "/skill" --pane=X` | `run()` or `send_input()` | Same |
| `legacy CLI wait_idle --idle-time=15` | `expect_prompt()` | **Broken** - needs fix |
| `legacy CLI capture > transcript.txt` | `transcript()` + `get_screen()` | Same |
| Manual JSONL parsing | `get_workflow_summary()` | **Much better** |
| Manual subagent tracking | `get_subagent_results()` | **Much better** |

### Documentation Updates Required

1. `.planning/testing/rules/canonical/RULES-ESSENTIAL.md` → Replace legacy CLI patterns
2. `.planning/testing/rules/canonical/VALIDATION-RULES.md` → Update A4 (legacy PTY-based)
3. `.planning/testing/rules/LEGACY-CLI-REFERENCE.md` → Deprecate or convert
4. `.planning/testing/rules/canonical/legacy CLI-instructions.md` → Replace with piloty-instructions.md
5. All workflow guides referencing legacy CLI

---

## Recommended Improvements for VRS Integration

### Priority 1: Bug Fixes (BLOCKING)

```python
# Fix _proc attribute
class PTY:
    def __init__(self):
        self._proc = None  # Initialize properly

# Fix send_claude string index
def send_claude(session_id, command, timeout):
    # Add bounds checking before string indexing

# Fix expect_prompt
def expect_prompt(session_id, timeout):
    # Use more robust prompt detection
    # Consider screen content, not just output stream
```

### Priority 2: VRS-Specific Extensions

```python
# New tool: validate_transcript
def validate_transcript(
    session_id: str,
    min_lines: int = 50,
    min_duration_sec: float = 5.0,
    required_markers: list[str] = [],
    forbid_perfect_metrics: bool = True
) -> ValidationResult:
    """
    Returns:
    {
        "valid": bool,
        "violations": [
            {"rule": "min_lines", "expected": 50, "actual": 12},
            {"rule": "required_marker", "marker": "alphaswarm", "found": false}
        ],
        "metrics": {
            "line_count": 12,
            "duration_sec": 3.2,
            "markers_found": ["slither"]
        }
    }
    """

# New tool: wait_for_tool_output
def wait_for_tool_output(
    session_id: str,
    tool_pattern: str,  # regex for tool output
    timeout: float = 60.0
) -> ToolOutputResult:
    """Wait until specific tool output appears"""

# Enhanced metadata
def get_metadata(session_id: str) -> SessionMetadata:
    """
    Returns:
    {
        "session_id": str,
        "alive": bool,
        "pid": int,
        "created_at": datetime,
        "duration_sec": float,
        "transcript_path": str,
        "pane_id": str,  # NEW
        "tag": str,       # NEW
        "prompt_regex": str  # NEW
    }
    """
```

### Priority 3: Workflow Helpers

```python
# New tool: run_vrs_workflow
def run_vrs_workflow(
    workflow: str,  # "audit", "verify", etc.
    target: str,    # contract path
    config: dict    # workflow-specific config
) -> WorkflowResult:
    """
    High-level wrapper that:
    1. Creates session with VRS naming pattern
    2. Starts Claude Code
    3. Sends workflow command
    4. Waits for completion
    5. Extracts and validates results
    6. Returns structured output
    """
```

---

## Test Coverage Summary

| Tool | Tested | Works | Bugs |
|------|--------|-------|------|
| run | ✅ | ✅ | - |
| send_input | ✅ | ✅ | - |
| send_control | ✅ | ✅ | - |
| send_password | ❌ | - | - |
| send_claude | ✅ | ❌ | string index |
| send_signal | ✅ | ❌ | _proc attr |
| poll_output | ✅ | ✅ | - |
| read | ✅ | ✅ | - |
| get_screen | ✅ | ✅ | - |
| get_scrollback | ✅ | ✅ | - |
| transcript | ✅ | ✅ | - |
| clear_scrollback | ✅ | ✅ | - |
| list_sessions | ✅ | ✅ | - |
| get_metadata | ✅ | ❌ | _proc attr |
| configure_session | ✅ | ✅ | - |
| terminate | ✅ | ✅ | - |
| expect_prompt | ✅ | ⚠️ | unreliable |
| start_claude | ✅ | ✅ | - |
| get_workflow_summary | ✅ | ✅ | - |
| get_subagent_results | ✅ | ✅ | - |

**Coverage:** 19/20 tools tested (95%)
**Working:** 15/19 (79%)
**Bugs:** 4 tools affected

---

## Conclusion

**SUPERSEDED:** This conclusion was written before the Agent Teams migration was chosen. Piloty was not adopted; the legacy infrastructure was replaced by Agent Teams + `claude-code-controller` instead. Original conclusion for historical context:

1. **CRITICAL:** Fix `send_claude` - without this, can't automate Claude Code
2. **HIGH:** Fix `expect_prompt` - needed for reliable synchronization
3. **HIGH:** Fix `_proc` attribute - needed for metadata and signals

After bug fixes, the VRS-specific enhancements (validation, duration tracking, tool marker detection) would make this a best-in-class testing framework.

---

## Next Steps

**SUPERSEDED (2026-02-09):** These next steps were not pursued. The project adopted Agent Teams + `claude-code-controller` instead of Piloty. All legacy testing infrastructure has been removed.
