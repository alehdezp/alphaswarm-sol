# Testing Context Overview

**Purpose:** Provide a minimal, load-safe overview for selecting the correct testing workflow.

## Non-Negotiables

- LIVE execution only for validation and E2E.
- claude-code-controller only for interactive tests.
- External ground truth required for validation claims.
- Full transcripts and reports for every run.
- Dedicated demo claude-code-agent-teams session per workflow run.
- `/gsd-plan-phase` must generate derived checks/research artifacts (no hardcoded expected outcomes).

## Real-World Definition

A test is real-world only if it uses the CLI in a dedicated demo claude-code-controller session, with isolation, live execution, and captured transcripts.

## How Everything Fits Together

- Rules live in ` .planning/testing/rules/canonical/ ` and are mandatory.
- Workflows in ` .planning/testing/workflows/ ` define exact test execution.
- Guides in ` .planning/testing/guides/ ` explain prompting, evidence, and debugging.
- Testing skill hierarchy lives in ` .planning/testing/rules/canonical/TESTING-FRAMEWORK.md `.
- Use the index to load only what you need.

## Testing Architecture Hierarchy

### Phase 3.1c: Smart Adaptive Testing Framework (PRIMARY)

The reasoning-based evaluation framework IS the testing framework. It:
- Tests all 30+ skills with capability + reasoning evaluation
- Tests all 21+ agents with behavioral + reasoning evaluation
- Tests full orchestrator flow with multi-agent evaluation
- Provides the continuous improvement loop (Test -> Evaluate -> Improve -> Re-test)
- Evaluates reasoning quality, not just output correctness
- All skill/agent/orchestrator tests are in Phase 3.1c (not 3.1b)

### Phase 3.1b: Testing Infrastructure Foundation (SUPPORTING)

Provides the plumbing that 3.1c depends on:
- Controller + Python bridge (claude-code-controller)
- TranscriptParser + data model (tool call extraction)
- Hook registration architecture (`.claude/settings.json` pattern)
- Core harness (WorkspaceManager, scenario runner)
- Scenario DSL (YAML tasks, trials, graders)
- Test project corpus (10 curated scenarios + dynamic generation guidelines)

## What To Load Next

Select a single workflow guide based on intent:

- CLI install or first run
  ` .planning/testing/workflows/workflow-cli-install.md `
- Skills and skill chaining
  ` .planning/testing/workflows/workflow-skills.md `
- Sub-agents and routing
  ` .planning/testing/workflows/workflow-agents.md `
- Orchestration end-to-end
  ` .planning/testing/workflows/workflow-orchestration.md `
- Audit entrypoint (main orchestrator)
  ` .planning/testing/workflows/workflow-audit-entrypoint.md `
- Graph build and query
  ` .planning/testing/workflows/workflow-graph.md `
- Graph contribution (ablation)
  ` .planning/testing/scenarios/graph/GRAPH-ABLATION.md `
- Performance suite
  ` .planning/testing/perf/PERF-PLAN.md `
- External tools
  ` .planning/testing/workflows/workflow-tools.md `
- E2E validation with ground truth
  ` .planning/testing/workflows/workflow-e2e.md `
- Failure recovery and diagnosis
  ` .planning/testing/workflows/workflow-failure-recovery.md `
- Grammar and in-situ testing
  ` .planning/testing/workflows/workflow-grammar.md `
- Verify instructions before subagents
  ` .planning/testing/workflows/workflow-instruction-verification.md `
- Real environment validation
  ` .planning/testing/workflows/workflow-real-env-validation.md `
- Documentation validation
  ` .planning/testing/workflows/workflow-docs-validation.md `
- Plan generation governance
  ` .planning/testing/PLAN-PHASE-GOVERNANCE.md `
- Reasoning-based evaluation framework
  ` .planning/phases/3.1c-reasoning-evaluation-framework/context.md `
- Phase 3.1b context → 3.1c readiness section for API contracts
  ` .planning/phases/3.1b-workflow-testing-harness/context.md `
- Phase 3.1c context → 3.1b API contracts section for dependency matrix
  ` .planning/phases/3.1c-reasoning-evaluation-framework/context.md `

## Reasoning-Based Evaluation (Phase 3.1c)

Phase 3.1c introduces an intelligent reasoning-based evaluation layer on top of the existing testing framework. Instead of only asserting "did the agent call the right tools?", the reasoning evaluator asks "did the agent REASON correctly?" using LLM-powered assessment (Claude Code subagent, not direct API), Graph Value Scoring, and interactive agent debriefs.

Phase 3.1c has 12 plans covering the full evaluation pipeline:
- 3.1c-01 through 3.1c-08: Core evaluation infrastructure (hooks, data models, parser, GVS, debrief, contracts, evaluator, runner)
- 3.1c-09: Skill Capability + Reasoning Tests (all 30+ skills)
- 3.1c-10: Agent Capability + Reasoning Tests (all 21+ agents)
- 3.1c-11: Orchestrator Flow + Multi-Agent Evaluation (full pipeline)
- 3.1c-12: Improvement Loop + Regression Baseline (continuous improvement)

Key capabilities:
- **Smart dynamic selection:** Each workflow's evaluation contract declares which evaluation components apply, avoiding false positives from blanket application.
- **Continuous improvement loop:** Test -> Evaluate -> Identify Failures -> Improve (sandbox) -> Re-test -> Detect Regression -> Report.
- **Safe sandboxing:** Prompt experiments run against copies in test project `.claude/` folders; production prompts are never modified during testing.

Key locations:
- Per-workflow evaluation contracts: ` tests/workflow_harness/contracts/workflows/ `
- Phase context: ` .planning/phases/3.1c-reasoning-evaluation-framework/context.md `

