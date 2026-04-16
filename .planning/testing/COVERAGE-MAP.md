# Workflow Coverage Map

**Purpose:** Show proof status for workflow documentation and testing evidence.

**Note:** Phase 3.1c owns all skill/agent/orchestrator test coverage. Phase 3.1b provides infrastructure only. Skill capability + reasoning tests (3.1c-09), agent behavioral + reasoning tests (3.1c-10), orchestrator flow + multi-agent evaluation (3.1c-11), and improvement loop + regression baseline (3.1c-12) are all Phase 3.1c responsibilities.

**Legend:**
- `tested`: claude-code-controller transcript exists and is linked
- `no-proof`: no transcript yet; blocker reason provided

**Updated:** 2026-02-11

## Coverage (untested first)

| Workflow | Proof Status | Transcript | Scenario | Worktree/Run Dir | Blocker/Reason | Priority |
|---|---|---|---|---|---|---|
| `.planning/testing/workflows/workflow-audit-entrypoint.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P0 |
| `.planning/testing/workflows/workflow-orchestration.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P0 |
| `.planning/testing/workflows/workflow-e2e.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P0 |
| `.planning/testing/workflows/workflow-cli-install.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P1 |
| `.planning/testing/workflows/workflow-graph.md` | **tested** | Plan 3.1c.1-04 | cli-smoke-wave1 | Agent Teams (worktree isolation) | Verified: build-kg, query --graph, cross-contamination, concurrent race, staleness detection, non-git fallback. Evidence: `.vrs/observations/plan04/` | P1 |
| `.planning/testing/workflows/workflow-skills.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P1 |
| `.planning/testing/workflows/workflow-agents.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P1 |
| `.planning/testing/workflows/workflow-tools.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P1 |
| `.planning/testing/workflows/workflow-failure-recovery.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P1 |
| `.planning/testing/workflows/workflow-instruction-verification.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P1 |
| `.planning/testing/workflows/workflow-docs-validation.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P2 |
| `.planning/testing/workflows/workflow-grammar.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P2 |
| `.planning/testing/workflows/workflow-real-env-validation.md` | no-proof | | none | n/a | No claude-code-controller transcript captured yet. | P2 |

## Next Proofs To Capture

- `.planning/testing/workflows/workflow-audit-entrypoint.md`
- `.planning/testing/workflows/workflow-orchestration.md`
- `.planning/testing/workflows/workflow-e2e.md`

## Reasoning-Based Evaluation Coverage (Phase 3.1c — Planned)

**Status:** Not yet implemented. Phase 3.1c has 12 plans covering evaluation infrastructure and all skill/agent/orchestrator tests. Evaluation contracts will be created for all 24 shipped workflows.

| Workflow Category | Workflows | Evaluation Contract | Status |
|---|---|---|---|
| Investigation | vrs-attacker, vrs-defender, vrs-verifier, vrs-secure-reviewer | Full (GVS + reasoning + debrief) | planned |
| Tool Integration | vrs-tool-slither, vrs-tool-aderyn, vrs-tool-mythril, vrs-tool-coordinator | Focused (tool execution + result parsing) | planned |
| Orchestration | vrs-audit, vrs-verify, vrs-debate, vrs-investigate | Full (multi-agent debrief + pipeline + reasoning) | planned |
| Support | vrs-health-check, vrs-bead-*, vrs-orch-*, vrs-pattern-*, vrs-context-pack, vrs-test-* | Lite (deterministic + correctness) | planned |

### Phase 3.1c Plan Coverage

| Plan | Scope | Status |
|---|---|---|
| 3.1c-01: Observation Hooks + Writer | 5 hooks + shared JSONL writer | planned |
| 3.1c-02: Assessment Data Structures | Pydantic models (ReasoningAssessment, GraphValueScore, etc.) | planned |
| 3.1c-03: Observation Parser | Mechanical extraction from JSONL observation files | planned |
| 3.1c-04: Graph Value Scorer | Graph query quality scoring + checkbox detection | planned |
| 3.1c-05: Debrief Protocol | Agent debrief (approach pending research) | planned |
| 3.1c-06: Evaluation Contracts | 24 per-workflow YAML evaluation contracts | planned |
| 3.1c-07: Reasoning Evaluator | Claude Code subagent evaluator + 4 prompt templates | planned |
| 3.1c-08: Evaluation Runner | Full pipeline orchestration | planned |
| 3.1c-09: Skill Capability + Reasoning Tests | All 30+ skills with evaluation pipeline | planned |
| 3.1c-10: Agent Capability + Reasoning Tests | All 21+ agents with behavioral + reasoning evaluation | planned |
| 3.1c-11: Orchestrator Flow + Multi-Agent Evaluation | Full pipeline with per-agent evaluation + debrief | planned |
| 3.1c-12: Improvement Loop + Regression Baseline | Safe sandbox prompt experiments + regression detection | planned |
