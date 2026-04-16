# Boilerplate Update Report - Phase Plan Guardrails

**Generated:** 2026-02-04
**Plan:** 07.3.1.9-08

---

## Summary

Updated "Execution Guardrails" boilerplate text in phase plan files from git worktree to jj workspace terminology.

| Metric | Count |
|--------|-------|
| **Files Updated** | 129 |
| **Files Already Migrated** | 10 |
| **Total with New Pattern** | 139 |
| **Remaining Old Pattern** | 2 (self-referential) |

---

## Text Migration

**Old Pattern:**
```
- Worktree isolation: run any commands or experiments that mutate state in a fresh git worktree; do not use the main worktree and do not reuse worktrees for reruns.
```

**New Pattern:**
```
- Workspace isolation: run any commands or experiments that mutate state in a fresh jj workspace; do not use the main workspace and do not reuse workspaces for reruns.
```

---

## Updated Phases

### Phase 05.x (Semantic Labeling & Core)

| Phase | Files Updated |
|-------|---------------|
| 05-semantic-labeling | 8 |
| 05.1-static-analysis-tool-integration | 10 |
| 05.2-multi-agent-sdk-integration | 10 |
| 05.3-opencode-sdk-refactor | 10 |
| 05.4-vulndocs-patterns-unification | 10 |
| 05.5-agent-execution-context-enhancement | 8 |
| 05.6-orchestration-skill-separation | 9 |
| 05.6.1-toon-format-adoption | 4 |
| 05.7-vulndocs-knowledge-consolidation | 10 |
| 05.8-repository-cleanup-hygiene | 5 |
| 05.9-llm-graph-interface-improvements | 13 |
| 05.10-pattern-context-batch-discovery-orchestration | 13 |
| 05.11-economic-context-agentic-workflow-integrity | 10 |

### Phase 06.x (Release Preparation)

| Phase | Files Updated |
|-------|---------------|
| 06-release-preparation | 7 (including archive) |
| 06.1-rebrand-completion | 2 |

### Phase 07.x (Testing Infrastructure)

| Phase | Files Updated |
|-------|---------------|
| 07.1.1-production-orchestration-hardening | 0 (no guardrails section) |

---

## Files Already Using New Pattern (Pre-Migrated)

These files were created during the 07.3.1.9 phase and already used the new terminology:

- `.planning/phases/07.3.1.9-jujutsu-workspace-migration/07.3.1.9-01-PLAN.md`
- `.planning/phases/07.3.1.9-jujutsu-workspace-migration/07.3.1.9-02-PLAN.md`
- `.planning/phases/07.3.1.9-jujutsu-workspace-migration/07.3.1.9-03-PLAN.md`
- `.planning/phases/07.3.1.9-jujutsu-workspace-migration/07.3.1.9-04-PLAN.md`
- `.planning/phases/07.3.1.9-jujutsu-workspace-migration/07.3.1.9-05-PLAN.md`
- `.planning/phases/07.3.1.9-jujutsu-workspace-migration/07.3.1.9-06-PLAN.md`
- `.planning/phases/07.3.1.9-jujutsu-workspace-migration/07.3.1.9-07-PLAN.md`
- `.planning/phases/07.3.1.9-jujutsu-workspace-migration/07.3.1.9-09-PLAN.md`
- `.planning/phases/07.3.1.9-jujutsu-workspace-migration/07.3.1.9-10-PLAN.md`
- `.planning/phases/07.3.1.7-synthetic-test-environments-workspace-harness/07.3.1.7-02-PLAN.md`

---

## Remaining Old Pattern References

Two files still contain "Worktree isolation" text:

1. **07.3.1.9-08-PLAN.md** - Self-referential (this migration plan shows the old text as what to migrate)
2. **07.3.1.9-09-PLAN.md** - References this plan's migration

These are intentional documentation references, not actual guardrail text.

---

## Historical Content Not Modified

Some completed plans contain "worktree" in their content (scripts, code examples) from before the migration. These are historical records and were NOT modified:

- `07.1.1-production-orchestration-hardening/07.1.1-05-PLAN.md` - References old `worktree.py` module
- `07.3-ga-validation/07.3-*-v6-PLAN.md` - Embedded test scripts using old worktree commands
- `07.3.1.5-full-testing-orchestrator/*.md` - Historical testing infrastructure plans
- `07.3.1.6-full-testing-hardening/*.md` - Historical testing plans

These files document what was implemented before the jj migration and should remain unchanged for historical accuracy.

---

## Verification Commands

```bash
# Count files with new pattern (should be ~139)
grep -rl "Workspace isolation: run any commands" .planning/phases/ --include="*-PLAN.md" | wc -l

# Count files with old pattern (should be 2 - self-referential)
grep -rl "Worktree isolation: run any commands" .planning/phases/ --include="*-PLAN.md" | wc -l

# Verify no "git worktree" in guardrails sections
grep -r "git worktree" .planning/phases/*/\*-PLAN.md 2>/dev/null | grep -i "guardrail"
# Should return empty
```

---

## Migration Script

Created: `scripts/migrate_guardrail_text.sh`

Features:
- Safe batch replacement with sed
- Skips already-migrated files
- Verification of successful replacement
- Summary statistics
