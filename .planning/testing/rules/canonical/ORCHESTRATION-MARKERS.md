# Orchestration Markers Specification

**Status:** CANONICAL
**Created:** 2026-02-04
**Purpose:** Define exact marker strings for orchestration validation (IMP-A1)

---

## Overview

Orchestration markers are structured strings emitted during Claude Code orchestration that enable:
1. Automated validation of workflow execution
2. Sequence verification (stages in correct order)
3. Anti-fabrication checks (markers must be present and valid)
4. Progress tracking and debugging

## Marker Format

All markers follow this structure:
```
[STAGE_NAME field1={value1} field2={value2}]
```

- Stage names use SCREAMING_SNAKE_CASE
- Field names use snake_case
- Values are unquoted unless containing spaces
- Timestamps use ISO 8601 format: `2026-02-04T15:30:00Z`

---

## Stage Markers (Required Sequence)

### 1. Preflight Stage
```
[PREFLIGHT_START]
[PREFLIGHT_PASS duration_ms={ms}]
[PREFLIGHT_FAIL reason={reason}]
```
- **Emitter:** Init orchestrator (skill)
- **Required fields:** `duration_ms` (integer)
- **Failure fields:** `reason` (string, no spaces or use underscore)

### 2. Graph Build Stage
```
[GRAPH_BUILD_START target={path}]
[GRAPH_BUILD_SUCCESS nodes={n} edges={e} hash={h}]
[GRAPH_BUILD_FAIL reason={reason}]
```
- **Emitter:** CLI (`alphaswarm build-kg`)
- **Required fields:** `nodes` (integer), `edges` (integer), `hash` (sha256 first 12 chars)
- **Example:** `[GRAPH_BUILD_SUCCESS nodes=142 edges=387 hash=a3f8c2b1e9d4]`

### 3. Context Load Stage
```
[CONTEXT_LOAD_START protocol={name}]
[CONTEXT_READY protocol={name} ctl={high|medium|low|simulated}]
[CONTEXT_INCOMPLETE protocol={name} missing={fields}]
[CONTEXT_SIMULATED protocol={name} reason={reason}]
```
- **Emitter:** Context pack loader
- **Required fields:** `protocol` (string), `ctl` (enum: high/medium/low/simulated)
- **CTL = Context Trust Level**

### 4. Task Creation Stage
```
TaskCreate(id={task_id}, subject={subject})
TaskUpdate(id={task_id}, status={status})
```
- **Emitter:** Claude Code Task tool
- **Required fields:** `id` (string), `subject` (string, may have spaces)
- **Status values:** `pending`, `in_progress`, `completed`, `pending_dedup`, `ready`
- **Note:** These are Claude Code native markers, not bracketed

### 5. Detection Stage
```
[DETECTION_START patterns={count}]
[DETECTION_MATCH pattern={id} function={name} confidence={score}]
[DETECTION_COMPLETE matches={count} unique={count}]
```
- **Emitter:** Pattern matcher
- **Required fields:** `patterns` (integer), `matches` (integer), `unique` (integer)
- **Confidence:** 0.0-1.0 float

### 6. Deduplication Stage
```
[DEDUP_START findings={count}]
[DEDUP_MERGE source={id1} target={id2} reason={reason}]
[DEDUP_COMPLETE original={count} deduplicated={count}]
```
- **Emitter:** Dedup orchestrator
- **Required fields:** `original` (integer), `deduplicated` (integer)

### 7. Subagent Spawn Stage
```
SubagentStart(type={vrs-attacker|vrs-defender|vrs-verifier|vrs-secure-reviewer})
SubagentComplete(type={type}, findings={count}, evidence_nodes={count})
```
- **Emitter:** Claude Code Task tool (subagent spawn)
- **Valid types:** `vrs-attacker`, `vrs-defender`, `vrs-verifier`, `vrs-secure-reviewer`
- **Note:** Not bracketed (Claude Code native format)

### 8. Debate Stage
```
[DEBATE_START bead={id}]
[DEBATE_ROUND attacker_claims={n} defender_claims={n}]
[DEBATE_VERDICT bead={id} severity={severity} confidence={score}]
```
- **Emitter:** Verifier agent
- **Severity values:** `critical`, `high`, `medium`, `low`, `informational`, `safe`
- **Confidence:** 0.0-1.0 float

### 9. Report Generation Stage
```
[REPORT_START format={json|markdown|sarif}]
[REPORT_GENERATED findings={count} path={path}]
```
- **Emitter:** Report generator
- **Required fields:** `findings` (integer), `path` (string)

### 10. Progress Save Stage
```
[PROGRESS_SAVED state={path} checkpoint={id}]
[PROGRESS_RESUME checkpoint={id}]
```
- **Emitter:** State manager
- **Required fields:** `state` (path), `checkpoint` (string)

