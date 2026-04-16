# Phase 07.3.1.6 Testing Hardening Context

**Status:** Draft context
**Scope:** Testing-only phase context and requirements
**Purpose:** Build the most comprehensive, reusable, and mistake-resistant testing framework for AlphaSwarm.sol

---

**Important**
This document is context only. It is not an execution plan and must not be treated as one.

## Document Set (Consolidated)

- Context (this file) is the single source of truth for goals, constraints, gates, and non-negotiables.
- Super report contains the authoritative backlog of plan seeds with implementation guidance.
- Plan placeholder exists to prevent accidental execution. Execution plans may be drafted for review, but **must not be executed** until the Definition Gate and Alignment Campaign pass.

## Phase Definition

- **Autonomous execution phase** for a testing framework that forces orchestration to happen and proves it with evidence.
- Documentation alignment phase that keeps workflows, skills, and tests consistent over time.
- Not a feature delivery phase and not a refactor phase.

## Execution Model (Core Principle)

**All execution is autonomous via Claude Code controller + claude-code-controller.** Human intervention is only required for final plan confirmation when confidence is below threshold.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS EXECUTION MODEL                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Plan Execution (Autonomous via Claude Code + claude-code-controller)             │
│   ├─ claude-code-agent-teams sessions launch automatically (controller-driven)         │
│   ├─ workflows execute without human watching                       │
│   ├─ evidence is captured automatically                             │
│   ├─ gates pass/fail based on defined criteria                      │
│   └─ system self-validates: "Does output match expected?"           │
│                                                                      │
│   Autonomous Validation                                              │
│   ├─ Transcript meets thresholds? (lines, duration, markers)        │
│   ├─ All required artifacts present?                                │
│   ├─ Test assertions pass?                                          │
│   └─ Evidence pack validates against schema?                        │
│                                                                      │
│   IF all gates pass AND confidence >= 0.95:                         │
│       → Plan marked COMPLETE (no human needed)                      │
│                                                                      │
│   IF gates pass BUT confidence < 0.95:                              │
│       → Request human confirmation with:                            │
│         • Scenario tested                                           │
│         • Workflow executed                                         │
│         • Where to verify (transcript path)                         │
│         • How to verify (what to check)                             │
│         • Expected outcome vs actual                                │
│       → Human confirms: "matches" or "doesn't match"                │
│                                                                      │
│   IF any gate fails:                                                 │
│       → Plan marked FAILED (iterate autonomously)                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Human confirmation is NOT involvement during execution.** Humans only confirm final plan status when the system is uncertain.

## Pre-Phase Reality (Must Be Acknowledged)

**CRITICAL:** The system does not orchestrate yet, and no real testing has been executed.

| Component | Current State | Target State (After Testing Framework) |
|---|---|---|
| `vrs-audit` | Describes workflow, does not orchestrate | Spawns tasks and subagents with evidence |
| `vrs-attacker` | Definition exists, not invoked | Spawned and produces exploit analysis |
| `vrs-defender` | Definition exists, not invoked | Spawned and produces mitigations |
| `vrs-verifier` | Definition exists, not invoked | Arbitrates attacker/defender debate |
| Orchestration | Theoretical in docs | Real tool calls in transcripts |

The testing framework is being built to force orchestration and prove it with transcripts.

## Root Cause: Why Skills Don’t Orchestrate

The missing behavior is primarily caused by missing explicit tool directives in skill prompts.

- Skill prompts describe orchestration but do not instruct Claude Code to invoke TaskCreate/TaskUpdate, spawn subagents, or execute tool calls.
- This yields symptoms: no TaskCreate/TaskUpdate markers, no subagent spawns, and findings produced without a task lifecycle.
- Plans must target prompt-level tool usage, not documentation-only updates.

## Phase Goals (Non-Negotiable)

