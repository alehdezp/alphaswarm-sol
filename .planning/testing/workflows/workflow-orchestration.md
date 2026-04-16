# Workflow Orchestration End-To-End

**Purpose:** Validate orchestration flows from start to verdict with full evidence and routing.

## When To Use

- Any change to orchestration, pools, beads, or debate routing.

## Preconditions

- claude-code-controller installed.
- Target contract set.

## Steps

1. Execute the orchestration workflow in live mode.
2. Verify routing to attacker, defender, verifier, and reviewer roles.
3. Confirm tasks are created, assigned, and updated (TaskCreate/Task/TaskUpdate).
4. Confirm progress guidance is emitted (stage, next step, resume hint).
5. Confirm evidence packet creation and verdict emission.
6. Confirm hook enforcement (preflight + Stop/SubagentStop gates).
7. Capture transcripts and reports.

## Orchestration Marker Spec (Required)

Canonical marker strings live in `.planning/testing/MARKER-REGISTRY.yaml`. The list below is the **minimum** subset for this workflow.

**Stage markers (exact strings from philosophy):**
- `[PREFLIGHT_PASS]` or `[PREFLIGHT_FAIL]`
- `[GRAPH_BUILD_SUCCESS]`
- `[CONTEXT_READY]`
- `[TOOLS_COMPLETE]`
- `[DETECTION_COMPLETE]`
- `TaskCreate(task-id)`
- `TaskUpdate(task-id, verdict)`
- `[REPORT_GENERATED]`
- `[PROGRESS_SAVED]`

**Context markers (exact strings from context workflows):**
- `[CONTEXT_READY]`
- `[CONTEXT_INCOMPLETE]`
- `[CONTEXT_SIMULATED]` (when simulated/bypassed)

**Subagent spawn markers (exact strings):**
- `SubagentStart(vrs-attacker)`
- `SubagentStart(vrs-defender)`
- `SubagentStart(vrs-verifier)`
- `SubagentStart(vrs-secure-reviewer)` (when used)

## Optional A/B Comparison (High-Signal)

- Run a solo investigation workflow and a full audit workflow on the same target.
- Compare: task lifecycle markers, subagent outputs, and reasoning depth.
- Record differences in the evidence pack.

## claude-code-controller Commands

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria orchestration" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=30.0 --timeout=600
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript with multi-agent debate markers.
- Task lifecycle markers (TaskCreate/Task/TaskUpdate).
- Progress guidance markers (stage + next step).
- Evidence packet with graph nodes, pattern IDs, and file:line locations.
- Hook markers (preflight gate + completion gate).

## Failure Diagnosis

- Missing debate markers indicates orchestration failure.
- Missing evidence fields indicates validation failure.
- Missing task lifecycle markers indicates task orchestration failure.
- Missing hook markers indicates gate enforcement failure.

## Reasoning-Based Evaluation (Phase 3.1c)

**Orchestrator flow tests live in Phase 3.1c (plan 3.1c-11), not Phase 3.1b.** The full multi-agent evaluation pipeline (per-agent evaluation + pipeline completeness scoring + interactive debrief + improvement loop) applies here. Binary pass/fail checks cannot assess whether the orchestrator decomposed tasks well, coordinated agents effectively, or synthesized findings with appropriate reasoning depth.

The regression baseline (3.1c-12) captures orchestrator evaluation scores alongside skill and agent scores, enabling cross-run comparison and regression detection for the full orchestration pipeline.

Orchestration workflows receive the full evaluation battery when the framework is active.

### Evaluation Contract

The orchestration evaluation contract at `tests/workflow_harness/contracts/workflows/vrs-audit.yaml` defines:
- Required hooks: SubagentStart, SubagentStop (for multi-agent tracking)
- Scored dimensions: pipeline_completeness, agent_coordination, task_decomposition, evidence_chain
- Multi-agent debrief via SendMessage (not Stop hook — uses interactive protocol)
- Metaprompting enabled

### Multi-Agent Interactive Debrief

Before shutdown, the orchestrator sends targeted questions to each teammate via SendMessage:
1. Did all pipeline stages complete? Where were friction points?
2. Did agent coordination work? Where did communication break down?
3. Were tasks well-decomposed? What would you split or merge differently?
4. Did you know what to do at each stage, or were instructions unclear?

Each agent's response is captured and evaluated alongside its transcript.

### Per-Agent Evaluation

Each spawned agent within the orchestration is evaluated individually against its role-specific contract:
- Attacker → investigation contract (GVS, evidence grounding, novel insight)
- Defender → investigation contract (GVS, evidence grounding, role compliance)
- Verifier → investigation contract (synthesis quality, role compliance)

### Pipeline Completeness Score

Beyond marker checking, the reasoning evaluator assesses:
- Did the pipeline handle errors gracefully?
- Were intermediate results passed correctly between stages?
- Did the orchestrator make appropriate decisions at branch points?

### Safe Sandboxing

Orchestration prompt improvements (to `/vrs-audit` SKILL.md or agent .md files) follow the safe sandboxing rule:
1. Copy to test project .claude/
2. Modify copy
3. Re-run and compare
4. Human approves production change
