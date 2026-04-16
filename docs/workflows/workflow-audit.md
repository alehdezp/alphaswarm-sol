# Workflow Audit Entrypoint

**Purpose:** Define the expected end-to-end audit orchestration.

> **v6.0 Status:** This workflow is the TARGET design. E2E pipeline currently breaks at Stage 4. Phase 3 will prove the full pipeline works on a real contract.

## Inputs

- Contract scope
- Settings (`.vrs/settings.yaml`)
- Tool availability

## Outputs

- Evidence‑linked audit report
- Task history (TaskCreate/Task/TaskUpdate)
- State updates (`.vrs/state/current.yaml`)
- Hook markers (preflight, task lifecycle, verification)

## Preflight Gate (Required)

Before orchestration, the audit must validate:

- `.vrs/settings.yaml` exists and matches schema
- tool availability (orchestrator tool call: `uv run alphaswarm tools status`)
- graph presence (or trigger build)
- context availability when Tier C is enabled

**Failure behavior:** emit explicit guidance (what failed, why, next action/skill) and halt.

**Schema reference:** `docs/reference/settings-state-schema.md`

## Hook Enforcement (Required)

Audit orchestration must be enforced with hooks:

- **PreToolUse** blocks tool calls when settings disallow tools or preflight failed.
- **Stop / SubagentStop** blocks completion until TaskCreate/TaskUpdate markers and evidence sections exist.
- **SessionStart** loads `.vrs/state/current.yaml` and emits current stage.

Hook contracts live in: `docs/reference/claude-code-orchestration.md`.

## Skills

- `vrs-audit`
- `vrs-health-check`
- `vrs-context-pack`
- `vrs-pattern-batch`
- `vrs-pattern-verify`
- `vrs-bead-create`, `vrs-bead-update`, `vrs-bead-list`
- `vrs-orch-spawn`, `vrs-orch-resume`
- `vrs-tool-slither`, `vrs-tool-aderyn`

**Note:** Testing orchestration uses dev skills in `.claude/skills/vrs-test-*/` (not shipped).

## Subagents

- `vrs-attacker`
- `vrs-defender`
- `vrs-verifier`
- `vrs-secure-reviewer`
- `vrs-integrator`
- `vrs-supervisor`
- `vrs-pattern-scout`
- `vrs-pattern-composer`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Stages

1. Health check and init
2. Graph build
3. Context generation (protocol + economic)
4. Tool initialization
5. Pattern detection (Tier A/B/C)
6. Task orchestration per finding
7. Verification + debate
8. Report
9. Progress + resume state update

## Orchestration Marker Contract (Required)

**Stage markers (exact strings):**
- `[PREFLIGHT_PASS]` or `[PREFLIGHT_FAIL]`
- `[GRAPH_BUILD_SUCCESS]`
- `[CONTEXT_READY]` (or `[CONTEXT_INCOMPLETE]` when context is unavailable)
- `[TOOLS_COMPLETE]`
- `[DETECTION_COMPLETE]`
- `[REPORT_GENERATED]`
- `[PROGRESS_SAVED]`

**Task lifecycle markers (exact strings):**
- `TaskCreate(task-id)`
- `TaskUpdate(task-id, verdict)`

**Subagent spawn markers (exact strings):**
- `SubagentStart(vrs-attacker)`
- `SubagentStart(vrs-defender)`
- `SubagentStart(vrs-verifier)`
- `SubagentStart(vrs-secure-reviewer)` (when used)
- `SubagentStart(vrs-integrator)` (when used)

## Task Contract (Required)

- TaskCreate must appear for every pattern candidate (marker required in transcript).
- TaskUpdate must include evidence and verdict for each task (marker required in transcript).
- Findings must not be emitted without a task lifecycle.

## Success

- Task lifecycle markers present
- Stage markers present for each audit stage
- Graph-first: BSKG/VQL queries appear before conclusions
- Progress guidance emitted
- False positives explicitly discarded
- Hook markers show preflight and task enforcement

## Failure

- Findings reported without tasks or verification
- Missing tool/context stages
- Audit completes without hook enforcement

## Testing

- `.planning/testing/workflows/workflow-audit-entrypoint.md`
