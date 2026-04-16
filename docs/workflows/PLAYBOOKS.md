# Workflow Playbooks (Draft)

**Purpose:** Provide minimal, operator-facing branching guidance for common workflow variations.

**Status:** Draft placeholder. Will be expanded as audit pipeline is proven (Phase 3+).

## Global Notes
- These playbooks are not guarantees. They describe intended workflow variations and must be validated with testing framework evidence.
- If a workflow is not yet validated, record the gap in `.planning/testing/DOCS-VALIDATION-STATUS.md`.
- Primary interface is Claude Code workflow skills (`/vrs-*`). CLI commands are subordinate tool calls for dev/CI only.
- All workflow commands must use `vrs-*` naming and follow the evidence requirements in `.planning/testing/guides/guide-evidence.md`.

## Playbook A: Graph-Only Run (Skip Context and Tools)
**Goal:** Build and query the graph without context generation or tool runs.

**When to use:**
- You only want graph structure and direct VQL/NL querying.

**Commands (example):**
- `/vrs-audit contracts/` with context/tools disabled in `.vrs/settings.yaml`
- `/vrs-investigate <bead-id>` for focused graph-only follow-up

**Expected outputs:**
- `.vrs/graphs/graph.toon` (or configured graph artifact)
- Query/evidence output from orchestrated workflow

**Notes:**
- Tier C patterns should be gated (context absent).
- Record transcript + evidence pack.

## Playbook B: Context-Skip Audit (Tier C Gated)
**Goal:** Run audit workflow but explicitly skip context generation.

**When to use:**
- You want Tier A/B only, or testing without context artifacts.

**Commands (example):**
- `/vrs-audit contracts/` with `context.economic.enabled=false` in `.vrs/settings.yaml`

**Expected outputs:**
- Audit report with Tier C marked unknown or skipped

**Notes:**
- Must emit explicit bypass marker if simulated context is used.

## Playbook C: Pattern Subset Validation
**Goal:** Test a specific pattern set or label subset against a target scope.

**When to use:**
- Focused validation of a small pattern family or label class.

**Commands (example):**
- `/vrs-investigate <bead-id>`
- `/vrs-verify <bead-id>`

**Expected outputs:**
- Query results + evidence references

**Notes:**
- Use Tier B/C harness rules if reasoning is required.

## Playbook D: Resume / Rollback
**Goal:** Resume a run or roll back to a checkpoint.

**When to use:**
- A run failed or needs to continue from a known checkpoint.

**Commands (example):**
- `/vrs-orch-resume <pool-id>`
- `/vrs-audit contracts/ --resume <run-id>` (if supported by active workflow contract)

**Expected outputs:**
- Updated `.vrs/state/current.yaml`
- Updated session status extras

**Note:** Resume functionality is evolving; check `docs/workflows/workflow-progress.md` and `.planning/STATE.md` for current capability status.

## Playbook E: Tools-Skip Audit
**Goal:** Run audit without static tool execution.

**When to use:**
- You need a quick pass and accept missing tool evidence.

**Commands (example):**
- `/vrs-audit contracts/` with tools disabled in `.vrs/settings.yaml`

**Expected outputs:**
- Audit report with tool section explicitly marked skipped

---

**Next Expansion Targets:**
- Add explicit input/output schemas per playbook
- Add evidence requirements per branch
- Add decision log references per run
- Add operator status queries for tasks and outputs
