# Docs Validation Status

**Purpose:** Track which testing docs have been validated with real claude-code-controller runs.

**Scope:** `.planning/testing/` workflows and guides. Product docs in `docs/workflows/` are tracked separately (see phase coverage map or runbook).

## Status

- All entries start as pending until a real run is completed.
- Update the status immediately after validation.
- Transcript paths should point to `.vrs/testing/runs/<run_id>/transcript.txt` (canonical run directory).

| Doc | Status | Transcript | Notes |
|---|---|---|---|
| `.planning/testing/workflows/workflow-cli-install.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-graph.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-skills.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-agents.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-orchestration.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-audit-entrypoint.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-tools.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-e2e.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-failure-recovery.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-grammar.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-instruction-verification.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-docs-validation.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/workflows/workflow-real-env-validation.md` | pending | | Blocked: no claude-code-controller transcript captured yet. |
| `.planning/testing/guides/guide-orchestration-progress.md` | pending | | Blocked: depends on validated orchestration workflow transcripts; none captured yet. |
| `.planning/testing/guides/guide-settings.md` | pending | | Blocked: depends on validated cli-install or settings workflow transcript; none captured yet. |
| `.planning/testing/guides/guide-tier-c.md` | pending | | Blocked: depends on a validated Tier C run transcript; none captured yet. |
| `.planning/testing/guides/guide-alignment-campaign.md` | pending | | Blocked: depends on an alignment campaign run transcript; none captured yet. |
| `.planning/testing/guides/guide-jujutsu-workspaces.md` | pending | | Blocked: depends on validated jj workspace scenario transcripts; none captured yet. |
| `.planning/testing/ALIGNMENT-LEDGER-TEMPLATE.md` | pending | | Blocked: no alignment campaign run captured yet. |
| `.planning/testing/guides/guide-skill-reviewer.md` | pending | | Blocked: needs validation against a full skill-reviewer run; only a smoke transcript exists. |
| `.planning/testing/skill-reviewer/SKILL.md` | validated | `.vrs/testing/runs/2026-02-03-skill-reviewer-smoke/transcript.txt` | claude-code-controller smoke test |
| `.planning/testing/skill-reviewer/references/evaluation_checklist.md` | pending | | Blocked: needs validation against a full skill-reviewer run; only a smoke transcript exists. |
| `.planning/testing/skill-reviewer/references/pr_template.md` | pending | | Blocked: needs validation against a full skill-reviewer run; only a smoke transcript exists. |
| `.planning/testing/skill-reviewer/references/marketplace_template.json` | pending | | Blocked: needs validation against a full skill-reviewer run; only a smoke transcript exists. |
| `.planning/testing/skill-reviewer/references/review_report_template.md` | pending | | Blocked: needs validation against a full skill-reviewer run; only a smoke transcript exists. |
