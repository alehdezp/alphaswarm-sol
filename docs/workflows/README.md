# Workflow Index

**Purpose:** Route to the correct workflow doc with progressive disclosure.

## How To Use

1. Start with `docs/workflows/CONTEXT.md` for a minimal overview.
2. Load one workflow doc for details.
3. Use `docs/reference/testing-framework.md` for validation expectations.

## Session Starters (Query → Doc)

| If you want to... | Load |
|---|---|
| Understand the complete architecture | `.planning/phases/07.3.1.6-full-testing-hardening/07.3.1.6-PLAN-INDEX.md` |
| Understand the overall workflow system | `docs/workflows/CONTEXT.md` |
| See visual workflow diagrams | `docs/workflows/diagrams/06-complete-architecture-ascii.md` |
| Understand hooks + task orchestration | `docs/reference/claude-code-orchestration.md` |
| Run the main audit entrypoint | `docs/workflows/workflow-audit.md` |
| Build and query the graph | `docs/workflows/workflow-graph.md` |
| Generate protocol + economic context | `docs/workflows/workflow-context.md` |
| Run static analysis tools | `docs/workflows/workflow-tools.md` |
| Orchestrate tasks and subagents | `docs/workflows/workflow-tasks.md` |
| Verify findings and debate | `docs/workflows/workflow-verify.md` |
| Track progress and resume | `docs/workflows/workflow-progress.md` |
| Install and initialize | `docs/workflows/workflow-install.md` |
| Manage beads | `docs/workflows/workflow-beads.md` |
| Run VulnDocs pipeline | `docs/workflows/workflow-vulndocs.md` |
| Use workflow playbooks | `docs/workflows/PLAYBOOKS.md` |
| Understand evaluation pipeline | `docs/workflows/workflow-evaluate.md` |
| Work with use case scenarios | `docs/workflows/workflow-scenarios.md` |
| Run improvement loop | `docs/workflows/workflow-improvement.md` |

## Workflow Catalog

| Workflow | Purpose | Primary Skills | Subagents |
|---|---|---|---|
| Audit Entrypoint | End‑to‑end orchestration | `vrs-audit` | `vrs-attacker`, `vrs-defender`, `vrs-verifier` |
| Install/Init | Setup + health check | `vrs-health-check` | none |
| Graph Build | Build + validate graph | `vrs-graph-contract-validate` | none |
| Context Generation | Protocol + economic context | `vrs-context-pack`, `vrs-economic-context` | `vrs-context-packer` |
| Tool Initialization | Static tools | `vrs-tool-slither`, `vrs-tool-aderyn` | none |
| Task Orchestration | TaskCreate/TaskUpdate flow | `vrs-orch-spawn` | attacker/defender/verifier |
| Verification + Debate | Validate findings | `vrs-verify`, `vrs-debate` | attacker/defender/verifier |
| Progress + Resume | State and checkpoints | `vrs-orch-resume` | none |
| Bead Lifecycle | Create/update/list beads | `vrs-bead-create`, `vrs-bead-update`, `vrs-bead-list` | none |
| VulnDocs Pipeline | Discover/add/refine/test | `vrs:discover`, `vrs:add-vulnerability`, `vrs:refine`, `vrs:test-pattern` | `vrs-pattern-*` |
| Evaluation Pipeline | Score workflow quality | `vrs-test-scenario`, `vrs-test-regression` | `vrs-test-assessor` |
| Use Case Scenarios | Define expected behavior | `vrs-test-scenario`, `vrs-test-affected` | none |
| Improvement Loop | Detect → evaluate → improve | `vrs-test-suggest`, `vrs-test-regression` | `vrs-test-assessor` |

## Skills → Workflow Map

- `vrs-audit` → `docs/workflows/workflow-audit.md`
- `vrs-health-check` → `docs/workflows/workflow-install.md`
- `vrs-graph-contract-validate` → `docs/workflows/workflow-graph.md`
- `vrs-context-pack`, `vrs-economic-context` → `docs/workflows/workflow-context.md`
- `vrs-tool-slither`, `vrs-tool-aderyn` → `docs/workflows/workflow-tools.md`
- `vrs-orch-spawn`, `vrs-orch-resume` → `docs/workflows/workflow-tasks.md`
- `vrs-verify`, `vrs-debate` → `docs/workflows/workflow-verify.md`
- `vrs-orch-resume` → `docs/workflows/workflow-progress.md`
- `vrs-bead-*` → `docs/workflows/workflow-beads.md`
- `vrs-validate-vulndocs`, `vrs:discover`, `vrs:add-vulnerability`, `vrs:refine`, `vrs:test-pattern` → `docs/workflows/workflow-vulndocs.md`
- `vrs-test-scenario`, `vrs-test-regression` → `docs/workflows/workflow-evaluate.md`
- `vrs-test-affected` → `docs/workflows/workflow-scenarios.md`
- `vrs-test-suggest` → `docs/workflows/workflow-improvement.md`

## Reverse Mapping (Skills/Subagents → Workflows)

For debugging and analysis, skills and subagents must link back to workflow contracts:

- Skills basics: `docs/guides/skills-basics.md`
- Skills authoring: `docs/guides/skills-authoring.md`
- Subagent catalog: `docs/reference/agents.md`

These references should remain in sync with this workflow map.

Registry fields used for machine validation:

- `src/alphaswarm_sol/skills/registry.yaml` → `workflow_refs`
- `src/alphaswarm_sol/agents/catalog.yaml` → `workflow_refs`

Validate cross-links with:

```bash
python3 scripts/validate_workflow_refs.py
python3 scripts/validate_workflow_refs.py --strict
```
