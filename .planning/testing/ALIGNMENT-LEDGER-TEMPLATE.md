# Alignment Ledger Template

**Purpose:** Map workflows to skills, subagents, commands, and evidence so coverage is auditable at a glance.

## Instructions

- Create a copy per phase or per validation campaign.
- Every workflow must have at least one transcript.
- Keep this ledger in sync with:
  - `docs/workflows/README.md`
  - `src/alphaswarm_sol/skills/registry.yaml` (`workflow_refs`)
  - `src/alphaswarm_sol/agents/catalog.yaml` (`workflow_refs`)

## Ledger

| Workflow | Skills | Subagents | Command | Transcript | Status | Notes |
|---|---|---|---|---|---|---|
| `docs/workflows/workflow-audit.md` | `vrs-audit` | `vrs-attacker`, `vrs-defender`, `vrs-verifier` | `/vrs-audit contracts/` | `.vrs/testing/runs/<run_id>/transcript.txt` | pending | |
| `docs/workflows/workflow-graph.md` | `vrs-graph-contract-validate` | none | `uv run alphaswarm build-kg contracts/` | `.vrs/testing/runs/<run_id>/transcript.txt` | pending | |
| `docs/workflows/workflow-context.md` | `vrs-context-pack` | `vrs-context-packer` | `uv run alphaswarm context generate .` | `.vrs/testing/runs/<run_id>/transcript.txt` | pending | |
| `docs/workflows/workflow-tools.md` | `vrs-tool-slither`, `vrs-tool-aderyn` | none | `uv run alphaswarm tools run ...` | `.vrs/testing/runs/<run_id>/transcript.txt` | pending | |
| `docs/workflows/workflow-tasks.md` | `vrs-orch-spawn` | `vrs-attacker` | `/vrs-audit ...` | `.vrs/testing/runs/<run_id>/transcript.txt` | pending | |
| `docs/workflows/workflow-verify.md` | `vrs-verify`, `vrs-debate` | `vrs-verifier` | `/vrs-verify ...` | `.vrs/testing/runs/<run_id>/transcript.txt` | pending | |
