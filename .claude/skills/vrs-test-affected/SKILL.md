---
name: vrs-test-affected
description: |
  Map changed files to affected use case scenarios. Given a list of modified
  files (or auto-detected from git diff), identify which scenarios could be
  impacted and run only those.

  Invoke when user wants to:
  - Test impact of changes: "what scenarios does this change affect?"
  - Targeted testing: "test affected workflows", "/vrs-test-affected"
  - Pre-PR validation: "which scenarios should I run for this PR?"

slash_command: vrs-test-affected
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(pytest*)
  - Bash(uv run*)
  - Bash(git*)
  - Bash(python*)
---

# VRS Test Affected — Change Impact Analysis

You are the **VRS Test Affected** skill. You map code changes to affected scenarios and run targeted tests.

## How to Invoke

```bash
/vrs-test-affected                    # auto-detect from git diff
/vrs-test-affected src/alphaswarm_sol/kg/builder/  # specific paths
/vrs-test-affected --since HEAD~3     # changes in last 3 commits
```

## Workflow

### 1. Detect changed files

```bash
# Auto-detect unstaged + staged changes
git diff --name-only
git diff --cached --name-only

# Or changes since a specific commit
git diff --name-only HEAD~3
```

### 2. Map files to affected scenarios

Use this mapping to identify affected scenarios:

| Changed File Pattern | Affected Scenarios |
|---------------------|-------------------|
| `src/alphaswarm_sol/kg/builder/` | UC-GRAPH-*, UC-AUDIT-* (graph affects all audits) |
| `src/alphaswarm_sol/shipping/skills/vrs-audit/` | UC-AUDIT-* |
| `src/alphaswarm_sol/shipping/skills/vrs-verify/` | UC-VER-* |
| `src/alphaswarm_sol/shipping/skills/vrs-investigate/` | UC-INV-* |
| `src/alphaswarm_sol/shipping/skills/vrs-debate/` | UC-DEB-* |
| `src/alphaswarm_sol/shipping/agents/vrs-attacker*` | UC-ATK-*, UC-AUDIT-* |
| `src/alphaswarm_sol/shipping/agents/vrs-defender*` | UC-DEF-*, UC-VER-* |
| `vulndocs/` | UC-AUDIT-* (pattern changes affect detection) |
| `src/alphaswarm_sol/tools/` | UC-TOOL-* |
| `tests/workflow_harness/` | All scenarios (evaluation infrastructure) |
| `tests/scenarios/` | All scenarios (test infrastructure) |

Also scan scenario YAML files for references to changed paths:
```bash
grep -rl "changed_file_pattern" .planning/testing/scenarios/use-cases/
```

### 3. Run affected scenarios

```bash
# Build a -k filter from affected scenario IDs
uv run pytest tests/scenarios/ -k "UC-AUDIT-001 or UC-AUDIT-003 or UC-ATK-001" -v
```

### 4. Report

```
=== AFFECTED SCENARIOS ===

Changed files: 3
  - src/alphaswarm_sol/shipping/agents/vrs-attacker.md
  - vulndocs/reentrancy/classic/patterns/classic-001.yaml
  - src/alphaswarm_sol/kg/builder/semantic_ops.py

Affected scenarios: 8
  UC-AUDIT-001, UC-AUDIT-002, UC-AUDIT-003, UC-AUDIT-004, UC-AUDIT-005
  UC-ATK-001, UC-ATK-002
  UC-GRAPH-001

Results: 7 passed, 1 failed
  UC-AUDIT-005: FAIL (oracle pattern broken by semantic_ops change)
```

## Key Principle

Run the minimum tests needed to validate changes. Don't run 32 scenarios when 4 are affected. But also don't skip tests that might be impacted — better to over-test than under-test.
