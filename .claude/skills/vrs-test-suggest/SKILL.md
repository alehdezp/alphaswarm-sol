---
name: vrs-test-suggest
description: |
  Analyze scenario failures and produce prioritized improvement suggestions.
  Runs scenarios for a specified workflow, identifies weakest dimensions,
  groups failures by root cause, and proposes specific fixes with confidence.

  Invoke when user wants to:
  - Get improvement ideas: "how can I improve vrs-audit?"
  - Analyze failures: "why is UC-AUDIT-005 failing?"
  - Prioritize work: "what should I fix first?"
  - Suggest improvements: "/vrs-test-suggest vrs-attacker"

slash_command: vrs-test-suggest
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(pytest*)
  - Bash(uv run*)
  - Bash(python*)
  - Task
---

# VRS Test Suggest — Improvement Recommendations

You are the **VRS Test Suggest** skill. You analyze scenario results to produce prioritized, actionable improvement suggestions.

## How to Invoke

```bash
/vrs-test-suggest vrs-audit          # suggest improvements for audit workflow
/vrs-test-suggest vrs-attacker       # suggest improvements for attacker agent
/vrs-test-suggest UC-AUDIT-005       # analyze specific scenario failure
/vrs-test-suggest --all              # analyze all failing scenarios
```

## Workflow

### 1. Run affected scenarios

```bash
# For a workflow
uv run pytest tests/scenarios/ -k "audit" -v --tb=long

# For a specific scenario
uv run pytest tests/scenarios/ -k "UC-AUDIT-005" -v --tb=long
```

### 2. Collect dimension scores

For each failing scenario, identify:
- Which `must_happen` items failed
- Which evaluation dimensions scored lowest
- Which regression signals triggered

### 3. Group failures by root cause

Don't list individual symptoms. Group related failures:

```
ROOT CAUSE 1: Graph queries too broad (affects 3 scenarios)
  - UC-AUDIT-001: graph_utilization=35 (queries return too many results)
  - UC-AUDIT-005: graph_utilization=28 (oracle-specific query missing)
  - UC-ATK-001: evidence_quality=40 (findings not anchored to graph nodes)

ROOT CAUSE 2: Missing reentrancy pattern for simple contracts
  - UC-AUDIT-001: finding_accuracy=50 (reentrancy detected via lens, not pattern)
```

### 4. Produce improvement suggestions

For each root cause, suggest a specific fix:

```
SUGGESTION 1: Add pattern-specific query templates [HIGH CONFIDENCE]
  Impact: +15 points on graph_utilization across 3 scenarios
  Action: Add query templates to attacker prompt:
    "For reentrancy: query 'TRANSFERS_VALUE_OUT before WRITES_USER_BALANCE'"
    "For oracle: query 'READS_EXTERNAL_VALUE without CHECKS_STALENESS'"
  Files to modify: src/alphaswarm_sol/shipping/agents/vrs-attacker.md
  Affected scenarios: UC-AUDIT-001, UC-AUDIT-005, UC-ATK-001

SUGGESTION 2: Calibrate reentrancy pattern for minimal contracts [MEDIUM CONFIDENCE]
  Impact: +10 points on finding_accuracy for UC-AUDIT-001
  Action: Review reentrancy pattern conditions - may require fewer edges
  Files to modify: vulndocs/reentrancy/classic/patterns/classic-001.yaml
  Affected scenarios: UC-AUDIT-001
```

### 5. Prioritize by impact

Rank suggestions by: (point improvement × number of affected scenarios)

```
=== IMPROVEMENT PRIORITY ===

1. Add query templates [+45 total points across 3 scenarios] → DO FIRST
2. Fix reentrancy pattern [+10 points for 1 scenario] → DO SECOND
3. Strengthen defender independence [+8 points for 2 scenarios] → DO THIRD
```

## Integration with Improvement Loop

After applying a suggestion:
1. Run `/vrs-test-scenario <affected>` to verify improvement
2. Run `/vrs-test-regression` to check for regressions
3. If improved and no regressions → commit
4. If regressed → revert and try alternative approach

## Key Principle

Suggestions must be **specific enough to implement in one PR**. Not "improve graph utilization" but "add this exact query template to this exact prompt file for this exact vulnerability class."
