# Task Lifecycle State Machine

**Purpose:** Define TaskCreate/TaskUpdate state transitions and agent assignments.

## Task States

```mermaid
stateDiagram-v2
    [*] --> pending: TaskCreate

    pending --> in_progress: Agent assigned

    in_progress --> in_progress: Agent handoff
    in_progress --> completed: Verdict confirmed
    in_progress --> completed: Verdict rejected

    completed --> [*]

    note right of pending
        Task created from pattern candidate
        No agent assigned yet
    end note

    note right of in_progress
        One or more agents working
        Evidence being collected
    end note

    note right of completed
        Final verdict reached
        Evidence attached
    end note
```

## Detailed Task Flow

```mermaid
flowchart TB
    subgraph Creation["Task Creation"]
        C1["Pattern candidate found"]
        C2["TaskCreate(subject, description)"]
        C3["Assign task_id"]
        C4["status: pending"]
    end

    subgraph Assignment["Agent Assignment"]
        A1["Assign to attacker"]
        A2["TaskUpdate(status: in_progress)"]
        A3["attacker analyzes"]
        A4["Attacker evidence collected"]
    end

    subgraph Handoff["Agent Handoff"]
        H1["Assign to defender"]
        H2["TaskUpdate(status: in_progress)"]
        H3["defender analyzes"]
        H4["Defender evidence collected"]
    end

    subgraph Arbitration["Verifier Arbitration"]
        V1["Assign to verifier"]
        V2["TaskUpdate(status: in_progress)"]
        V3["verifier cross-checks"]
        V4["Verdict determined"]
    end

    subgraph Completion["Task Completion"]
        D1["TaskUpdate(status: completed)"]
        D2["Attach verdict + evidence"]
        D3["Close task"]
    end

    C1 --> C2 --> C3 --> C4
    C4 --> A1 --> A2 --> A3 --> A4
    A4 --> H1 --> H2 --> H3 --> H4
    H4 --> V1 --> V2 --> V3 --> V4
    V4 --> D1 --> D2 --> D3
```

## Task Schema

```yaml
task:
  id: "task-001"                    # Unique identifier
  subject: "Reentrancy in withdraw" # Brief title (imperative)
  description: |                    # Detailed description
    Pattern: reentrancy-classic
    Location: Vault.sol:42-55
    Signature: R:bal -> X:out -> W:bal
  activeForm: "Investigating reentrancy"  # Present continuous form
  status: "in_progress"             # pending | in_progress | completed
  owner: "vrs-attacker"             # Current agent
  metadata:
    pattern_id: "reentrancy-classic"
    severity: "high"
    confidence: 0.85
  evidence:
    - type: "graph_node"
      id: "func_vault_withdraw_123"
    - type: "code_location"
      file: "Vault.sol"
      lines: [42, 55]
  blocks: []                        # Task IDs this blocks
  blockedBy: []                     # Task IDs blocking this
```

## Agent Assignment Sequence

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant T as Task System
    participant A as Attacker
    participant D as Defender
    participant V as Verifier

    Note over O: Pattern candidate found
    O->>T: TaskCreate(candidate)
    T-->>O: task_id: task-001

    O->>T: TaskUpdate(task-001, owner: attacker)
    T->>A: Spawn with task context

    A->>A: Analyze exploit path
    A->>T: TaskUpdate(evidence: attack_narrative)
    A-->>O: [ATTACKER_DONE]

    O->>T: TaskUpdate(task-001, owner: defender)
    T->>D: Spawn with task + attacker evidence

    D->>D: Search guards/mitigations
    D->>T: TaskUpdate(evidence: guards_found)
    D-->>O: [DEFENDER_DONE]

    O->>T: TaskUpdate(task-001, owner: verifier)
    T->>V: Spawn with all evidence

    V->>V: Cross-check, arbitrate
    V->>T: TaskUpdate(verdict: confirmed, confidence: 0.9)
    V-->>O: [VERIFIER_DONE]

    O->>T: TaskUpdate(task-001, status: completed)
