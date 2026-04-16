# AlphaSwarm.sol Workflows - Complete ASCII Architecture

**Purpose:** Workflow-first architecture reference for the Claude Code orchestration model.

**Model contract:** Claude Code is the primary interface. CLI commands are subordinate tool calls used by orchestrated workflows, subagents, or developers in CI/debug.

---

## Quick Navigation

| Layer | Workflows | Purpose |
|-------|-----------|---------|
| L1 | Install, Graph | Prepare environment and build BSKG |
| L2 | Context, Tools | Enrich graph and gather tool evidence |
| L3 | Audit, Tasks, Beads | Orchestrate findings and investigation work |
| L4 | Verify, Debate | Multi-agent adjudication |
| L5 | Progress | State + resume continuity |
| L6 | VulnDocs, Testing | Development and validation loops |

---

## Master Orchestration Diagram

**Workflow documents:** `docs/workflows/README.md`, `docs/workflows/workflow-audit.md`, `docs/architecture.md`

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                          ALPHASWARM.SOL EXECUTION MAP                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER ENTRY                                                                  │
│      │                                                                       │
│      ├──► /vrs-audit contracts/                                              │
│      ├──► /vrs-health-check                                                  │
│      └──► /vrs-investigate / /vrs-verify / /vrs-debate                      │
│      │                                                                       │
│      ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                    CLAUDE CODE (PRIMARY ORCHESTRATOR)                 │  │
│  │  - Routes workflow stages                                              │  │
│  │  - Creates TaskCreate/TaskUpdate lifecycle                             │  │
│  │  - Spawns subagents (attacker/defender/verifier)                       │  │
│  │  - Captures evidence + markers                                          │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│      │                     │                          │                      │
│      │                     │                          │                      │
│      ▼                     ▼                          ▼                      │
│  ┌───────────────┐   ┌──────────────────┐   ┌───────────────────────────┐   │
│  │ Subagents     │   │ Tool Calls       │   │ State + Artifacts         │   │
│  │ vrs-attacker  │   │ (CLI subordinate)│   │ .vrs/state/current.yaml   │   │
│  │ vrs-defender  │   │ alphaswarm ...   │   │ .vrs/graphs/*.toon        │   │
│  │ vrs-verifier  │   │ slither/aderyn   │   │ evidence packs/transcripts│   │
│  └───────────────┘   └──────────────────┘   └───────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Layered Workflow View

```text
L1 FOUNDATION
  - install/init workflow
  - graph build workflow

L2 CONTEXT + TOOLS
  - protocol/economic context workflow
  - static tool workflow (status/run/dedupe)

L3 ORCHESTRATION CORE
  - /vrs-audit (9-stage contract)
  - task orchestration (TaskCreate/TaskUpdate)
  - bead lifecycle (create/update/list)

L4 VERIFICATION
  - /vrs-verify
  - /vrs-debate
  - attacker ↔ defender ↔ verifier arbitration

L5 PROGRESS
  - run state persistence
  - resume semantics via orchestration workflow

L6 DEVELOPMENT
  - VulnDocs authoring/validation
  - workflow harness and regression suites
```

---

## 9-Stage Audit Contract (Workflow-First)

```text
Stage 1  Preflight         - settings/schema/tool readiness
Stage 2  Build Graph       - BSKG artifact + integrity checks
Stage 3  Context           - protocol/economic context pack
Stage 4  Tool Init         - static analyzer outputs
Stage 5  Detection         - Tier A/B/C candidate generation
Stage 6  Task Creation     - TaskCreate per candidate
Stage 7  Verification      - attacker/defender/verifier workflow
Stage 8  Report            - evidence-linked findings
Stage 9  Progress Update   - state saved + resume hints
```

Required orchestration evidence:

- stage markers (`[PREFLIGHT_PASS]`, `[GRAPH_BUILD_SUCCESS]`, ...)
- task lifecycle markers (`TaskCreate(...)`, `TaskUpdate(...)`)
- evidence links (`graph_node_ids`, file:line, tool output refs)

---

## Workflow Dependency Graph

```text
install/init
   │
   ▼
graph build
   │
   ├──────────────┐
   ▼              ▼
context         tools
   └──────┬───────┘
          ▼
       /vrs-audit
          │
    ┌─────┴─────┐
    ▼           ▼
  tasks       beads
    │           │
    └─────┬─────┘
          ▼
     verify/debate
          │
          ▼
       progress

PARALLEL DEV LOOP:
  vulndocs <-> testing harness
```

---

## Execution Surfaces

| Surface | Primary Use | Notes |
|---------|-------------|-------|
| Claude Code workflows | User-facing operation | Primary product UX |
| CLI tool calls (`alphaswarm ...`) | Subagent/dev/CI execution | Subordinate to workflows |
| Controller/test harness | Programmatic workflow validation | Used for multi-trial reliability testing |

---

## Developer Tool Calls (Subordinate Surface)

```bash
# graph tooling
uv run alphaswarm build-kg contracts/
uv run alphaswarm query "pattern:weak-access-control"

# tool orchestration
uv run alphaswarm tools status
uv run alphaswarm tools run contracts/ --tools slither,aderyn

# validation tooling
uv run alphaswarm vulndocs validate vulndocs/
uv run pytest tests/ -n auto --dist loadfile
```

These commands are used by orchestrated workflows and by developers in CI/debug paths.

---

## Canonical Sources

- Workflow contracts: `docs/workflows/workflow-*.md`
- Architecture and execution model: `docs/PHILOSOPHY.md`, `docs/architecture.md`, `docs/claude-code-architecture.md`
- Skill registry: `src/alphaswarm_sol/skills/registry.yaml`
- Agent catalog: `src/alphaswarm_sol/agents/catalog.yaml`
- Shipping assets: `src/alphaswarm_sol/shipping/skills/`, `src/alphaswarm_sol/shipping/agents/`

---

*Updated 2026-02-10 | Claude Code workflow-first alignment*
