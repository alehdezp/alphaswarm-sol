# Audit Entrypoint Stage Flow

**Purpose:** Detail the 9-stage audit pipeline with inputs, outputs, and decision points.

## Stage Overview

```mermaid
flowchart TB
    START((Start))

    subgraph Stage1["Stage 1: Preflight Gate"]
        P1["Validate .vrs/settings.yaml"]
        P2["Check tool availability"]
        P3["Load state from current.yaml"]
        P_FAIL{"Preflight<br/>passed?"}
    end

    subgraph Stage2["Stage 2: Graph Build"]
        G1["Check graph cache"]
        G2["Build via Slither"]
        G3["Serialize to .toon"]
        G_CHECK{"Graph<br/>valid?"}
    end

    subgraph Stage3["Stage 3: Context Generation"]
        C1["Generate protocol context"]
        C2["Generate economic context"]
        C3["Validate required fields"]
        C_CHECK{"Context<br/>complete?"}
    end

    subgraph Stage4["Stage 4: Tool Initialization"]
        T1["Tool status call (alphaswarm tools status)"]
        T2["Tool scan call (alphaswarm tools run)"]
        T3["Collect tool outputs"]
    end

    subgraph Stage5["Stage 5: Pattern Detection"]
        D1["Tier A: Deterministic"]
        D2["Tier B: LLM-verified"]
        D3["Tier C: Label-dependent"]
        D4["Collect candidates"]
    end

    subgraph Stage6["Stage 6: Task Orchestration"]
        O1["TaskCreate per candidate"]
        O2["Assign to agents"]
        O3["Track task IDs"]
    end

    subgraph Stage7["Stage 7: Verification + Debate"]
        V1["Attacker: exploit path"]
        V2["Defender: guards"]
        V3["Verifier: arbitrate"]
        V4["TaskUpdate with verdict"]
    end

    subgraph Stage8["Stage 8: Report Generation"]
        R1["Merge verified findings"]
        R2["Attach evidence"]
        R3["Generate report"]
    end

    subgraph Stage9["Stage 9: Progress Update"]
        S1["Update current.yaml"]
        S2["Emit resume hint"]
        S3["Store evidence pack"]
    end

    ABORT((Abort))
    DONE((Done))

    START --> P1
    P1 --> P2 --> P3 --> P_FAIL
    P_FAIL -->|No| ABORT
    P_FAIL -->|Yes| G1

    G1 --> G2 --> G3 --> G_CHECK
    G_CHECK -->|No| ABORT
    G_CHECK -->|Yes| C1

    C1 --> C2 --> C3 --> C_CHECK
    C_CHECK -->|No, Tier C disabled| T1
    C_CHECK -->|Yes| T1

    T1 --> T2 --> T3 --> D1

    D1 --> D2 --> D3 --> D4 --> O1

    O1 --> O2 --> O3 --> V1

    V1 --> V2 --> V3 --> V4 --> R1

    R1 --> R2 --> R3 --> S1

    S1 --> S2 --> S3 --> DONE
```

## Stage Details

### Stage 1: Preflight Gate

```mermaid
flowchart LR
    subgraph Inputs
        I1[".vrs/settings.yaml"]
        I2["Skill arguments"]
        I3[".vrs/state/current.yaml"]
    end

    subgraph Checks
        C1["Schema validation"]
        C2["Tool availability"]
        C3["Previous state"]
    end

    subgraph Outputs
        O1["[PREFLIGHT_PASS]"]
        O2["Settings hash"]
        O3["Current stage loaded"]
    end

    I1 --> C1
    I2 --> C1
    I3 --> C3
    C1 --> O1
    C1 --> O2
    C3 --> O3
```

**Required Markers:**
- `[PREFLIGHT_PASS]` or `[PREFLIGHT_FAIL: reason]`
- Settings hash in evidence

**Failure Behavior:**
- Emit guidance: what failed, why, next action
- Halt with non-zero exit

### Stage 2: Graph Build

```mermaid
flowchart LR
    subgraph Inputs
        I1["contracts/"]
        I2["Graph cache"]
    end

    subgraph Processing
        P1["Slither analysis"]
        P2["Property extraction"]
        P3["Signature derivation"]
        P4["Integrity check"]
    end

    subgraph Outputs
        O1[".vrs/graphs/*.toon"]
        O2["[GRAPH_BUILD_SUCCESS]"]
        O3["Node count, edge count"]
    end

    I1 --> P1
    I2 -->|cache hit| O1
    P1 --> P2 --> P3 --> P4
    P4 --> O1
    P4 --> O2
    P4 --> O3
```

