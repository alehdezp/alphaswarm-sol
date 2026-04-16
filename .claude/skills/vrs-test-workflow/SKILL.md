---
name: vrs-test-workflow
description: |
  Tests VRS skill and agent workflows by spawning Agent Teams workers
  that execute workflows in isolated subagent contexts, capturing output
  and evaluating results against success criteria.

  Invoke when user wants to:
  - Test a skill workflow: "test /vrs-audit workflow", "/vrs-test-workflow audit"
  - Validate agent output: "test vrs-attacker against Vault.sol"
  - Evaluate workflow quality: "evaluate last audit run"
slash_command: vrs:test-workflow
context: fork
tools:
  - Read
  - Glob
  - Grep
  - Bash(uv run pytest*)
  - Bash(uv run alphaswarm*)
  - Task
---

# VRS Test Workflow

Test VRS skill and agent workflows using Agent Teams orchestration.

## Purpose

Validate that skills and agents produce correct, high-quality output when
executed against real contracts. Uses Agent Teams workers to run workflows
in isolated contexts and evaluates results against defined success criteria.

## When to Use

- After modifying a skill or agent prompt
- Before promoting a skill to shipping
- When validating agent output quality
- During CI/CD workflow validation

## Arguments

- **target**: Skill name or agent type to test (e.g., `audit`, `vrs-attacker`)
- **contract**: Contract path to test against (optional, uses default corpus)
- **criteria**: Success criteria file (optional, uses defaults)

## Workflow

1. **Select target**: Identify skill/agent to test
2. **Prepare context**: Set up test contract and expected outputs
3. **Spawn worker**: Launch Agent Teams worker with target skill/agent
4. **Capture output**: Collect worker output via TaskUpdate
5. **Evaluate**: Compare output against success criteria
6. **Report**: Generate pass/fail report with evidence

## Execution

```bash
# Run workflow test for audit skill
uv run pytest tests/ -k "test_workflow" -v

# Run against specific contract
uv run alphaswarm build-kg tests/contracts/VulnerableVault.sol
```

## Success Criteria

Default criteria per skill type:

| Skill Type | Criteria |
|-----------|----------|
| Investigation | Finds >= 1 real vulnerability, evidence chain complete |
| Tool | Runs without error, produces valid output |
| Verification | Verdict matches ground truth |
| Debate | Attacker/defender produce distinct arguments |

## Two-Tier Evaluation Model

Workflow tests use a two-tier evaluation architecture:

- **Engine tier** (observe -> parse -> score -> evaluate): Captures raw outputs, extracts structured metrics, computes scores, and renders pass/fail verdicts. This is deterministic and fast.
- **Intelligence tier** (discover -> generate -> heal -> fingerprint): Discovers emergent patterns across runs, synthesizes new test scenarios targeting gaps, detects stuck evaluation dimensions, and builds reasoning fingerprints for behavioral drift detection.

When writing workflow tests, ensure the engine tier can capture sufficient structured output for the intelligence tier to operate on.

## Compositional Stress Testing

Orchestrator workflow tests should exercise non-standard agent compositions to verify robustness:

- Attacker-only (no defender): Does the system still produce bounded output?
- Dual-verifier: Do two verifiers converge or diverge on the same evidence?
- Missing-role: What happens when a required agent type is unavailable?
- Swapped-model-tier: Does a sonnet-attacker produce meaningfully different results than opus-attacker?

These compositions surface fragile assumptions in the orchestration layer.

## Agent Team Context Isolation

When spawning Agent Teams workers, control their context to produce
realistic evaluation results.

**Spawn protocol:**
```python
# Create team (once per test run)
TeamCreate(team_name="workflow-test-{target}", description="Testing {target}")

# Spawn NAMED teammates with FOCUSED context
Task(
    team_name="workflow-test-{target}",
    name="worker-1",
    subagent_type="general-purpose",
    prompt="""You are testing workflow {target} on {contract}.

TOOLS (use ONLY these):
- `uv run alphaswarm build-kg {contract}` — build knowledge graph
- `uv run alphaswarm query "{query}"` — semantic graph query
- `Read` on {contract} ONLY

DO NOT read CLAUDE.md, .planning/*, docs/*, or vulndocs/.
Write results to .vrs/observations/{target}/."""
)
```

**Why**: Full project context makes tests unrealistic. Real users have
focused context. Never use bare `Task(subagent_type=...)` and call it
"Agent Teams" — Agent Teams require `TeamCreate` + `Task(team_name=...)`.

## Sequential Execution Constraint

**Plans spawning Agent Teams must run in top-level sessions.** Workflow tests that launch Agent Teams workers cannot be nested inside subagent contexts — they must execute at the top level to avoid context isolation conflicts. Design test harnesses accordingly: the test runner itself must be the top-level orchestrator.

## Replaces

- vrs-workflow-test (skills-testing)
- vrs-evaluate-workflow (skills-testing)
- vrs-agentic-testing (skills-testing)
