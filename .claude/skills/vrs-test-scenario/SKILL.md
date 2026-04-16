---
name: vrs-test-scenario
description: |
  Run a single use case scenario through the evaluation pipeline and produce
  structured feedback. Loads scenario YAML, evaluates against expected behavior,
  reports pass/fail with evidence and improvement suggestions.

  Invoke when user wants to:
  - Test a specific scenario: "test UC-AUDIT-001", "run scenario UC-ATK-001"
  - Validate expected behavior: "does the audit detect reentrancy?"
  - Get feedback on a workflow: "how well does vrs-audit handle oracle manipulation?"

slash_command: vrs-test-scenario
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(pytest*)
  - Bash(uv run*)
  - Bash(python*)
---

# VRS Test Scenario — Single Scenario Evaluation

You are the **VRS Test Scenario** skill. You run a single use case scenario through the evaluation pipeline and produce structured, actionable feedback.

## How to Invoke

```bash
/vrs-test-scenario UC-AUDIT-001
/vrs-test-scenario UC-ATK-001
/vrs-test-scenario "audit"          # runs all audit scenarios
```

## Workflow

### 1. Find the scenario

```bash
# Single scenario by ID
uv run pytest tests/scenarios/ -k "UC-AUDIT-001" -v --tb=long

# All scenarios matching a pattern
uv run pytest tests/scenarios/ -k "audit" -v --tb=long
```

### 2. Report results

For each scenario, report:

```
UC-AUDIT-001: PASS/FAIL (score: XX)
  ✓ [must_happen item that passed]
  ✓ [must_happen item that passed]
  ✗ [must_happen item that FAILED] (score: XX on dimension_name)
  → SUGGESTION: [specific improvement suggestion]

Regression signals:
  - [signal]: OK / TRIGGERED
```

### 3. If scenario fails

1. Read the scenario YAML to understand expected behavior
2. Identify which `must_happen` items failed and why
3. Check which evaluation dimensions scored lowest
4. Provide specific, actionable improvement suggestions

### 4. Structured output

Always produce a summary table:

| Scenario | Status | Score | Lowest Dimension | Suggestion |
|----------|--------|-------|-------------------|------------|
| UC-AUDIT-001 | PASS | 78 | evidence_quality (45) | Anchor findings to line numbers |

## Scenario Locations

- YAML files: `.planning/testing/scenarios/use-cases/`
- Schema: `.planning/testing/scenarios/use-cases/_schema.yaml`
- Test runner: `tests/scenarios/test_use_cases.py`
- Evaluation contracts: `src/alphaswarm_sol/testing/evaluation/contracts/`

## Key Principle

Feedback must be **actionable**. Not "score dropped" but "evidence_quality scored 35 because findings lack line numbers; fix: add 'cite exact line numbers' to attacker prompt."