- Make testing evidence-first and claude-code-agent-teams-driven across all workflows.
- Prove Tier B/C reasoning on complex vulnerabilities using graph + VQL, not pattern matching.
- Build a plan-seeded framework where every workflow has a proof run and evidence pack.
- Keep testing docs aligned with workflow contracts at all times.

## Non-Goals

- Add new product features.
- Replace core architecture or redesign major components.
- Use simulated execution for validation.
- Delete skills or agents; extract only the strongest testing ideas into the framework.

## Constraints And Assumptions

- Validation runs use Claude Code subscriptions only. API-call handling is out of scope.
- No direct comparison to static analysis tools in this phase. Success is Tier B/C reasoning with graph + VQL.
- Dedicated demo claude-code-agent-teams sessions are mandatory for interactive tests.

## External Ground Truth Requirement (Validation)

- Any plan or scenario that claims validation or E2E correctness **must** reference external provenance.
- Scenario manifests must include `requires_ground_truth: true` and a `ground_truth_ref` that points to `.planning/testing/ground_truth/PROVENANCE-INDEX.md`.
- If provenance is missing, the scenario is **blocked** and the run is invalid.

## Required Sources Of Truth

- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`
- `.planning/testing/rules/canonical/VALIDATION-RULES.md`
- `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md`
- `.planning/testing/rules/canonical/TESTING-PHILOSOPHY.md`
- `.planning/testing/rules/claude-code-controller-REFERENCE.md` and `.planning/testing/rules/canonical/claude-code-controller-instructions.md`
- `skills/enforce-testing-rules.md`
- `docs/reference/workflows.md`
- `docs/reference/testing-framework.md`

## Lattice Map (How To Think About Coverage)

Use this lattice to locate every plan seed and avoid blind spots.

Axis 1: Workflow stage (install, init, build-kg, audit, verify, report).
Axis 2: Evidence quality (transcript, evidence pack, ground truth, human review).
Axis 3: Reasoning depth (Tier A, Tier B, Tier C, VQL usage, context usage).

## Testing Architecture (Controller → Subject → Evaluator)

- Controller is your Claude Code session.
- Subject is an isolated Claude Code session driven by claude-code-controller.
- Evaluator compares transcripts to criteria and ground truth.
- Evidence packs are required for every run.

## Evidence And Iteration (Human-Like)

- Run, observe, hypothesize, adjust, re-run.
- Require evidence of change and improvement.
- Track iteration artifacts and transcript diffs.

## Orchestration Definition (Markers Required)

A skill “orchestrates” only when transcripts show all required markers:

- TaskCreate and TaskUpdate with task IDs.
- Subagent spawn markers (attacker, defender, verifier).
- Graph, context, and tool usage markers.
- `.vrs/state/current.yaml` updated at stage transitions.
- Progress guidance with stage, next step, and resume hint.

These markers are the assertion basis for tests.

## Effectiveness Objective (Tier B/C Reasoning)

The framework must prove LLMs detect complex logic, authorization, and economic-loss vulnerabilities using:

- Tier B/C pattern guidelines.
- VQL graph queries and graph-first reasoning.
- Protocol and economic context packs (real or simulated).

Use lattice-based scenario design for Tier B/C validation.
Reference: `.planning/testing/guides/guide-pattern-lattice.md`.

## Economic Context Complexity (Bypass Required)

When scenarios embed mock economic context, the framework must allow an explicit bypass:

- Mark simulated context in settings or scenario metadata.
- Skip context generation when mock context is present.
- Emit transcript markers proving bypass was intentional.

## Testing Scope (All Components Must Be Covered)

- Installation and first-run workflow.
- CLI entrypoints and help output.
- Knowledge graph build and query flows.
- Protocol and economic context generation.
- External tools integration and tool markers.
- Pattern detection across Tier A, B, and C.
- Complex logic/auth/economic bugs validated via Tier B/C and VQL queries.
- TaskCreate and TaskUpdate lifecycle for all findings.
- Subagent routing and scope enforcement.
- Verification, debate, and false positive handling.
- Progress, resume, and restart semantics.
- Evidence pack creation and storage.
- Documentation validation and alignment checks.

## Dedicated Demo Session Policy (Non-Negotiable)

- Every interactive test runs in a dedicated demo claude-code-agent-teams session.
- Standard label format: `vrs-demo-{workflow}-{timestamp}`.
- Demo sessions must never be shared with development work.
- Parallel runs must use separate labels and separate worktrees or run directories.

## Worktree Strategy (Reusable Scenarios)

- One worktree per workflow scenario.
- Re-run only the isolated workflow, not the entire E2E suite.
- Roll back the worktree between runs to measure progress.
- Parallel scenarios must not share state or evidence paths.

## Alignment Campaign (Blocking)

- Build an alignment ledger mapping workflow → skills → subagents → commands → transcripts.
- Update `workflow_refs` in registries and validate with `scripts/validate_workflow_refs.py`.
- Run claude-code-controller tests per the coverage spiral and record evidence.
- Update docs first, then skills and subagents, then re-run tests.

## Human Validation Touchpoints (Fast Review)

- First successful install + init transcript.
- First audit entrypoint transcript with TaskCreate/TaskUpdate.
- First progress/resume transcript with stage + next-step guidance.

Provide transcript path + 5-line summary and request a fast Pass/Fail review.

## Definition Gate (Before Any Execution)

- Definitions for EI, CTL, and Tier C gating thresholds are documented.
- Workflow contracts exist in docs and define inputs, outputs, and success criteria.
- Orchestration markers are defined and testable.
- Alignment ledger template exists and validation script is specified.

## Exit Criteria

- All core workflows have evidence-backed transcripts.
- Audit entrypoint shows preflight, tasks, progress guidance, and verification.
- Installation, init, and health check are validated in real sessions.
- Documentation and workflow contracts are aligned with actual behavior.
- Tier B/C complex vulnerability detection is demonstrated with real transcripts.

## Plan Writing Guardrails (For You)

Every plan you write from the super report must include:

1. Goal and scope boundary.
2. Required references and prerequisites.
3. Implementation steps (sequence, dependencies, pitfalls).
4. Evidence artifacts and success criteria.
5. Human validation step if required.
6. Docs to update and cross-links to maintain.

## Ordered Backlog Summary (Condensed)

1. Installation and first-run validation in real claude-code-agent-teams sessions.
2. Evidence standardization and evidence pack schema enforcement.
3. Iteration protocol, diagnostics, and failure taxonomy.
4. Workflow contracts and orchestration marker spec.
5. Audit entrypoint orchestration with progress guidance.
6. Hook enforcement layer for preflight and completion gates.
7. Settings and state enforcement with strict validation.
8. Tier C gating with EI/CTL integration and simulated context bypass.
9. Tool initialization guarantees in audit flow.
10. Complex vulnerability evaluation harness (Tier B/C + VQL).
11. Coverage map, minimum proof runs, and legacy regressions.
12. Documentation validation with live evidence.
13. State concurrency and locking behavior.
14. Idempotent CLI behavior for repeat runs.
15. Exit codes and structured YAML outputs.
16. Graph integrity checks before downstream use.
17. Alignment ledger and readiness evidence table.
18. Registry validation script for workflow refs.
19. UX runbook and progress UI contract.
20. Ground truth acquisition and provenance index.
21. Automation plan and CI enforcement stage.

## Open Definitions

- EI: Economic Intelligence tasks and expected outputs.
- CTL: Definition and placement in audit pipeline.
- Tier C gating thresholds and required label coverage.

## Plan Policy

- Do not execute any plan until the Definition Gate and Alignment Campaign pass.
- Drafting plans for review is allowed, but they remain gated and non-executable until the gate is complete.
- All plans must reference the super report plan seed IDs and required evidence artifacts.