```

## TaskCreate Requirements

```mermaid
flowchart LR
    subgraph Required["Required Fields"]
        R1["subject<br/>(imperative verb)"]
        R2["description<br/>(pattern + location)"]
        R3["activeForm<br/>(present continuous)"]
    end

    subgraph Optional["Optional Fields"]
        O1["metadata.pattern_id"]
        O2["metadata.severity"]
        O3["blockedBy"]
    end

    subgraph Generated["Auto-Generated"]
        G1["id"]
        G2["status: pending"]
        G3["timestamp"]
    end
```

**Subject Naming:**
| Good | Bad |
|------|-----|
| "Investigate reentrancy in withdraw" | "reentrancy-001" |
| "Verify access control on setOwner" | "task" |
| "Check oracle manipulation risk" | "finding #3" |

## TaskUpdate Rules

```mermaid
flowchart TB
    subgraph Allowed["Allowed Transitions"]
        A1["pending → in_progress"]
        A2["in_progress → in_progress<br/>(agent handoff)"]
        A3["in_progress → completed"]
    end

    subgraph NotAllowed["Not Allowed"]
        N1["completed → in_progress"]
        N2["pending → completed<br/>(skip analysis)"]
        N3["Any → deleted<br/>(without evidence)"]
    end

    subgraph Required["Required for Completion"]
        R1["verdict"]
        R2["confidence"]
        R3["evidence array"]
    end
```

**TaskUpdate Evidence Requirements:**
| Verdict | Min Evidence Items |
|---------|-------------------|
| confirmed | 5 (attack + defense + cross-check) |
| likely | 3 |
| uncertain | 2 |
| rejected | 3 (refutation evidence) |

## False Positive Handling

```mermaid
flowchart LR
    subgraph FP["False Positive Flow"]
        F1["Candidate found"]
        F2["TaskCreate"]
        F3["Attacker analyzes"]
        F4["No exploit path"]
        F5["Defender confirms guard"]
        F6["Verifier: rejected"]
        F7["TaskUpdate<br/>status: completed<br/>verdict: rejected"]
    end

    F1 --> F2 --> F3 --> F4 --> F5 --> F6 --> F7
```

**Required for Rejection:**
- Discard rationale in evidence
- Guard/mitigation reference
- TaskUpdate with `verdict: rejected`

## Scope Enforcement

```mermaid
flowchart TB
    subgraph Scope["Task Scope"]
        S1["Contract: Vault.sol"]
        S2["Function: withdraw"]
        S3["Pattern: reentrancy-classic"]
    end

    subgraph InScope["Agent MUST Stay In Scope"]
        I1["Analyze withdraw function"]
        I2["Check related state vars"]
        I3["Follow direct call paths"]
    end

    subgraph OutOfScope["Agent MUST NOT"]
        O1["Analyze unrelated contracts"]
        O2["Report unrelated patterns"]
        O3["Exceed assigned pattern"]
    end

    S1 --> I1
    S2 --> I2
    S3 --> I3

    S1 -.-> O1
    S3 -.-> O2
```

**Scope Drift Detection:**
- If agent mentions contracts not in task scope → flag
- If agent reports patterns not in task assignment → reject
- If task scope exceeded → TaskUpdate with scope violation note

## Hook Enforcement

```mermaid
flowchart TB
    subgraph PreHook["Before Task Completion"]
        P1["Stop/SubagentStop hook"]
        P2{"TaskCreate<br/>exists?"}
        P3{"TaskUpdate<br/>has evidence?"}
    end

    subgraph Enforcement["Enforcement"]
        E1["Block completion"]
        E2["Emit error: missing task lifecycle"]
        E3["Require fix before continue"]
    end

    subgraph Success["Allow Completion"]
        S1["Proceed to report"]
    end

    P1 --> P2
    P2 -->|No| E1 --> E2
    P2 -->|Yes| P3
    P3 -->|No| E1
    P3 -->|Yes| S1
```

## Marker Summary

| Event | Marker | Required Fields |
|-------|--------|-----------------|
| Task created | `TaskCreate` | subject, description |
| Agent assigned | `TaskUpdate` | owner, status: in_progress |
| Evidence added | `TaskUpdate` | evidence array |
| Verdict reached | `TaskUpdate` | verdict, confidence |
| Task completed | `TaskUpdate` | status: completed |
| Spawn events | `[ATTACKER_SPAWN]`, etc. | task_id |
| Done events | `[ATTACKER_DONE]`, etc. | evidence summary |
