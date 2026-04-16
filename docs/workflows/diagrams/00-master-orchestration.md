# Master Workflow Orchestration

**Purpose:** Show how all AlphaSwarm.sol workflows connect and interact.

## High-Level Flow

```mermaid
flowchart TB
    subgraph UserEntry["User Entry Points"]
        INSTALL["Install & Init"]
        AUDIT_CMD["/vrs-audit contracts/"]
        SKILL_CMD["Other /vrs-* skills"]
    end

    subgraph Orchestration["Audit Orchestration (vrs-audit)"]
        direction TB
        PREFLIGHT["1. Preflight Gate"]
        GRAPH["2. Graph Build"]
        CONTEXT["3. Context Generation"]
        TOOLS["4. Tool Initialization"]
        DETECT["5. Pattern Detection"]
        TASKS["6. Task Orchestration"]
        VERIFY["7. Verification + Debate"]
        REPORT["8. Report Generation"]
        PROGRESS["9. Progress Update"]

        PREFLIGHT --> GRAPH
        GRAPH --> CONTEXT
        CONTEXT --> TOOLS
        TOOLS --> DETECT
        DETECT --> TASKS
        TASKS --> VERIFY
        VERIFY --> REPORT
        REPORT --> PROGRESS
    end

    subgraph Supporting["Supporting Workflows"]
        BEADS["Bead Lifecycle"]
        VULNDOCS["VulnDocs Pipeline"]
        TESTING["Testing Orchestration"]
    end

    subgraph State["State Management"]
        SETTINGS[".vrs/settings.yaml"]
        STATE[".vrs/state/current.yaml"]
        EVIDENCE[".vrs/evidence/"]
    end

    %% Entry connections
    INSTALL --> PREFLIGHT
    AUDIT_CMD --> PREFLIGHT
    SKILL_CMD --> Supporting

    %% Cross-workflow connections
    DETECT --> BEADS
    BEADS --> TASKS
    VULNDOCS -.-> DETECT

    %% State connections
    SETTINGS --> PREFLIGHT
    PREFLIGHT --> STATE
    PROGRESS --> STATE
    VERIFY --> EVIDENCE
```

## Workflow Dependencies

```mermaid
flowchart LR
    subgraph Foundation["Foundation Layer"]
        W_INSTALL["workflow-install"]
        W_GRAPH["workflow-graph"]
    end

    subgraph Context["Context Layer"]
        W_CONTEXT["workflow-context"]
        W_TOOLS["workflow-tools"]
    end

    subgraph Core["Core Layer"]
        W_AUDIT["workflow-audit"]
        W_TASKS["workflow-tasks"]
        W_VERIFY["workflow-verify"]
    end

    subgraph Support["Support Layer"]
        W_PROGRESS["workflow-progress"]
        W_BEADS["workflow-beads"]
        W_VULNDOCS["workflow-vulndocs"]
    end

    W_INSTALL --> W_AUDIT
    W_GRAPH --> W_AUDIT
    W_CONTEXT --> W_AUDIT
    W_TOOLS --> W_AUDIT

    W_AUDIT --> W_TASKS
    W_AUDIT --> W_VERIFY
    W_AUDIT --> W_PROGRESS

    W_TASKS --> W_BEADS
    W_VERIFY --> W_BEADS

    W_VULNDOCS -.-> W_AUDIT
```

## Skill-to-Workflow Mapping

```mermaid
flowchart TB
    subgraph Skills["Skills (User Invokes)"]
        S_AUDIT["vrs-audit"]
        S_HEALTH["vrs-health-check"]
        S_VERIFY["vrs-verify"]
        S_DEBATE["vrs-debate"]
        S_ORCH["vrs-orch-spawn"]
        S_STATUS["vrs-status"]
        S_RESUME["vrs-resume"]
        S_BEAD["vrs-bead-*"]
        S_TOOL["vrs-tool-*"]
        S_DISCOVER["vrs-discover"]
    end

    subgraph Workflows["Workflows (Executed)"]
        WF_INSTALL["Install"]
        WF_AUDIT["Audit"]
        WF_TASKS["Tasks"]
        WF_VERIFY["Verify"]
        WF_PROGRESS["Progress"]
        WF_BEADS["Beads"]
        WF_TOOLS["Tools"]
        WF_VULNDOCS["VulnDocs"]
    end

    S_AUDIT --> WF_AUDIT
    S_HEALTH --> WF_INSTALL
    S_VERIFY --> WF_VERIFY
    S_DEBATE --> WF_VERIFY
    S_ORCH --> WF_TASKS
    S_STATUS --> WF_PROGRESS
    S_RESUME --> WF_PROGRESS
    S_BEAD --> WF_BEADS
    S_TOOL --> WF_TOOLS
    S_DISCOVER --> WF_VULNDOCS
```

## Agent Involvement by Workflow