**Required Markers:**
- `[GRAPH_BUILD_SUCCESS]` or `[GRAPH_BUILD_FAIL]`
- Node count for integrity check

**Underlying Tool Call (typically orchestrated by Claude Code):**
```bash
uv run alphaswarm build-kg contracts/ --with-labels
```

### Stage 3: Context Generation

```mermaid
flowchart LR
    subgraph Inputs
        I1["contracts/"]
        I2["Protocol docs"]
        I3["Settings"]
    end

    subgraph ProtocolContext
        P1["Extract roles"]
        P2["Trust boundaries"]
        P3["Upgradeability model"]
    end

    subgraph EconomicContext
        E1["Asset flows"]
        E2["Value transfers"]
        E3["Invariants"]
    end

    subgraph Outputs
        O1[".vrs/context/protocol-pack.yaml"]
        O2["EI/CTL outputs"]
        O3["[CONTEXT_READY]"]
    end

    I1 --> P1
    I2 --> P1
    P1 --> P2 --> P3 --> O1

    I1 --> E1
    I3 -->|economic enabled| E1
    E1 --> E2 --> E3 --> O2

    O1 --> O3
    O2 --> O3
```

**Required Fields for Tier C:**
- Roles (admin, user, operator, etc.)
- Upgradeability model
- Asset flows
- Trust boundaries

**Tier C Gating:**
```
IF context.fields.missing > 0 AND tier_c.enabled:
    WARN "Tier C gating: missing fields"
    SKIP Tier C patterns
```

### Stage 4: Tool Initialization

```mermaid
flowchart LR
    subgraph ToolStatus
        S1["tool status (alphaswarm tools status)"]
        S2["Check: slither"]
        S3["Check: aderyn"]
        S4["Check: mythril"]
    end

    subgraph ToolRun
        R1["tool run (alphaswarm tools run)"]
        R2["Slither scan"]
        R3["Aderyn scan"]
        R4["Deduplication"]
    end

    subgraph Outputs
        O1[".vrs/tools/slither.json"]
        O2[".vrs/tools/aderyn.json"]
        O3["[SLITHER_RUN]"]
        O4["[ADERYN_RUN]"]
    end

    S1 --> S2 --> S3 --> S4
    S4 --> R1
    R1 --> R2 --> O1
    R1 --> R3 --> O2
    O1 --> R4
    O2 --> R4
    R2 --> O3
    R3 --> O4
```

**Required Markers:**
- `[TOOL_STATUS]`
- `[SLITHER_RUN]`, `[ADERYN_RUN]`, etc.
- Tool output paths in evidence

### Stage 5: Pattern Detection

```mermaid
flowchart TB
    subgraph TierA["Tier A: Deterministic"]
        A1["Graph properties only"]
        A2["Semantic operations"]
        A3["Signature ordering"]
        A4["HIGH confidence"]
    end

    subgraph TierB["Tier B: LLM-Verified"]
        B1["Graph + context questions"]
        B2["LLM verification"]
        B3["MEDIUM confidence"]
    end

    subgraph TierC["Tier C: Label-Dependent"]
        C1["Requires semantic labels"]
        C2["Label presence/absence"]
        C3["MEDIUM confidence"]
        C4{"Context<br/>available?"}
    end

    subgraph Candidates["Candidate Collection"]
        CAND["All candidates"]
        DEDUP["Deduplicate"]
        RANK["Rank by severity"]
    end

    A1 --> A2 --> A3 --> A4 --> CAND
    B1 --> B2 --> B3 --> CAND
    C4 -->|Yes| C1
    C4 -->|No| SKIP["Skip Tier C"]
    C1 --> C2 --> C3 --> CAND
    CAND --> DEDUP --> RANK
```

**Pattern Flow per Tier:**
| Tier | Input | Process | Output |
|------|-------|---------|--------|
| A | BSKG graph | Property + signature match | HIGH confidence candidates |
| B | BSKG + context | LLM verification questions | MEDIUM confidence candidates |
| C | BSKG + labels | Label match with thresholds | MEDIUM confidence candidates |

