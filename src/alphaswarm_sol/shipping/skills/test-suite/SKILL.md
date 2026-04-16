---
name: /vrs-test-suite
forced-eval: true
version: 1.0.0
owner: 3.1c-01 (stub) -> 3.1c-09 (complete)
---

# /vrs-test-suite

Orchestrate the reasoning evaluation suite across tiers. Runs evaluation
workflows, collects results, and produces a SuiteExitReport.

## Purpose

Execute evaluation workflows for a specified tier/category, applying the
two-stage testing model (capability contract check first, reasoning
evaluation only if capability passes). Produce a structured exit report
conforming to the SuiteExitReport schema.

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tier` | `Literal["core", "important", "standard"]` | `"standard"` | Testing tier to evaluate |
| `category` | `str \| None` | `None` | Workflow category filter (investigation, tool, orchestration, support) |
| `workflow_ids` | `list[str] \| None` | `None` | Specific workflows to evaluate (overrides tier/category) |
| `dry_run` | `bool` | `False` | If True, run pipeline on 1 workflow in headless mode, validate exit report schema, then stop |
| `debate` | `bool` | `False` | Enable dual-evaluator debate protocol (extends per-workflow ceiling to 3600s) |
| `effort_level` | `Literal["minimal", "standard", "thorough"]` | `"standard"` | Evaluation effort level |

## Exit Report Schema

The suite produces a `SuiteExitReport` conforming to:
`.vrs/schemas/test_suite_exit_report.schema.json`

## Per-Workflow Loop

```pseudocode
for each workflow in selected_workflows:
    # Budget check
    if elapsed > per_workflow_budget:
        write WorkflowStatus(workflow_id, status="interrupted", error="budget_exceeded")
        continue

    # Kill-file check
    if path_exists(".vrs/evaluations/kill.signal"):
        write WorkflowStatus(workflow_id, status="skipped", error="kill_signal")
        break  # stop all remaining workflows

    # Skip pending tier changes (IMP-03)
    if workflow_id in pending_tier_changes.yaml:
        write WorkflowStatus(workflow_id, status="skipped", error="pending_tier_change")
        continue

    try:
        1. Load evaluation contract from
           src/alphaswarm_sol/testing/evaluation/contracts/{workflow_id}.yaml
        2. Spawn Agent Teams for this workflow
           - Pass per-teammate file boundaries in spawn prompt (see Delegation Rules)
           - Hooks observe tool_use, bskg_query, session lifecycle events
        3. Run capability contract check (pass/fail gate)
           - If FAIL: record as capability_gating_failed, skip to step 7
        4. Parse observations into EvaluationInput
        5. Call evaluation_runner.py:
           python evaluation_runner.py --session-id {session_id} --contract {contract_path}
        6. Read EvaluationResult JSON from runner stdout
           - If debate=True: dual-evaluator protocol produces reconciled scores
        7. Produce EvaluationResult with ScoreCard
        8. Persist result to .vrs/evaluations/results/{workflow_id}.json
        9. Atomic write to .vrs/evaluations/progress.json (update per_workflow_status)

    except Exception as e:
        # Intra-stage failure policy: try/continue
        write {workflow_id}.failed.json with error context to .vrs/evaluations/
        increment consecutive_failure_counter
        check circuit_breaker(consecutive_failure_counter, infrastructure_failure_type)
