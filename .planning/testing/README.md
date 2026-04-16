# Testing Framework Docs

**Scope:** Testing-only documentation for AlphaSwarm.sol
**Goal:** Real-world claude-code-controller validation of every workflow, skill, agent, and orchestration path

---

## How To Use These Docs

Use progressive disclosure to minimize context size.

1. Start with `.planning/testing/DOC-INDEX.md` for routing.
2. Load the specific context doc that matches your intent.
3. Load a single workflow guide for the exact feature you are testing.
4. Only load detailed references when you execute the test.

Top-level pointer in planning:

- ` .planning/TESTING-INDEX.md `

## Documentation Layers

- Layer 1: Index
  ` .planning/testing/DOC-INDEX.md `
- Layer 2: Context
  ` .planning/testing/CONTEXT-OVERVIEW.md `
- Layer 3: Detail
  ` .planning/testing/workflows/ ` and ` .planning/testing/guides/ `

## Canonical Rules

The canonical rules live in ` .planning/testing/rules/canonical/ `. This folder contains testing-focused summaries and references. If there is any conflict, the canonical rules in ` .planning/testing/rules/canonical/ ` win.

## Quick Start

If you need to test a specific area, use these routes:

- CLI install or first run
  Load ` .planning/testing/workflows/workflow-cli-install.md `
- Skills and skill chaining
  Load ` .planning/testing/workflows/workflow-skills.md `
- Sub-agents and routing
  Load ` .planning/testing/workflows/workflow-agents.md `
- Orchestration end-to-end
  Load ` .planning/testing/workflows/workflow-orchestration.md `
- Audit entrypoint (main orchestrator)
  Load ` .planning/testing/workflows/workflow-audit-entrypoint.md `
- Graph build and query
  Load ` .planning/testing/workflows/workflow-graph.md `
- External tools
  Load ` .planning/testing/workflows/workflow-tools.md `
- E2E validation with ground truth
  Load ` .planning/testing/workflows/workflow-e2e.md `
- Failure recovery and diagnosis
  Load ` .planning/testing/workflows/workflow-failure-recovery.md `
- Grammar and in-situ validation
  Load ` .planning/testing/workflows/workflow-grammar.md `
- Verify instructions before subagents
  Load ` .planning/testing/workflows/workflow-instruction-verification.md `
- Add a new workflow test
  Load ` .planning/testing/guides/guide-new-workflow.md `
- Real environment validation
  Load ` .planning/testing/workflows/workflow-real-env-validation.md `
- Validate documentation itself
  Load ` .planning/testing/workflows/workflow-docs-validation.md `
- Prompt an agent or LLM correctly
  Load ` .planning/testing/guides/guide-agent-prompting.md `
- Run the alignment campaign
  Load ` .planning/testing/guides/guide-alignment-campaign.md `
- Use jj workspace scenarios
  Load ` .planning/testing/guides/guide-jujutsu-workspaces.md `
- Run the skill reviewer
  Load ` .planning/testing/guides/guide-skill-reviewer.md `
- Debug agent behavior and drift
  Load ` .planning/testing/guides/guide-agent-debugging.md `
- Orchestration progress and resume
  Load ` .planning/testing/guides/guide-orchestration-progress.md `
- Iteration protocol and remediation
  Load ` .planning/testing/guides/guide-iteration.md `
- Tier C pattern testing
  Load ` .planning/testing/guides/guide-tier-c.md `
- Context quality gate
  Load ` .planning/testing/guides/guide-context-quality.md `
- Pattern lattice verification
  Load ` .planning/testing/guides/guide-pattern-lattice.md `
- Pattern evaluation for agent reasoning
  Load ` .planning/testing/guides/guide-pattern-evaluation.md `
- Plan generation governance (`/gsd-plan-phase`)
  Load ` .planning/testing/PLAN-PHASE-GOVERNANCE.md `
- Reasoning-based workflow evaluation
  Load ` .planning/phases/3.1c-reasoning-evaluation-framework/context.md `
- Render plan-vs-reality dashboard
  Run ` python scripts/planning/render_phase_plan_dashboard.py `