```mermaid
flowchart LR
    subgraph Workflows["Workflows"]
        WF_AUDIT["Audit"]
        WF_TASKS["Tasks"]
        WF_VERIFY["Verify"]
        WF_VULNDOCS["VulnDocs"]
        WF_TESTING["Testing"]
    end

    subgraph CoreAgents["Core Verification Agents"]
        A_ATK["vrs-attacker<br/>(opus)"]
        A_DEF["vrs-defender<br/>(sonnet)"]
        A_VER["vrs-verifier<br/>(opus)"]
        A_REV["vrs-secure-reviewer<br/>(sonnet)"]
    end

    subgraph OrchestratorAgents["Orchestration Agents"]
        A_SUP["vrs-supervisor"]
        A_INT["vrs-integrator"]
    end

    subgraph PatternAgents["Pattern Agents"]
        A_SCOUT["vrs-pattern-scout<br/>(haiku)"]
        A_PVER["vrs-pattern-verifier"]
        A_CTX["vrs-context-packer"]
    end

    subgraph TestAgents["Testing Agents"]
        A_COND["vrs-test-conductor<br/>(opus)"]
        A_BENCH["vrs-benchmark-runner"]
        A_MUT["vrs-mutation-tester"]
    end

    WF_AUDIT --> A_ATK
    WF_AUDIT --> A_DEF
    WF_AUDIT --> A_VER
    WF_AUDIT --> A_REV
    WF_AUDIT --> A_SUP
    WF_AUDIT --> A_INT

    WF_TASKS --> A_ATK
    WF_TASKS --> A_DEF
    WF_TASKS --> A_VER

    WF_VERIFY --> A_ATK
    WF_VERIFY --> A_DEF
    WF_VERIFY --> A_VER

    WF_VULNDOCS --> A_SCOUT
    WF_VULNDOCS --> A_PVER
    WF_VULNDOCS --> A_CTX

    WF_TESTING --> A_COND
    WF_TESTING --> A_BENCH
    WF_TESTING --> A_MUT
```

## Hook Enforcement Points

```mermaid
flowchart TB
    subgraph Hooks["Claude Code Hooks"]
        H_SESSION["SessionStart<br/>Load state, emit stage"]
        H_PRE["PreToolUse<br/>Block if preflight failed"]
        H_POST["PostToolUse<br/>Log markers"]
        H_STOP["Stop/SubagentStop<br/>Block if no TaskCreate"]
    end

    subgraph Stages["Audit Stages"]
        S1["Preflight"]
        S2["Graph"]
        S3["Context"]
        S4["Tools"]
        S5["Detection"]
        S6["Tasks"]
        S7["Verify"]
        S8["Report"]
    end

    H_SESSION --> S1
    H_PRE --> S2
    H_PRE --> S3
    H_PRE --> S4
    H_POST --> S5
    H_POST --> S6
    H_STOP --> S7
    H_STOP --> S8
```

## Data Flow

```mermaid
flowchart LR
    subgraph Input["Inputs"]
        SOL["Solidity<br/>contracts/"]
        DOCS["Protocol Docs"]
        SETTINGS["settings.yaml"]
    end

    subgraph Processing["Processing"]
        SLITHER["Slither"]
        BUILDER["VKG Builder"]
        BSKG["BSKG Graph"]
        PATTERNS["Pattern Engine"]
        AGENTS["Multi-Agent<br/>Verification"]
    end

    subgraph Output["Outputs"]
        GRAPH_FILE[".vrs/graphs/*.toon"]
        CONTEXT_FILE[".vrs/context/"]
        STATE_FILE[".vrs/state/"]
        EVIDENCE_DIR[".vrs/evidence/"]
        REPORT["Audit Report"]
    end

    SOL --> SLITHER
    SLITHER --> BUILDER
    BUILDER --> BSKG
    BSKG --> GRAPH_FILE

    DOCS --> CONTEXT_FILE
    SETTINGS --> STATE_FILE

    BSKG --> PATTERNS
    PATTERNS --> AGENTS
    AGENTS --> EVIDENCE_DIR
    AGENTS --> REPORT
```

## Cross-References

| Workflow | Primary Doc | Skills | Agents |
|----------|-------------|--------|--------|
| Install | `workflow-install.md` | `vrs-health-check` | None |
| Graph | `workflow-graph.md` | `vrs-graph-contract-validate` | None |
| Context | `workflow-context.md` | `vrs-context-pack`, `vrs-economic-context` | `vrs-context-packer` |
| Tools | `workflow-tools.md` | `vrs-tool-slither`, `vrs-tool-aderyn` | None |
| Audit | `workflow-audit.md` | `vrs-audit` | All core agents |
| Tasks | `workflow-tasks.md` | `vrs-orch-spawn`, `vrs-orch-resume` | `attacker`, `defender`, `verifier` |
| Verify | `workflow-verify.md` | `vrs-verify`, `vrs-debate` | `attacker`, `defender`, `verifier` |
| Progress | `workflow-progress.md` | `vrs-status`, `vrs-resume` | None |
| Beads | `workflow-beads.md` | `vrs-bead-*` | Varies |
| VulnDocs | `workflow-vulndocs.md` | `vrs-discover`, `vrs-refine`, etc. | Pattern agents |
