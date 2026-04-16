# Progress & State Management

**Purpose:** Define state transitions, checkpoints, and resume behavior.

## State Machine

```mermaid
stateDiagram-v2
    [*] --> not_started

    not_started --> preflight: /vrs-audit
    preflight --> preflight_failed: Validation fails
    preflight --> graph: Validation passes

    preflight_failed --> preflight: /vrs-audit (retry)

    graph --> graph_failed: Build fails
    graph --> context: Build succeeds

    graph_failed --> graph: Rebuild

    context --> context_incomplete: Missing fields
    context --> tools: Complete

    context_incomplete --> context: Regenerate
    context_incomplete --> tools: Tier C disabled

    tools --> tools_failed: Tool error
    tools --> detection: Tools complete

    tools_failed --> detection: Skip failed tools

    detection --> tasks: Candidates found
    detection --> completed: No candidates

    tasks --> verification: Tasks created

    verification --> report: All verified

    report --> completed: Report generated

    completed --> [*]

    note right of preflight
        Load settings
        Check tool availability
        Load previous state
    end note

    note right of verification
        Multi-agent debate
        TaskUpdate with verdicts
    end note
```

## Stage Transitions

```mermaid
flowchart LR
    subgraph Stages["Audit Stages"]
        S0["not_started"]
        S1["preflight"]
        S2["graph"]
        S3["context"]
        S4["tools"]
        S5["detection"]
        S6["tasks"]
        S7["verification"]
        S8["report"]
        S9["completed"]
    end

    S0 -->|"/vrs-audit"| S1
    S1 -->|"PREFLIGHT_PASS"| S2
    S2 -->|"GRAPH_BUILD_SUCCESS"| S3
    S3 -->|"CONTEXT_READY"| S4
    S4 -->|"TOOLS_COMPLETE"| S5
    S5 -->|"DETECTION_COMPLETE"| S6
    S6 -->|"TASKS_CREATED"| S7
    S7 -->|"VERIFICATION_DONE"| S8
    S8 -->|"REPORT_GENERATED"| S9
```

## State Schema

```yaml
# .vrs/state/current.yaml
version: "1.0"
run_id: "audit-2026-02-03-001"
started_at: "2026-02-03T14:30:00Z"
updated_at: "2026-02-03T14:45:00Z"

stage: "verification"
stage_started_at: "2026-02-03T14:42:00Z"

completed_stages:
  - stage: preflight
    completed_at: "2026-02-03T14:30:15Z"
    duration_ms: 15000
  - stage: graph
    completed_at: "2026-02-03T14:32:00Z"
    duration_ms: 105000
  - stage: context
    completed_at: "2026-02-03T14:35:00Z"
    duration_ms: 180000
  - stage: tools
    completed_at: "2026-02-03T14:38:00Z"
    duration_ms: 180000
  - stage: detection
    completed_at: "2026-02-03T14:40:00Z"
    duration_ms: 120000
  - stage: tasks
    completed_at: "2026-02-03T14:42:00Z"
    duration_ms: 120000

tasks:
  total: 5
  pending: 0
  in_progress: 2
  completed: 3
  items:
    - id: task-001
      status: completed
      verdict: confirmed
    - id: task-002
      status: completed
      verdict: rejected
    - id: task-003
      status: completed
      verdict: likely
    - id: task-004
      status: in_progress
      owner: vrs-defender
    - id: task-005
      status: in_progress
      owner: vrs-attacker

artifacts:
  graph: ".vrs/graphs/project.toon"
  context: ".vrs/context/protocol-pack.yaml"
  tools:
    slither: ".vrs/tools/slither.json"
    aderyn: ".vrs/tools/aderyn.json"

next_step: "Complete verification for task-004 and task-005"
resume_hint: "/vrs-orch-resume <pool-id>"

settings_hash: "sha256:abc123..."
commit_hash: "772c2fc"
```

## Resume Flow

```mermaid
flowchart TB
    subgraph Check["Resume Check"]
        C1["Load current.yaml"]
        C2{"Previous<br/>run exists?"}
        C3{"Stage<br/>incomplete?"}
    end

    subgraph Resume["Resume Options"]
        R1["Continue from last stage"]
        R2["Restart from stage"]
        R3["Start fresh"]
    end

    subgraph Action["Resume Action"]
        A1["Load completed artifacts"]
        A2["Skip completed stages"]
        A3["Resume at current stage"]
    end

    C1 --> C2
    C2 -->|No| R3
    C2 -->|Yes| C3
    C3 -->|Yes| R1
    C3 -->|No| R2

    R1 --> A1 --> A2 --> A3
```

### Resume Commands (Current + Planned)

**Note:** Resume is supported via orchestration workflows. Rollback remains a future extension.

```bash
# Check current state
cat .vrs/state/current.yaml

# Resume from where left off
/vrs-orch-resume <pool-id>

# Resume specific run
/vrs-orch-resume <pool-id>

# Restart from specific stage
/vrs-audit contracts/ --resume <run-id>

# Start fresh (discard state)
/vrs-audit contracts/ --fresh
```

## Checkpoint System