**All skill/agent/orchestrator tests are in Phase 3.1c (not 3.1b).** This is because these tests require the full evaluation pipeline (capability contracts + reasoning evaluation + debrief + graph value scoring + improvement loop), not just mechanical liveness checks.

### 3.1b -> 3.1c Handoff Contract

Phase 3.1c extends 3.1b infrastructure. The handoff requires:

| 3.1b Delivers | 3.1c Extends With |
|---|---|
| TranscriptParser (tool calls, messages) | `get_text_between_tools()`, `get_debrief_response()`, `get_graph_queries()` |
| `WorkspaceManager.install_hooks([log_session])` | `install_hooks([observation hooks x5])` |
| `.vrs/` debug artifacts | `.vrs/observations/` hook JSONL |
| Scenario DSL (tasks, trials, graders) | `evaluation:` block (contract, GVS, reasoning) |
| Controller events (`agent:spawned`, `task:completed`) | `agent_transcript_path` in `agent:exited`, `SendMessage` content |
| Regression baseline (pass@k) | internal regression signals (graph, reasoning, evidence) — for before/after comparison only |
| `env_manager.ts` (git versioning) | sandbox `.claude/` copying for prompt experiments |
| Capability contracts (binary pass/fail) | Evaluation contracts (breakage detection + improvement identification, internal regression signals) |
| (no skill/agent/orchestrator tests) | Skill tests (3.1c-09), Agent tests (3.1c-10), Orchestrator tests (3.1c-11) |

## Reference Docs

- claude-code-controller usage
  ` .planning/testing/guides/guide-claude-code-controller.md `
- Evidence packs and reports
  ` .planning/testing/guides/guide-evidence.md `
- Iteration protocol and remediation
  ` .planning/testing/guides/guide-iteration.md `
- Ground truth provenance
  ` .planning/testing/guides/guide-ground-truth.md `
- Inventory and coverage
  ` .planning/testing/guides/guide-inventory.md `
- Add new workflows
  ` .planning/testing/guides/guide-new-workflow.md `
- Agent and LLM prompting
  ` .planning/testing/guides/guide-agent-prompting.md `
- Alignment campaign
  ` .planning/testing/guides/guide-alignment-campaign.md `
- Jujutsu workspaces
  ` .planning/testing/guides/guide-jujutsu-workspaces.md `
- Skill reviewer
  ` .planning/testing/guides/guide-skill-reviewer.md `
- Agent debugging and drift checks
  ` .planning/testing/guides/guide-agent-debugging.md `
- Orchestration progress and resume
  ` .planning/testing/guides/guide-orchestration-progress.md `
- Tier C pattern testing
  ` .planning/testing/guides/guide-tier-c.md `
- Context quality gate
  ` .planning/testing/guides/guide-context-quality.md `
- Pattern lattice verification
  ` .planning/testing/guides/guide-pattern-lattice.md `
- Pattern evaluation for agent reasoning
  ` .planning/testing/guides/guide-pattern-evaluation.md `
- Pattern discovery from anomalies
  ` .planning/testing/guides/guide-pattern-discovery.md `
- VQL minimum query set
  ` .planning/testing/vql/VQL-LIBRARY.md `
- Graph usage metrics
  ` docs/reference/graph-usage-metrics.md `
- Tool maximization matrix
  ` .planning/testing/TOOL-MAX-MATRIX.md `
- Settings file control
  ` .planning/testing/guides/guide-settings.md `
- Command discovery
  ` .planning/testing/guides/guide-command-discovery.md `
- Command inventory
  ` .planning/testing/COMMAND-INVENTORY.md `
- Alignment ledger
  ` .planning/testing/ALIGNMENT-LEDGER-TEMPLATE.md `
- Coverage map
  ` .planning/testing/COVERAGE-MAP.md `
- Operator status contract
  ` .planning/testing/OPERATOR-STATUS-CONTRACT.md `
- Decision log schema
  ` .planning/testing/DECISION-LOG-SCHEMA.md `
- Ground truth provenance index
  ` .planning/testing/ground_truth/PROVENANCE-INDEX.md `
- Docs validation status
  ` .planning/testing/DOCS-VALIDATION-STATUS.md `
- Scenario manifest
  ` .planning/testing/scenarios/SCENARIO-MANIFEST.yaml `
- Tier B/C scenario library
  ` .planning/testing/scenarios/tier-bc/SCENARIO-LIBRARY.md `
- Economic model library
  ` .planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md `
- Hard-case coverage
  ` .planning/testing/scenarios/hard-cases/HARD-CASE-COVERAGE.md `
- Performance scenarios
  ` .planning/testing/scenarios/perf/PERF-SCENARIOS.md `
- Marker registry
  ` .planning/testing/MARKER-REGISTRY.yaml `
- Templates
  ` .planning/testing/templates/ `
- Plan contract schema
  ` .planning/testing/schemas/phase_plan_contract.schema.json `

## Outputs/Artifacts

Generated files you should expect from real runs:

- ` .vrs/testing/runs/<run_id>/transcript.txt `
- ` .vrs/testing/runs/<run_id>/report.json `
- ` .vrs/testing/runs/<run_id>/environment.json `
- ` .vrs/testing/runs/<run_id>/ground_truth.json `
- ` .vrs/testing/runs/<run_id>/manifest.json `
- ` .vrs/testing/state/current.yaml `
- ` .vrs/testing/state/history/ `
- ` .vrs/observations/{session_id}.jsonl ` — hook observation logs
- ` .vrs/testing/runs/{run_id}/reasoning_assessment.json ` — LLM evaluation
- ` .vrs/testing/runs/{run_id}/graph_value_score.json ` — GVS report
- ` tests/workflow_harness/contracts/workflows/*.yaml ` — evaluation contracts
