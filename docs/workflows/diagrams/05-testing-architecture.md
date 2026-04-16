# Testing Architecture

**Purpose:** Define the testing patterns for workflow validation (development use only).

## Core Architecture

```mermaid
flowchart TB
    subgraph Automated["Automated Tests (Primary)"]
        A1["pytest test suite"]
        A2["Graph builder tests"]
        A3["Pattern detection tests"]
        A4["Tool integration tests"]
    end

    subgraph Evidence["Evidence Validation"]
        E1["Transcript analysis"]
        E2["Marker detection"]
        E3["Evidence quality checks"]
        E4["Pass/Fail decision"]
    end

    Automated -->|"produces"| Evidence
```

## Why This Architecture?

```mermaid
flowchart LR
    subgraph Problem["The Problem"]
        P1["Skills describe workflows"]
        P2["But don't execute them"]
        P3["No proof of orchestration"]
    end

    subgraph Solution["The Solution"]
        S1["Automated test suites"]
        S2["Evidence-based validation"]
        S3["External ground truth"]
        S4["Validate against criteria"]
    end

    Problem --> Solution
```

**Key Insight:** Testing skills by reading their source is insufficient. We must validate them through automated tests and evidence-based evaluation.

## Evaluation Criteria

```mermaid
flowchart TB
    subgraph MarkerCheck["Required Markers"]
        M1["TaskCreate with task_id"]
        M2["TaskUpdate with evidence"]
        M3["Agent spawn markers"]
        M4["Stage markers"]
    end

    subgraph Evidence["Evidence Validation"]
        E1["Graph node IDs present"]
        E2["Code locations (file:line)"]
        E3["Evidence pack created"]
    end

    subgraph Decision["Pass/Fail"]
        D1{"All checks<br/>pass?"}
        PASS["PASS"]
        FAIL["FAIL + reason"]
    end

    MarkerCheck --> D1
    Evidence --> D1
    D1 -->|Yes| PASS
    D1 -->|No| FAIL
```

### Marker Detection

```python
# Expected markers by workflow
REQUIRED_MARKERS = {
    "vrs-audit": [
        r"\[PREFLIGHT_PASS\]",
        r"\[GRAPH_BUILD_SUCCESS\]",
        r"TaskCreate",
        r"TaskUpdate",
        r"\[ATTACKER_SPAWN\]",
        r"\[VERDICT:",
    ],
    "vrs-health-check": [
        r"/vrs-health-check",
        r"health",
    ],
    "vrs-verify": [
        r"\[ATTACKER_SPAWN\]",
        r"\[DEFENDER_SPAWN\]",
        r"\[VERIFIER_SPAWN\]",
        r"\[VERDICT:",
    ],
}
```

## Evidence Pack Structure

```mermaid
flowchart TB
    subgraph Pack[".vrs/testing/runs/run-001/"]
        F1["transcript.txt"]
        F2["report.json"]
        F3["environment.json"]
        F4["commands.log"]
        F5["ground_truth.json"]
    end

    subgraph Report["report.json"]
        R1["pass: true/false"]
        R2["markers_found: [...]"]
        R3["markers_missing: [...]"]
        R4["duration_ms: 45000"]
        R5["transcript_lines: 523"]
    end

    subgraph Environment["environment.json"]
        E1["settings_hash"]
        E2["commit_hash"]
        E3["tool_versions"]
        E4["timestamp"]
    end
```

### Evidence Pack Schema

```yaml
# report.json
{
  "run_id": "run-2026-02-03-001",
  "workflow": "vrs-audit",
  "pass": true,
  "started_at": "2026-02-03T14:30:00Z",
  "completed_at": "2026-02-03T14:45:00Z",
  "duration_ms": 900000,
  "markers": {
    "required": ["PREFLIGHT_PASS", "TaskCreate", "TaskUpdate", "VERDICT"],
    "found": ["PREFLIGHT_PASS", "TaskCreate", "TaskUpdate", "VERDICT:confirmed"],
    "missing": []
  },
  "evidence": {
    "task_ids": ["task-001", "task-002"],
    "verdicts": ["confirmed", "rejected"],
    "graph_nodes": 42,
    "code_locations": 15
  }
}
```

## Workflow-Specific Testing

### Install Workflow Test

Run `vrs-health-check` through Claude Code orchestration and capture transcript + tool events.

**Expected Markers:**
- `/vrs-health-check` invocation
- tool-call evidence (if health-check triggers CLI internally)
- Health check JSON output

### Audit Workflow Test

**Expected Markers:**
- `[PREFLIGHT_PASS]`
- `[GRAPH_BUILD_SUCCESS]`
- `TaskCreate`
- `[ATTACKER_SPAWN]`, `[DEFENDER_SPAWN]`, `[VERIFIER_SPAWN]`
- `TaskUpdate` with verdict
- `[VERDICT: confirmed/rejected]`

### Verification Workflow Test

**Expected Markers:**
- Agent spawns
- Debate markers (if triggered)
- `[VERDICT:]`

## Parallel Testing

```mermaid
flowchart TB
    subgraph Controller["Controller"]
        C1["Test orchestrator"]
    end

    subgraph Workspaces["Isolated Workspaces"]
        W1["workspace-1<br/>/test-001"]
        W2["workspace-2<br/>/test-002"]
        W3["workspace-3<br/>/test-003"]
    end

    Controller --> W1
    Controller --> W2
    Controller --> W3
```

**Parallel Testing Rules:**
- Each test in separate workspace
- No shared state between tests
- Evidence packs in separate directories

## Test Categories

```mermaid
flowchart LR
    subgraph Smoke["Smoke Tests"]
        SM1["Health check works"]
        SM2["Graph builds"]
        SM3["Basic skill loads"]
    end

    subgraph Integration["Integration Tests"]
        IN1["Full audit flow"]
        IN2["Multi-agent debate"]
        IN3["Resume from checkpoint"]
    end

    subgraph E2E["End-to-End Tests"]
        E1["Fresh install → audit → report"]
        E2["Complex vulnerability detection"]
        E3["Failure recovery"]
    end

    Smoke -->|"< 30s"| Integration -->|"2-10min"| E2E
```

| Category | Duration | Transcript Lines | Frequency |
|----------|----------|------------------|-----------|
| Smoke | < 30s | 50+ | Every change |
| Integration | 2-10min | 200+ | Daily |
| E2E | 10-30min | 500+ | Weekly |

## Marker Summary

| Test Phase | Markers |
|------------|---------|
| Setup | `[TEST_START]`, `[PANE_LAUNCHED]` |
| Execution | `[SKILL_INVOKED]`, workflow markers |
| Capture | `[TRANSCRIPT_CAPTURED]` |
| Evaluation | `[MARKERS_CHECKED]`, `[EVIDENCE_VALIDATED]` |
| Result | `[TEST_PASS]` or `[TEST_FAIL: reason]` |