---

## Required Marker Sequences

### Full Audit Workflow
```
[PREFLIGHT_START] → [PREFLIGHT_PASS]
→ [GRAPH_BUILD_START] → [GRAPH_BUILD_SUCCESS]
→ [CONTEXT_LOAD_START] → [CONTEXT_READY]
→ TaskCreate(...)
→ [DETECTION_START] → [DETECTION_COMPLETE]
→ [DEDUP_START] → [DEDUP_COMPLETE]
→ SubagentStart(...) → SubagentComplete(...)  (×3 for debate)
→ [DEBATE_START] → [DEBATE_VERDICT]
→ [REPORT_GENERATED]
→ [PROGRESS_SAVED]
```

### Minimum E2E Markers
For E2E validation, ALL of these must appear:
- `[GRAPH_BUILD_SUCCESS ...]`
- `TaskCreate(...)`
- `TaskUpdate(...)`
- `SubagentStart(...)`
- `SubagentComplete(...)`
- `[REPORT_GENERATED ...]`

---

## Anti-Fabrication Rules

### Marker Presence Thresholds

| Test Type | Required Markers | Min Count |
|-----------|------------------|-----------|
| Smoke | `[PREFLIGHT_PASS]`, `[GRAPH_BUILD_SUCCESS]` | 2 |
| Agent Unit | Above + `SubagentStart`, `SubagentComplete` | 4 |
| E2E | Above + `TaskCreate`, `[REPORT_GENERATED]` | 6 |
| Multi-Agent | Above + `[DEBATE_VERDICT]` | 7 |

### Validation Logic
```python
def validate_markers(transcript: str, test_type: str) -> bool:
    required = REQUIRED_MARKERS[test_type]
    for marker_pattern in required:
        if not re.search(marker_pattern, transcript):
            return False
    return True
```

### Timestamp Consistency
- Markers must appear in chronological order
- `GRAPH_BUILD_SUCCESS` timestamp must precede `DETECTION_START`
- `SubagentStart` must precede corresponding `SubagentComplete`

---

## VQL Query Markers

For graph-first enforcement (I-03), VQL queries must be marked:
```
[VQL_QUERY id={VQL-MIN-XX} result_count={n}]
```

- Must appear BEFORE any conclusion marker
- At least one VQL query per finding
- Example: `[VQL_QUERY id=VQL-MIN-04 result_count=3]`

---

## Tool Bypass Markers

When a tool is unavailable or times out:
```
[TOOL_BYPASS tool={name} reason={tool_unavailable|tool_timeout|scope_exclusion}]
```

Allowed reasons:
- `tool_unavailable`: Tool not installed
- `tool_timeout`: Tool exceeded timeout
- `scope_exclusion`: Tool excluded from scope

---

## Marker Emission Responsibility

| Marker Category | Emitter |
|----------------|---------|
| Preflight | Init orchestrator skill |
| Graph Build | CLI (`alphaswarm build-kg`) |
| Context Load | Context pack loader |
| Task Create/Update | Claude Code Task tool |
| Detection | Pattern matcher |
| Deduplication | Dedup orchestrator |
| Subagent | Claude Code Task tool |
| Debate | Verifier agent |
| Report | Report generator |
| Progress | State manager |

---

## Usage in Validation

### Transcript Validation Script
```python
# scripts/validate_orchestration_markers.py
REQUIRED_MARKERS = {
    'smoke': [
        r'\[PREFLIGHT_PASS',
        r'\[GRAPH_BUILD_SUCCESS',
    ],
    'agent_unit': [
        r'\[PREFLIGHT_PASS',
        r'\[GRAPH_BUILD_SUCCESS',
        r'SubagentStart\(',
        r'SubagentComplete\(',
    ],
    'e2e': [
        r'\[PREFLIGHT_PASS',
        r'\[GRAPH_BUILD_SUCCESS',
        r'TaskCreate\(',
        r'TaskUpdate\(',
        r'SubagentStart\(',
        r'SubagentComplete\(',
        r'\[REPORT_GENERATED',
    ],
    'multi_agent': [
        r'\[PREFLIGHT_PASS',
        r'\[GRAPH_BUILD_SUCCESS',
        r'TaskCreate\(',
        r'SubagentStart\(type=vrs-attacker',
        r'SubagentStart\(type=vrs-defender',
        r'SubagentStart\(type=vrs-verifier',
        r'\[DEBATE_VERDICT',
        r'\[REPORT_GENERATED',
    ],
}
```

---

## Document Maintenance

- Update when new stages are added
- Update when marker format changes
- Version this document with date
- Cross-reference with RULES-ESSENTIAL.md

**Last Updated:** 2026-02-04
