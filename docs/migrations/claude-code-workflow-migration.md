# Claude Code Workflow Migration Guide

**Migration from legacy CLI-first documentation assumptions to Claude Code workflow-first architecture.**

**Date:** 2026-02-10

---

## Why This Migration

AlphaSwarm.sol is now documented and specified as:

- **Workflow-first:** Claude Code `/vrs-*` skills are the product interface.
- **Orchestration-centric:** Task lifecycle, markers, and evidence contracts drive correctness.
- **CLI-subordinate:** CLI remains for tool execution, CI, and advanced diagnostics.

Legacy docs that implied "user runs CLI commands first" were updated.

---

## Old vs New Model

| Area | Legacy Assumption | New Contract |
|------|-------------------|--------------|
| User entrypoint | `alphaswarm ...` commands | `/vrs-*` skill workflows in Claude Code |
| Orchestration | Optional/implicit | Mandatory and evidence-checked |
| CLI role | Primary UX | Subagent/dev/CI tooling surface |
| Validation | Command success focused | Marker + task + evidence contracts |
| Documentation claims | Mixed aspirational/current | Explicit current-vs-target framing |

Runtime split note:
- Shipping uses shipped `/vrs-*` subagent workflows.
- Phase-3 testing uses Claude Code Agent Teams features + `ClaudeCodeRunner` (headless `claude --print`) for harnessed validation.

---

## Breaking Changes for Integrators

1. **Primary control plane shifted to workflows.**
   Integrations should invoke and evaluate workflow outputs and evidence artifacts, not raw CLI session text.

2. **Task/evidence contract is now first-class.**
   Reportable findings are expected to include graph links and provenance fields.

3. **Resume/status semantics are workflow-driven.**
   Prefer orchestrated resume paths (`/vrs-orch-resume`) and state artifacts in `.vrs/state/current.yaml`.

4. **Deprecated/stale references removed.**
   References to deprecated agents, old skill paths, and unvalidated benchmark claims were removed or marked as targets.

---

## What Stayed Compatible

- CLI command surface remains available for development and CI.
- Existing graph build/query workflows remain valid as tool-level operations.
- VulnDocs and pattern authoring remain supported with updated workflow framing.

---

## Migration Checklist

- [ ] Update runbooks to use `/vrs-*` workflows as primary entrypoints.
- [ ] Use CLI commands only where tool-level execution is explicitly required.
- [ ] Validate integration outputs against marker/task/evidence contracts.
- [ ] Update internal docs and dashboards to read workflow artifacts (`.vrs/`), not ad-hoc terminal output.
- [ ] Remove references to deprecated skill paths and stale commands.

---

## Updated Documentation Areas

- Core docs: `docs/index.md`, `docs/PHILOSOPHY.md`, `docs/claude-code-architecture.md`
- Getting started: `docs/getting-started/installation.md`, `docs/getting-started/first-audit.md`
- Guides: skills, queries, beads, testing, patterns, VulnDocs authoring
- References: agents, CLI, graph-first template, tools overview, testing framework
- Workflows/diagrams: install/audit/tools/graph/playbooks + architecture diagrams
- Repo-level entrypoint: `README.md`

---

## Validation Strategy After Migration

Use this order for confidence:

1. Skill invocation and workflow smoke tests
2. Orchestrator flow tests (task lifecycle + marker contracts)
3. Evidence provenance and replay tests
4. Negative-control regression tests
5. Benchmark publication (after prior gates pass)

---

*This migration guide defines the documentation contract until Phase 3 implementation gates are fully closed.*
