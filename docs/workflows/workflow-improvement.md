# Workflow: Detection-Evaluation Improvement Loop

**Purpose:** Define the feedback loop between detection quality and evaluation measurement.

> **v6.0 Status:** First iteration proven in Phase 3.1d-08. Framework supports demand-driven improvement with regression protection.

## The Loop

```
Detect → Evaluate → Identify Gaps → Improve → Re-evaluate → Compare → Ship
  ↑                                                                      │
  └──────────────────────────────────────────────────────────────────────┘
```

1. **Detect** — Run pattern detection on contracts
2. **Evaluate** — Score results against use case scenarios
3. **Identify gaps** — Find lowest-scoring dimensions and failing scenarios
4. **Improve** — Apply targeted fix to pattern/prompt/graph
5. **Re-evaluate** — Run affected scenarios with the fix
6. **Compare** — Check against baseline for regressions
7. **Ship** — Commit only if no regressions

## Demand-Driven Improvement

Don't improve all 466 patterns or all 51 workflows. Improve what scenarios expose as broken.

| Trigger | Action | Measured By |
|---------|--------|-------------|
| UC-AUDIT-001 fails: reentrancy not detected | Fix reentrancy patterns | Recall on reentrancy corpus |
| UC-AUDIT-004 fails: access control missed | Fix access-control patterns | Recall on AC corpus |
| False positive in UC-AUDIT-002 | Tighten pattern conditions | Precision on safe variants |
| Agent didn't use graph first | Update agent prompt | graph_utilization dimension score |

## How To Run an Improvement Cycle

### 1. Identify the target

```bash
# Run scenarios, find the worst performer
uv run pytest tests/scenarios/ -k "audit" -v

# Or use the suggest skill
# /vrs-test-suggest "vrs-audit"
```

### 2. Record baseline

```bash
uv run pytest tests/scenarios/ -k "UC-AUDIT-001"
# Note: baseline scores are automatically tracked by BaselineManager
```

### 3. Make the change

Edit the pattern, prompt, or graph code as needed.

### 4. Re-evaluate

```bash
# Run affected scenarios
uv run pytest tests/scenarios/ -k "UC-AUDIT-001 or UC-ATK-001"
```

### 5. Check for regressions

```bash
# Run full regression suite
uv run pytest tests/scenarios/
```

### 6. Ship if clean

Commit the change + any scenario updates together.

## Improvement Targets

Improvement targets come from three sources:

1. **Scenario failures** — Scenarios whose `must_happen` items fail
2. **Low dimension scores** — Dimensions consistently scoring below 50
3. **Detection baseline** — Categories with low precision or recall

## Detection Baseline (Phase 3.1d-05)

Established on 7 corpus contracts (5 DVDeFi + 2 test contracts):

| Metric | Value | Notes |
|--------|-------|-------|
| Precision | 13.3% | High false positive rate due to overly broad patterns |
| Recall | 83.3% (contract-level) | Most vulnerability classes detected |
| Recall | 64.3% (strict per-vuln) | 4 full + 1 partial out of 7 known vulns |
| Guard Recognition | Improved (was NONE) | nonReentrant suppresses 10 FPs now |

## Pattern Improvements

Targeted by scenario failures and detection baseline:

| Pattern Category | Scenario | Current Status | Key Issue |
|-----------------|----------|---------------|-----------|
| Reentrancy | UC-AUDIT-001 | 100% recall, guards working | Redundancy (14 patterns fire for 1 vuln) |
| Access control | UC-AUDIT-004 | Broad detection, high FP | access-tierb-001 too permissive |
| Oracle | UC-AUDIT-005 | Partial detection | Only generic oracle reads detected |
| Invariant manipulation | Not covered | 0% recall | No pattern for accounting invariants (UnstoppableVault) |
| Governance attacks | Not covered | ~50% partial | No cross-contract governance pattern (SelfiePool) |

## Prompt Improvements

Driven by failure narratives from the evaluation pipeline:

| Failure Narrative | Prompt Change | Agent |
|-------------------|---------------|-------|
| "Didn't formulate hypothesis first" | Add hypothesis-first template | vrs-attacker |
| "Missed guard in inherited contract" | Add "check inherited contracts" | vrs-defender |
| "Agreed without independent evidence" | Strengthen independence constraint | vrs-verifier |
| "Read code before building graph" | Enforce graph-first in all prompts | All agents |

## GSD Phase Integration

Every GSD phase plan that modifies a workflow MUST include:

| Step | Action | Tool |
|------|--------|------|
| Pre-change | Run affected scenarios, record baseline | `pytest tests/scenarios/ -k "affected"` |
| Implement | Make the change | Normal dev work |
| Validate | Run affected scenarios, compare to baseline | `pytest tests/scenarios/ -k "affected"` |
| Feedback | Read failure narratives, identify issues | Evaluator produces structured feedback |
| Fix | Address issues identified by feedback | Iterate on implementation |
| Regression | Run ALL scenarios | `pytest tests/scenarios/` |
| Ship | Only if no regressions | Baseline updated |

## Skills

| Skill | When To Use |
|-------|------------|
| `/vrs-test-suggest` | Get improvement recommendations for a workflow |
| `/vrs-test-scenario` | Test a specific scenario after changes |
| `/vrs-test-regression` | Full regression check before committing |
| `/vrs-test-affected` | Find which scenarios a code change affects |
