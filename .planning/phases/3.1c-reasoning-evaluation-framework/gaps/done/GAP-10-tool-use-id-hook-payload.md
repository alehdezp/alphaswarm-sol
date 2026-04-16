# GAP-10: Does Claude Code Inject tool_use_id Into Hook Payloads?

**Created by:** improve-phase
**Source:** P5-IMP-08
**Priority:** HIGH
**Status:** resolved
**depends_on:** []

## Question

Does Claude Code inject a `tool_use_id` field into PreToolUse/PostToolUse hook stdin JSON payloads? The project's own hook-verification-findings.md (RS-04) verified PreToolUse input fields as: session_id, transcript_path, cwd, permission_mode, hook_event_name, tool_name, tool_input — with no `tool_use_id`. Is this field absent, or was it missed in verification?

## Context

Plan 3.1c-03 (observation parser) needs to pair tool_use events with their results. The current code uses LIFO matching (line 161 of observation_parser.py), which breaks on parallel tool calls. The proposed fix is to correlate by `tool_use_id`, but this depends on the field being present in hook payloads.

If `tool_use_id` IS present: add to 3.1c-02 scope (hooks capture it) and 3.1c-03 scope (parser pairs by ID).
If `tool_use_id` is NOT present: evaluate alternatives — timestamp proximity pairing, command-content fingerprinting, or accepting imperfect pairing for v1.

## Research Approach

- Search Claude Code official documentation for hook input schema (PreToolUse, PostToolUse)
- Search for any Claude Code hook examples that show the full stdin payload structure
- Check Anthropic docs or GitHub for Claude Code hook specifications
- Check if `tool_use_id` appears in any Claude Code related documentation
- Authoritative source: Anthropic official docs, Claude Code source/docs, verified examples

## Findings

**Confidence: HIGH** — Based on official Anthropic documentation (primary source).

### `tool_use_id` IS present in hook payloads

The official Claude Code hooks reference at `https://code.claude.com/docs/en/hooks` (also mirrored at `https://docs.anthropic.com/en/docs/claude-code/hooks`) explicitly documents `tool_use_id` as a field in three hook events:

#### 1. PreToolUse

The docs state (verbatim): "PreToolUse hooks receive `tool_name`, `tool_input`, and `tool_use_id`." This is listed as an event-specific field alongside the common fields (session_id, transcript_path, cwd, permission_mode, hook_event_name).

#### 2. PostToolUse

The official example includes `tool_use_id`:
```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
  "cwd": "/Users/...",
  "permission_mode": "default",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "content": "file content"
  },
  "tool_response": {
    "filePath": "/path/to/file.txt",
    "success": true
  },
  "tool_use_id": "toolu_01ABC123..."
}
```

#### 3. PostToolUseFailure

Also includes `tool_use_id` in the official example:
```json
{
  "session_id": "abc123",
  "hook_event_name": "PostToolUseFailure",
  "tool_name": "Bash",
  "tool_input": { "command": "npm test" },
  "tool_use_id": "toolu_01ABC123...",
  "error": "Command exited with non-zero status code 1",
  "is_interrupt": false
}
```

#### 4. PermissionRequest explicitly LACKS it

The docs note that PermissionRequest "receive `tool_name` and `tool_input` fields like PreToolUse hooks, but without `tool_use_id`." This explicit exclusion further confirms `tool_use_id` is a deliberate, documented field in the other tool events.

### Why RS-04 missed it

The project's RS-04 verification (2026-02-11) cross-referenced two sources:
1. **RS-02 research** — which predated or didn't capture this field
2. **`claude-code-hooks-mastery` reference repo** — a community repo that may not have used or documented all available fields

Neither source is authoritative. The official Anthropic docs are the primary source and clearly document `tool_use_id`. The RS-04 finding was a false negative caused by relying on secondary sources without checking the official reference.

### The `tool_use_id` format

The format shown in official docs is `"toolu_01ABC123..."`, which matches the Anthropic API tool_use_id format used in the Messages API. This is the same ID that correlates a `tool_use` content block with its `tool_result` in the conversation transcript. This means the hook payload ID and the transcript ID are the same value — enabling direct correlation.

### Sources

| Source | URL | Confidence |
|--------|-----|------------|
| Official Claude Code Hooks Reference | https://code.claude.com/docs/en/hooks | **HIGH** (primary) |
| Anthropic Docs Mirror | https://docs.anthropic.com/en/docs/claude-code/hooks (redirects to above) | **HIGH** (same content) |
| Project RS-04 Findings | `.vrs/debug/phase-3.1b/research/hook-verification-findings.md` | MEDIUM (secondary, missed field) |

## Recommendation

**`tool_use_id` IS available. Use it for tool_use/tool_result pairing. Update plans 3.1c-02 and 3.1c-03.**

### Specific changes needed

#### Plan 3.1c-02 (Observation Hooks)

Add `tool_use_id` capture to observation hooks. Every PreToolUse and PostToolUse observation event MUST include the `tool_use_id` field from the hook stdin payload. The observation hook scripts should extract it alongside tool_name and tool_input:

```python
# In observation hook scripts for PreToolUse/PostToolUse/PostToolUseFailure:
tool_use_id = input_data.get("tool_use_id")  # "toolu_01ABC123..."
```

The JSONL observation record should include `tool_use_id` as a top-level field.

#### Plan 3.1c-03 (Observation Parser)

Replace LIFO matching with `tool_use_id` correlation:
- When parsing a PreToolUse observation, index by `tool_use_id`
- When parsing a PostToolUse/PostToolUseFailure observation, look up the matching PreToolUse by `tool_use_id`
- This correctly handles parallel tool calls where LIFO ordering is unreliable

The current LIFO matching (observation_parser.py line 161) should be replaced with a dict lookup keyed by `tool_use_id`.

#### Update RS-04 findings

Add a correction note to `.vrs/debug/phase-3.1b/research/hook-verification-findings.md` documenting that the PreToolUse and PostToolUse schemas were incomplete — `tool_use_id` was missed. The corrected schemas should include the field.

#### CONTEXT.md

No CONTEXT.md changes needed. This is a factual finding that unblocks existing plan scope. The plans already anticipated this field might be available; now it is confirmed.
