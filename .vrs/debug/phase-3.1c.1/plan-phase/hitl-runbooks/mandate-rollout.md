# HITL Runbook — Testing Mandate Rollout (Plan 3.1c.1-05b)

## Preconditions

- Plan 05a completed: PHASE-TYPE-TAXONOMY.md and TESTING-GATE-TEMPLATE.md exist
- 3.1c.2-CONTEXT.md and 3.1f-CONTEXT.md exist (verified by file read)
- No active editing of governance files by other processes

## Verification Commands

### Check 1: Testing Gate in 3.1c.1-CONTEXT.md (CODE+FRAMEWORK)
```bash
grep -n 'Testing Gate' .planning/phases/3.1c.1-cli-graph-isolation-hardening/3.1c.1-CONTEXT.md
grep 'CODE+FRAMEWORK' .planning/phases/3.1c.1-cli-graph-isolation-hardening/3.1c.1-CONTEXT.md
```
**Expected:** Both return non-empty results.

### Check 2: Testing Gate in 3.1c.2-CONTEXT.md (EVALUATION+FRAMEWORK)
```bash
grep -n 'Testing Gate' .planning/phases/3.1c.2-agent-evaluation-harness-hardening/3.1c.2-CONTEXT.md
grep 'EVALUATION+FRAMEWORK' .planning/phases/3.1c.2-agent-evaluation-harness-hardening/3.1c.2-CONTEXT.md
grep 'Bootstrap Exception' .planning/phases/3.1c.2-agent-evaluation-harness-hardening/3.1c.2-CONTEXT.md
```
**Expected:** All three return non-empty results.

### Check 3: Testing Gate in 3.1f-CONTEXT.md (CODE+EVALUATION)
```bash
grep -n 'Testing Gate' .planning/phases/3.1f-proven-loop-closure/3.1f-CONTEXT.md
grep 'CODE+EVALUATION' .planning/phases/3.1f-proven-loop-closure/3.1f-CONTEXT.md
```
**Expected:** Both return non-empty results.

### Check 4: ROADMAP.md Phase Authoring Requirements
```bash
grep -n 'Phase Authoring Requirements' .planning/ROADMAP.md
grep 'PHASE-TYPE-TAXONOMY.md' .planning/ROADMAP.md
grep 'TESTING-GATE-TEMPLATE.md' .planning/ROADMAP.md
```
**Expected:** All three return non-empty results.

### Check 5: PLAN-PHASE-GOVERNANCE.md Testing Gate Compliance
```bash
grep -n 'Testing Gate Compliance' .planning/testing/PLAN-PHASE-GOVERNANCE.md
grep 'fail the governance check' .planning/testing/PLAN-PHASE-GOVERNANCE.md
```
**Expected:** Both return non-empty results.

### Check 6: Snapshot Protocol in downstream phases
```bash
grep 'Snapshot Protocol' .planning/phases/3.1c.2-agent-evaluation-harness-hardening/3.1c.2-CONTEXT.md
grep 'Snapshot Protocol' .planning/phases/3.1f-proven-loop-closure/3.1f-CONTEXT.md
grep 'jj log' .planning/phases/3.1c.2-agent-evaluation-harness-hardening/3.1c.2-CONTEXT.md
grep 'jj log' .planning/phases/3.1f-proven-loop-closure/3.1f-CONTEXT.md
```
**Expected:** All four return non-empty results.

### Check 7: No premature CONTEXT.md for phases 4+
```bash
find .planning/phases/ -path '*/4*/*CONTEXT*' -o -path '*/5*/*CONTEXT*' -o -path '*/6*/*CONTEXT*' -o -path '*/7*/*CONTEXT*' -o -path '*/8*/*CONTEXT*'
```
**Expected:** Empty output (no files found).

### Check 8: Cross-references resolve
```bash
test -f .planning/testing/rules/canonical/PHASE-TYPE-TAXONOMY.md && echo "TAXONOMY: exists"
test -f .planning/testing/templates/TESTING-GATE-TEMPLATE.md && echo "TEMPLATE: exists"
grep 'Phase-type taxonomy' .planning/testing/rules/canonical/TESTING-FRAMEWORK.md
```
**Expected:** Both files exist. TESTING-FRAMEWORK.md contains taxonomy reference.

### Check 9: PLAN-PHASE-GOVERNANCE.md is additive-only
```bash
git diff .planning/testing/PLAN-PHASE-GOVERNANCE.md | head -50
```
**Expected:** Diff shows only additions at end of file. No deletions or modifications to existing lines.

## Failure Signatures

| Failure | Severity | Action |
|---------|----------|--------|
| Testing Gate absent from a CONTEXT.md | critical | Re-add from template |
| Wrong phase type declared | major | Correct type per taxonomy analysis |
| Snapshot Protocol missing mechanical commands | major | Add jj/git commands per PHASE-TYPE-TAXONOMY.md |
| Existing governance content modified | major | Revert to pre-change version, re-apply additive only |
| CONTEXT.md created for phase 4+ | critical | Delete immediately |
| Cross-reference to non-existent file | major | Verify Plan 05a outputs exist |

## Runtime Budget

All checks are grep/file-existence operations. Total runtime: < 30 seconds.