### Stage 6: Task Orchestration

```mermaid
sequenceDiagram
    participant C as Claude Code
    participant T as TaskCreate
    participant A as Attacker
    participant D as Defender
    participant V as Verifier

    loop For each candidate
        C->>T: TaskCreate(candidate)
        T-->>C: task_id
        C->>A: Assign task_id
        A-->>C: [ATTACKER_SPAWN]
        C->>D: Assign task_id
        D-->>C: [DEFENDER_SPAWN]
        C->>V: Assign task_id
        V-->>C: [VERIFIER_SPAWN]
    end
```

**Required Markers:**
- `TaskCreate` with task ID
- `[ATTACKER_SPAWN]`, `[DEFENDER_SPAWN]`, `[VERIFIER_SPAWN]`
- Task ID tracking

### Stage 7: Verification + Debate

```mermaid
sequenceDiagram
    participant A as Attacker
    participant D as Defender
    participant V as Verifier
    participant T as TaskUpdate

    A->>A: Construct exploit path
    A->>D: Claim + attack narrative
    D->>D: Search guards/mitigations
    D->>V: Counterclaim + evidence

    opt Debate Required
        A->>V: Rebuttal + bypass
        D->>V: Counter-rebuttal
    end

    V->>V: Cross-check evidence
    V->>T: TaskUpdate(verdict, confidence)
    T-->>V: [VERDICT: confirmed/rejected]
```

**Verdict Types:**
| Verdict | Meaning | Confidence |
|---------|---------|------------|
| `confirmed` | Verified by test or consensus | HIGH |
| `likely` | Strong evidence, no proof | >= 0.75 |
| `uncertain` | Weak or conflicting | 0.40-0.75 |
| `rejected` | Disproven or benign | - |

### Stage 8: Report Generation

```mermaid
flowchart LR
    subgraph Inputs
        I1["Verified findings"]
        I2["Evidence packs"]
        I3["Task history"]
    end

    subgraph Processing
        P1["Merge findings"]
        P2["Rank by severity"]
        P3["Attach evidence"]
        P4["Format report"]
    end

    subgraph Outputs
        O1["Audit report"]
        O2["Evidence index"]
        O3["[REPORT_GENERATED]"]
    end

    I1 --> P1
    I2 --> P3
    I3 --> P2
    P1 --> P2 --> P3 --> P4
    P4 --> O1
    P4 --> O2
    P4 --> O3
```

### Stage 9: Progress Update

```mermaid
flowchart LR
    subgraph StateUpdate
        S1["Update current.yaml"]
        S2["Set stage: completed"]
        S3["Record task IDs"]
    end

    subgraph ResumeInfo
        R1["Emit resume hint"]
        R2["Next step guidance"]
    end

    subgraph Evidence
        E1["Store evidence pack"]
        E2["Transcript path"]
    end

    S1 --> S2 --> S3
    S3 --> R1 --> R2
    S3 --> E1 --> E2
```

**State Schema (current.yaml):**
**Note:** State management functionality is planned for future implementation.

```yaml
run_id: "audit-2026-02-03-001"
stage: "completed"
completed_stages: [preflight, graph, context, tools, detection, tasks, verify, report, progress]
tasks:
  - id: task-001
    verdict: confirmed
  - id: task-002
    verdict: rejected
resume_hint: "/vrs-orch-resume <pool-id>"
evidence_path: ".vrs/evidence/audit-2026-02-03-001/"
```

## Marker Summary

| Stage | Required Markers |
|-------|------------------|
| Preflight | `[PREFLIGHT_PASS/FAIL]`, settings hash |
| Graph | `[GRAPH_BUILD_SUCCESS/FAIL]`, node count |
| Context | `[CONTEXT_READY]`, context fields |
| Tools | `[TOOL_STATUS]`, `[SLITHER_RUN]`, `[ADERYN_RUN]` |
| Detection | `[DETECTION_COMPLETE]`, candidate count |
| Tasks | `TaskCreate`, `[*_SPAWN]` markers |
| Verify | `TaskUpdate`, `[VERDICT: *]` |
| Report | `[REPORT_GENERATED]` |
| Progress | `[STATE_UPDATED]`, resume hint |
