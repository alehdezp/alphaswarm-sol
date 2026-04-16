# Plan-Phase Governance Contract

**Status:** Canonical (applies to every active phase context)  
**Primary Trigger:** `/gsd-plan-phase`  
**Purpose:** Prevent planning drift by forcing research-backed, non-hardcoded checks that are derived from real phase context and repository evidence.

## Why This Exists

Phase plans become unreliable when they:
- pre-fill pass/fail outcomes without evidence,
- skip precondition discovery,
- use placeholder tests,
- or do not capture drift causes in a comparable way.

This contract makes `/gsd-plan-phase` produce executable, auditable, and improvable plans.

## Non-Hardcoded Rule (Mandatory)

For every plan:
- Checks must be **investigation-first** (`question -> evidence -> derivation -> rule`).
- Thresholds must be **derived** from measured baseline, external source, or explicit human decision.
- Static pass/fail claims without derivation are prohibited.

Allowed static values:
- Protocol-level invariants (e.g., "no dangling references").
- Schema-required presence checks.
- External regulatory/spec constraints with source citation.

## Required `/gsd-plan-phase` Outputs Per Plan

For plan `<plan-id>` in phase `<phase-id>`, generate:

1. `.vrs/debug/phase-<phase-id>/plan-phase/derived-checks/<plan-id>.yaml`  
2. `.vrs/debug/phase-<phase-id>/plan-phase/research/<plan-id>.md`  
3. `.vrs/debug/phase-<phase-id>/plan-phase/hitl-runbooks/<scenario-id>.md`

All generated check files must validate against:
- `.planning/testing/schemas/phase_plan_contract.schema.json`

Template source:
- `.planning/testing/templates/PLAN-INVESTIGATION-CHECKS-TEMPLATE.yaml`
- `.planning/testing/templates/HITL-RUNBOOK-TEMPLATE.md`
- `.planning/testing/templates/DRIFT-RCA-TEMPLATE.md`
- `.planning/testing/templates/PHASE-GATE-CHECKLIST-TEMPLATE.md`

## Mandatory Generation Flow

1. Load phase context (`.planning/phases/<phase>/context.md`).  
2. Resolve preconditions for each plan (inputs, dependencies, blockers, assumptions).  
3. Produce investigation checks from unresolved questions, not from desired outcomes.  
4. Derive thresholds/rules from evidence sources and record derivation method.  
5. Create research task list for missing context and unknowns.  
6. Generate runnable HITL runbook with exact commands, expected signals, failure signatures, and bounded runtime.  
7. Attach anti-hardcoding assertion per check (`why this is derived`).  
8. Register drift severity criteria before implementation begins.  
9. Emit phase entry checklist and phase exit checklist.

## Investigation Check Model

Every check must include:
- `question`: what uncertainty is being reduced.
- `evidence_sources[]`: commands, files, docs, or artifacts.
- `baseline_derivation`: how the baseline/threshold was derived.
- `success_rule`: executable rule using derived inputs.
- `anti_hardcode_assertion`: explicit statement of why the rule is not a fabricated target.
- `requires_research`: true if additional evidence is needed before execution.

## Drift Severity Matrix (Mandatory)

| Severity | Definition | Required Action |
|---|---|---|
| `minor` | Single-plan deviation with no evidence integrity risk | Log drift + local correction in same plan |
| `major` | Multi-plan or gate-affecting deviation | Block plan completion, run RCA, update plan dependencies |
| `critical` | Evidence integrity, safety, or benchmark-validity risk | Freeze phase advancement, run RCA + human checkpoint before resume |

## Drift RCA Contract

Every `major` or `critical` drift event requires RCA file created from:
- `.planning/testing/templates/DRIFT-RCA-TEMPLATE.md`

Required cause code (one primary + optional secondary):
- `bad_assumption`
- `missing_dependency`
- `scope_change`
- `test_gap`
- `tooling_failure`
- `environment_drift`
- `human_process_gap`

## HITL Runbook Contract

Every HITL scenario must provide:
- exact setup/preconditions,
- deterministic command sequence,
- expected observable signals,
- failure signatures,
- stop/resume instructions,
- max runtime budget.

Use:
- `.planning/testing/templates/HITL-RUNBOOK-TEMPLATE.md`

## No-Fake-Tests Policy

Any test file referenced by active phase plan outputs/gates must not be:
- `@pytest.mark.skip`
- `@pytest.mark.xfail`
- placeholder body (`pass`) as final assertion path.

See enforcement rules:
- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`
- `.planning/testing/rules/canonical/VALIDATION-RULES.md`

## Plan-vs-Reality Dashboard

Machine-generated status is mandatory for drift visibility.

Generator:
- `scripts/planning/render_phase_plan_dashboard.py`

Default outputs:
- `.vrs/debug/planning/plan-vs-reality.json`
- `.vrs/debug/planning/plan-vs-reality.md`

## Mandatory Testing Requirements (Phase 3.1d+)

Every GSD phase plan that modifies a workflow MUST include:

| Step | Action | Tool |
|------|--------|------|
| Pre-change | Run affected scenarios, record baseline | `/vrs-test-affected` or `pytest tests/scenarios/ -k "affected"` |
| Implement | Make the change | Normal dev work |
| Validate | Run affected scenarios, compare to baseline | `/vrs-test-scenario <ID>` |
| Feedback | Read failure narratives, identify issues | Evaluator produces structured feedback |
| Fix | Address issues identified by feedback | Iterate on implementation |
| Regression | Run ALL scenarios | `/vrs-test-regression` |
| Ship | Only if no regressions | Baseline updated |

Testing skills available:
- `/vrs-test-scenario` — Run single scenario, produce feedback
- `/vrs-test-regression` — Full regression suite, compare to baseline
- `/vrs-test-affected` — Map changed files → affected scenarios
- `/vrs-test-suggest` — Analyze failures, propose improvements

## Phase Entry/Exit Governance

Every active phase must maintain explicit checklists:
- Entry checklist before implementation starts.
- Exit checklist before phase completion is recorded.

Template:
- `.planning/testing/templates/PHASE-GATE-CHECKLIST-TEMPLATE.md`

## Testing Gate Compliance

Every plan task that produces a phase deliverable must include done criteria
requiring:
- Named artifact paths at `.vrs/observations/<phase>/`
- Score above phase-type-specific threshold (from PHASE-TYPE-TAXONOMY.md)

Enforcement: `/gsd-plan-phase` must verify that plan templates include
done criteria with artifact path requirements. Plans without artifact
requirements fail the governance check.

Phase types and their specific requirements:
`.planning/testing/rules/canonical/PHASE-TYPE-TAXONOMY.md`