```

## Delegation Rules

### PROHIBITED

The following operations are **never** permitted from the orchestrator session
(the session running /vrs-test-suite itself):

- `alphaswarm query` -- evaluation must not query the knowledge graph
- `alphaswarm build-kg` -- evaluation must not build knowledge graphs
- `Read` on `.sol` files -- evaluation must not read Solidity source code
- `Read` on `.py` files outside `tests/` and `src/alphaswarm_sol/testing/` -- no production code reading
- `Read` on `vulndocs/` paths -- evaluation must not read vulnerability documentation
- `Write` to `contracts/` or `src/` paths -- evaluation must not modify source code
- Any `git push` or `git commit` operations

### ALLOWED

- `Read` on `src/alphaswarm_sol/testing/evaluation/contracts/*.yaml` -- evaluation contracts
- `Read`/`Write` on `.vrs/evaluations/*` -- evaluation results and reports
- `Read` on `.planning/testing/scenarios/**` -- test scenario definitions
- `Read` on `.vrs/schemas/*` -- schema validation
- `Bash` with `python evaluation_runner.py` -- invoke scoring pipeline
- `Bash` with `python -m pytest` on `tests/workflow_harness/` -- verification

### Per-Teammate File Boundaries

When spawning Agent Teams for a workflow evaluation, the spawn prompt MUST
include explicit file boundary instructions AND context isolation.

**Context Isolation Requirement:** Teammates must be spawned with minimal,
focused context. Do NOT let them inherit the full project CLAUDE.md. This
ensures evaluations are realistic — a real user has focused context, not
full development instructions.

**Spawning Protocol (Agent Teams, NOT Task() subagents):**

```python
# 1. Create team (once per sub-wave)
TeamCreate(team_name="eval-{tier}-wave", description="{tier} evaluations")

# 2. Create tasks in shared TaskList
TaskCreate(subject="Evaluate {workflow_id} on {contract}", ...)

# 3. Spawn named teammates with FOCUSED prompt
Task(
    team_name="eval-{tier}-wave",
    name="investigator-{N}",
    subagent_type="general-purpose",
    prompt="""You are evaluating a Solidity contract for security vulnerabilities.

CONTEXT: You are a security investigator. You have access to a knowledge
graph builder and query engine. Your job is to find vulnerabilities.

TOOLS (use ONLY these):
- `uv run alphaswarm build-kg {contract_path}` — build graph
- `uv run alphaswarm query "{query}"` — semantic graph query
- `Read` on {contract_path} ONLY — read the contract source

DO NOT:
- Read CLAUDE.md, .planning/*, docs/*, or any project files
- Read vulndocs/ or vulnerability pattern documentation
- Use git commands or modify files outside .vrs/observations/

OUTPUT: Write debrief.json and exit_report.json to
.vrs/observations/plan09/{workflow_id}/

Check TaskList, claim a task, execute, mark complete."""
)
```

**For the orchestrator session (not teammates),** these boundaries apply:

```
You are evaluating workflow {workflow_id}.

FILE BOUNDARIES:
- You MAY read: {contract_path}, .vrs/evaluations/*, .planning/testing/scenarios/*
- You MUST NOT read: *.sol, vulndocs/*, production src/ outside testing/
- You MUST NOT call: alphaswarm query, alphaswarm build-kg
- You MUST NOT write: contracts/*, src/*
```

### JSONL Contamination Exit Check

After all workflows complete, scan observation JSONL for delegation violations:

```bash
# Check orchestrator session JSONL for prohibited calls
grep -E "alphaswarm (query|build-kg)" .vrs/observations/plan09/*.jsonl | grep "session_type.*orchestrator" && echo "CONTAMINATION: prohibited CLI call" && exit 1
grep -E '"tool":\s*"Read".*\.sol"' .vrs/observations/plan09/*.jsonl | grep "session_type.*orchestrator" && echo "CONTAMINATION: .sol read" && exit 1
echo "Delegate mode: CLEAN"
```

Zero violations required. Any contamination fails the suite.

## Budget and Limits

| Concept | Value | Description |
|---------|-------|-------------|
| `per_workflow_budget_ceiling` | 2700s (45 min) | Default timeout per workflow. After elapsed > ceiling, write `status: interrupted` and proceed to next |
| `per_workflow_total_ceiling_with_debate` | 3600s (60 min) | Binding override when `debate=True`. Maximum: 30 min execution + 15 min debate + 5 min scoring |
| `evaluation_timeout` | 900s | Python scoring layer timeout (evaluator LLM call). Separate from CC skill ceiling |

Budget sanity formula: `total_ceiling >= execution_p95 + debate_p95 + scoring_p95`.
Verify after first Core sub-wave run. [ESTIMATE: update after first Core run]

Between workflow iterations, check `elapsed > per_workflow_budget`. If exceeded,
write `WorkflowStatus(workflow_id, status="interrupted", error="budget_exceeded")`
and proceed to next workflow.

## Kill-File Mechanism

**Kill-file path:** `.vrs/evaluations/kill.signal`

**Polling interval:** Check between every workflow iteration (after completing or
failing one workflow, before starting the next).

**Behavior:** If `kill.signal` exists at poll time:
1. Write `WorkflowStatus` for current queue as `status: skipped, error: "kill_signal"`
2. Finalize progress.json with partial results
3. Write SuiteExitReport with `overall_passed: false` and metadata `kill_signal: true`
4. Exit gracefully -- do not abort mid-workflow

**Creation:** User creates `touch .vrs/evaluations/kill.signal` to request graceful stop.
**Cleanup:** Skill does NOT delete the kill file. User removes it before next run.

## Circuit Breaker

**Trigger:** 3 consecutive workflows produce `status: failed` with identical
`infrastructure_failure_type` values.

**Tier-aware thresholds:**
- Core/Important: 3 consecutive identical failures
- Standard: 5 consecutive identical failures

**Behavior on trigger:**
1. HALT stage execution immediately
2. Write `.vrs/evaluations/stage_halt_{stage}_{timestamp}.json` containing:
   ```json
   {
     "stage": "core_subwave_a",
     "halt_reason": "circuit_breaker_3_consecutive",
     "infrastructure_failure_type": "hook_installation_failed",
     "affected_workflow_ids": ["skill-vrs-audit", "skill-vrs-investigate", "skill-vrs-verify"],
     "consecutive_count": 3,
     "recommended_action": "Re-run Plan 02 hook installation"
   }
   ```
3. Human must acknowledge (delete halt file) before stage can resume

**Recommended action lookup:**
- `hook_installation_failed` -> "Re-run Plan 02 hook installation"
- `contract_schema_invalid` -> "Run validate_scenarios.py"
- `delegate_mode_violation` -> "Inspect SKILL.md delegation rules"
- `evaluator_timeout` -> "Check LLM API availability and token limits"
- `session_invalid` -> "Check observation directory permissions and JSONL format"

**Reset:** Counter resets to 0 on any successful workflow completion.

## Sub-Wave Ordering

**Wave 6 Execution Schedule (headless-first with interactive validation gate):**

| Stage | Sub-Wave | Description | Mode |
|-------|----------|-------------|------|
| 1 | Gate 0 | Dry-run on 1 Core investigation workflow | headless |
| 2 | 09c Standard | Headless structural check (~29 skills) | headless |
| IPV Gate | -- | 1 interactive Core dry-run (SendMessage + debrief validation) | interactive |
| 3 | 09a Core | ~10 Core skills, full evaluation | interactive |
| 4 | HITL Gate | Human reviews Core results (joint with Plan 10) | -- |
| 5 | 09b Important | ~15 Important skills, spot-check gate | headless/interactive |
| 6 | Spot-Check | Human spot-checks 3 Important results | -- |

**Within a sub-wave**, workflows execute in natural registration order from
evaluation contracts directory. No dependency ordering within a tier.

**3.2-Critical Workflows (P15-IMP-39):** Workflows tagged `3.2_critical: true`
in their evaluation contract execute in their natural tier position (not
promoted to Stage 1). Wave 6 Exit Report Section 1 reports their
CONCLUSION_SYNTHESIS and EVIDENCE_INTEGRATION scores separately.

**3.2 Readiness Signal:** 3 of 8 critical workflows must score above tier
threshold on CONCLUSION_SYNTHESIS and EVIDENCE_INTEGRATION.

**Standard-tier baseline exclusion (P15-CSC-02):** Standard-tier stub contracts
are evaluated for coverage tracking only. They do NOT contribute to baseline.
`run_reasoning: false` for Standard tier -- structural validation only.

## Pre-Flight Activation

### Gate 0 Dry-Run

Before any sub-wave execution, run the pipeline on 1 Core investigation
workflow in headless mode:

```
/vrs-test-suite --dry-run --tier core --workflow-ids skill-vrs-investigate
```

**Gate 0 criteria (all must pass):**
1. Agent Teams spawned and completed
2. Debrief artifact written to `.vrs/observations/plan09/`
3. Exit report passes schema validation against
   `.vrs/schemas/test_suite_exit_report.schema.json`
4. Delegate mode contamination check passes (zero prohibited calls in
   orchestrator JSONL)

**Gate 0 uses `run_mode=headless`.** Must succeed before pre-flight activation
test. Gate 0 failure HALTS all sub-waves.

### Interactive Pipeline Validation Gate (P15-ADV-1-01)

Between Stage 2 (Standard headless) and Stage 3 (Core), run ONE interactive
Core workflow in dry-run mode:

```
/vrs-test-suite --dry-run --tier core --workflow-ids vrs-attacker
```

**Validates:**
- SendMessage delivery between orchestrator and spawned agents
- `debrief_gate.py` blocking behavior
- Debrief collection produces non-null artifact
- Interactive DimensionScore output is written

Both Stage 1-2 (headless valid) AND this gate (interactive valid) are required
before Stage 3 (Core sub-wave) begins.

### Pre-Flight Activation Test (P11-IMP-13)

After Gate 0 passes, run activation test with 10 prompts:

**5 Matching prompts** (should trigger /vrs-test-suite):
1. "Run the evaluation suite on Core tier skills"
2. "Execute /vrs-test-suite for investigation workflows"
3. "Test all 30 skills with capability checks"
4. "Run skill evaluations with debate enabled"
5. "Evaluate Core investigation skills with dry-run"

**5 Non-matching prompts** (should NOT trigger /vrs-test-suite):
1. "Run a security audit on contracts/Vault.sol"
2. "Build the knowledge graph for this protocol"
3. "Investigate the reentrancy vulnerability in withdraw()"
4. "Create a new bead for finding FND-001"
5. "Check the health status of the system"

**Gate:** 10/10 required. If < 10/10, HALT suite execution. Do not proceed
to any sub-wave.

**Record:** Write activation test result to `.vrs/evaluations/progress.json`:
```json
{
  "activation_test": {
    "matching": 5,
    "non_matching": 5,
    "score": 10,
    "result": "pass",
    "timestamp": "2026-02-26T..."
  }
}
```

## Intra-Stage Failure Policy

**Model:** Try/continue (P15-ADV-4-02). Failed workflows do NOT halt the stage.

**On workflow failure:**
1. Write `{workflow_id}.failed.json` to `.vrs/evaluations/` with:
   ```json
   {
     "workflow_id": "skill-vrs-audit",
     "status": "failed",
     "infrastructure_failure_type": "evaluator_timeout",
     "error": "Evaluation runner timed out after 900s",
     "timestamp": "2026-02-26T...",
     "stage": "core_subwave_a"
   }
   ```
2. Increment consecutive failure counter
3. Check circuit breaker (see Circuit Breaker section)
4. If circuit breaker not triggered, proceed to next workflow

**Wave completion requirement:** ALL workflows must have either:
- Exit report (`.vrs/evaluations/results/{workflow_id}.json`), OR
- Failure record (`.vrs/evaluations/{workflow_id}.failed.json`)

**No silent gaps.** Any workflow_id without one of these two records means the
wave is incomplete.

**Escalation threshold:** If `.failed.json` count > 20% of wave (> 6 of 30),
escalate to human review before proceeding to next sub-wave.

**Stage gate structured summary:**
```json
{
  "completed": 8,
  "failed": 2,
  "skipped": 0,
  "failure_reasons": ["evaluator_timeout", "hook_crash"],
  "gate_passage": true
}
```
Gate passage requires: `completed >= 8` AND zero `delegate_mode_violation` failures.

## Progress Tracking

Atomic write to `.vrs/evaluations/progress.json` after each workflow completes
or fails. The file is the single source of truth for suite state.

```json
{
  "suite_id": "plan09-2026-02-26T...",
  "plan": "3.1c-09",
  "tier": "core",
  "started_at": "2026-02-26T...",
  "activation_test": { "matching": 5, "non_matching": 5, "score": 10, "result": "pass" },
  "gate_0": { "status": "passed", "workflow_id": "skill-vrs-investigate", "timestamp": "..." },
  "ipv_gate": { "status": "passed", "workflow_id": "vrs-attacker", "timestamp": "..." },
  "sub_waves": {
    "standard": { "total": 29, "completed": 29, "failed": 0, "skipped": 0 },
    "core": { "total": 10, "completed": 9, "failed": 1, "skipped": 0 },
    "important": { "total": 15, "completed": 14, "failed": 1, "skipped": 0 }
  },
  "per_workflow_status": [
    { "workflow_id": "skill-vrs-audit", "status": "completed", "tier": "core", "capability_check": "passed" },
    { "workflow_id": "skill-vrs-investigate", "status": "completed", "tier": "core", "capability_check": "passed" }
  ],
  "three_two_critical": {
    "total": 8,
    "above_threshold": 3,
    "readiness_signal": true,
    "workflows": [
      { "workflow_id": "skill-vrs-audit", "conclusion_synthesis": 72, "evidence_integration": 68, "above_threshold": true }
    ]
  },
  "delegate_mode": { "status": "clean", "violations": 0 },
  "updated_at": "2026-02-26T..."
}
```

**Atomic write pattern (~40 LOC):**
1. Build updated progress dict in memory
2. Write to `.vrs/evaluations/progress.json.tmp`
3. `os.replace(tmp_path, final_path)` for atomic rename
4. This prevents partial reads if another process checks progress mid-write

## Observation Directory

All observation data for this plan writes to:
`.vrs/observations/plan09/`

Session-scoped subdirectories: `.vrs/observations/plan09/{session_id}/`

## Tier 2 Standalone Test (P11-ADV-5-01)

If Plan 07 is complete (ReasoningEvaluator with LLM scoring operational),
execute Tier 2 evaluation: LLM quality evaluation using
`claude -p --output-format json` independently of Plan 07's `--json-schema`.

If Plan 07 is NOT complete, execute Tier 1 only (structural checks +
heuristic scoring). Document as `tier2_status: deferred` in progress.json.