```mermaid
flowchart TB
    subgraph Checkpoints["Checkpoint Creation"]
        CP1["After preflight: settings validated"]
        CP2["After graph: BSKG built"]
        CP3["After context: protocol pack ready"]
        CP4["After tools: tool outputs collected"]
        CP5["After detection: candidates identified"]
        CP6["After each task: evidence attached"]
    end

    subgraph Storage["Checkpoint Storage"]
        S1[".vrs/checkpoints/"]
        S2["checkpoint-{stage}-{timestamp}.yaml"]
    end

    subgraph Rollback["Rollback Capability"]
        R1["Future rollback extension"]
        R2["Restore state to checkpoint"]
        R3["Discard subsequent artifacts"]
    end

    CP1 --> S1
    CP2 --> S1
    CP3 --> S1
    CP4 --> S1
    CP5 --> S1
    CP6 --> S1

    S1 --> R1
    R1 --> R2 --> R3
```

### Checkpoint Schema

```yaml
# .vrs/checkpoints/checkpoint-graph-2026-02-03T14:32:00Z.yaml
checkpoint_id: "cp-graph-001"
created_at: "2026-02-03T14:32:00Z"
stage: "graph"
run_id: "audit-2026-02-03-001"

state_snapshot:
  stage: "graph"
  completed_stages: [preflight]

artifacts_snapshot:
  - path: ".vrs/graphs/project.toon"
    hash: "sha256:def456..."
    size_bytes: 524288

rollback_command: "future-extension"
```

## Progress Guidance

```mermaid
flowchart LR
    subgraph Guidance["Progress Guidance Format"]
        G1["Current stage"]
        G2["Completed stages"]
        G3["Next step"]
        G4["Resume hint"]
        G5["ETA (optional)"]
    end

    subgraph Output["Status Line Output"]
        O1["[STAGE: verification]"]
        O2["[COMPLETED: 6/9]"]
        O3["[NEXT: Verify task-004]"]
        O4["[RESUME: /vrs-orch-resume]"]
    end

    G1 --> O1
    G2 --> O2
    G3 --> O3
    G4 --> O4
```

### Progress Output Example

```
═══════════════════════════════════════════════════════════════════
  AlphaSwarm.sol Audit Progress
═══════════════════════════════════════════════════════════════════
  Run ID:     audit-2026-02-03-001
  Stage:      verification (7/9)
  Duration:   15 minutes

  ✓ preflight      (15s)
  ✓ graph          (1m 45s)
  ✓ context        (3m)
  ✓ tools          (3m)
  ✓ detection      (2m)
  ✓ tasks          (2m)
  → verification   (in progress)
    report
    completed

  Tasks: 3/5 completed
    - task-004: in_progress (defender)
    - task-005: in_progress (attacker)

  Next Step: Complete verification for task-004 and task-005
  Resume:    /vrs-orch-resume <pool-id>
═══════════════════════════════════════════════════════════════════
```

## Failure Recovery

```mermaid
flowchart TB
    subgraph Failure["Failure Detection"]
        F1["Stage timeout"]
        F2["Agent crash"]
        F3["Tool error"]
        F4["Invalid state"]
    end

    subgraph Recovery["Recovery Actions"]
        R1["Save checkpoint"]
        R2["Log failure reason"]
        R3["Emit recovery guidance"]
        R4["Update state.yaml"]
    end

    subgraph UserAction["User Actions"]
        U1["Retry current stage"]
        U2["Skip failed component"]
        U3["Rollback to checkpoint"]
        U4["Start fresh"]
    end

    F1 --> R1
    F2 --> R1
    F3 --> R1
    F4 --> R1

    R1 --> R2 --> R3 --> R4

    R4 --> U1
    R4 --> U2
    R4 --> U3
    R4 --> U4
```

### Failure State Schema

```yaml
# Added to current.yaml on failure
failure:
  occurred_at: "2026-02-03T14:50:00Z"
  stage: "tools"
  reason: "Slither timeout after 300s"
  recoverable: true
  recovery_options:
    - command: "/vrs-orch-resume <pool-id>"
      description: "Resume orchestration from current state"
    - command: "/vrs-audit contracts/ --resume <run-id>"
      description: "Re-enter audit flow with saved state"
    - command: "future rollback extension"
      description: "Rollback support planned"
```

## Session Integration

```mermaid
flowchart TB
    subgraph SessionStart["SessionStart Hook"]
        S1["Load .vrs/state/current.yaml"]
        S2["Emit current stage"]
        S3["Set status line extras"]
    end

    subgraph StatusLine["Status Line"]
        L1["stage: verification"]
        L2["next: task-004"]
        L3["run: audit-001"]
    end

    subgraph StageTransition["Stage Transition"]
        T1["Update current.yaml"]
        T2["Create checkpoint"]
        T3["Update status line"]
        T4["Emit progress marker"]
    end

    SessionStart --> StatusLine
    StageTransition --> StatusLine
```

## Marker Summary

| Event | Marker | State Update |
|-------|--------|--------------|
| Stage start | `[STAGE_START: name]` | `stage: name` |
| Stage complete | `[STAGE_COMPLETE: name]` | `completed_stages += name` |
| Checkpoint created | `[CHECKPOINT: id]` | Checkpoint file created |
| Resume | `[RESUME_FROM: stage]` | Load checkpoint |
| Rollback | `[ROLLBACK_TO: stage]` | Restore checkpoint |
| Failure | `[FAILURE: reason]` | `failure: {...}` |
| Recovery | `[RECOVERY: action]` | Clear failure |