- Pattern discovery from anomalies
  Load ` .planning/testing/guides/guide-pattern-discovery.md `
- VQL minimum query set
  Load ` .planning/testing/vql/VQL-LIBRARY.md `
- Graph usage metrics
  Load ` docs/reference/graph-usage-metrics.md `
- Graph ablation scenarios
  Load ` .planning/testing/scenarios/graph/GRAPH-ABLATION.md `
- Performance suite
  Load ` .planning/testing/perf/PERF-PLAN.md `
- Performance scenario list
  Load ` .planning/testing/scenarios/perf/PERF-SCENARIOS.md `
- Tool maximization matrix
  Load ` .planning/testing/TOOL-MAX-MATRIX.md `
- Settings file control
  Load ` .planning/testing/guides/guide-settings.md `
- Resolve missing commands
  Load ` .planning/testing/guides/guide-command-discovery.md `
- Command inventory
  See ` .planning/testing/COMMAND-INVENTORY.md `
- Alignment ledger
  See ` .planning/testing/ALIGNMENT-LEDGER-TEMPLATE.md `
- Coverage map
  See ` .planning/testing/COVERAGE-MAP.md `
- Operator status contract
  See ` .planning/testing/OPERATOR-STATUS-CONTRACT.md `
- Decision log schema
  See ` .planning/testing/DECISION-LOG-SCHEMA.md `
- Ground truth provenance index
  See ` .planning/testing/ground_truth/PROVENANCE-INDEX.md `
- Docs validation status
  See ` .planning/testing/DOCS-VALIDATION-STATUS.md `
- Scenario manifest
  See ` .planning/testing/scenarios/SCENARIO-MANIFEST.yaml `
- Tier B/C scenario library
  See ` .planning/testing/scenarios/tier-bc/SCENARIO-LIBRARY.md `
- Economic model library
  See ` .planning/testing/scenarios/economic/ECONOMIC-MODEL-LIBRARY.md `
- Hard-case coverage
  See ` .planning/testing/scenarios/hard-cases/HARD-CASE-COVERAGE.md `
- Marker registry
  See ` .planning/testing/MARKER-REGISTRY.yaml `
- Templates (scenario manifest + pattern logs)
  See ` .planning/testing/templates/ `

## Outputs/Artifacts

Generated files you should expect from real runs:

- ` .vrs/testing/runs/<run_id>/transcript.txt `
- ` .vrs/testing/runs/<run_id>/report.json `
- ` .vrs/testing/runs/<run_id>/environment.json `
- ` .vrs/testing/runs/<run_id>/ground_truth.json `
- ` .vrs/testing/runs/<run_id>/manifest.json `
- ` .vrs/testing/state/current.yaml `
- ` .vrs/testing/state/history/ `
- ` .vrs/debug/planning/plan-vs-reality.json `
- ` .vrs/debug/planning/plan-vs-reality.md `
- ` .vrs/observations/{session_id}.jsonl `
- ` .vrs/testing/runs/{run_id}/reasoning_assessment.json `
- ` .vrs/testing/runs/{run_id}/graph_value_score.json `

## Required claude-code-controller Usage

Interactive testing must use claude-code-controller only. The canonical reference is in:

- ` .planning/testing/guides/guide-claude-code-controller.md `
- Agent-related testing must follow the skill hierarchy in ` .planning/testing/rules/canonical/TESTING-FRAMEWORK.md `.

## Dedicated Demo Session Requirement

- Every interactive test must run in a dedicated demo claude-code-agent-teams session.
- Use the session label `vrs-demo-{workflow}-{timestamp}` for all runs.
- Do not share demo sessions with development work.
- For parallel runs, use distinct session labels and separate jj workspaces or run directories.

## Updating These Docs

Use the documentation maintenance guidelines:

- ` .planning/testing/DOCS-MAINTAIN.md `

## Doc Freshness Rule

- Any new testing plan seed or scenario heuristic must be reflected in the relevant testing guide.
- Update ` .planning/testing/DOC-INDEX.md ` whenever a guide or workflow doc changes.
