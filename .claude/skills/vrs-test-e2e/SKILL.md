---
name: vrs-test-e2e
description: |
  Runs end-to-end validation pipeline using Agent Teams orchestration.
  Executes multi-wave validation against real contracts with quality gates
  between waves and coordinates parallel workers for throughput.

  Invoke when user wants to:
  - Run full E2E validation: "/vrs-test-e2e", "run full validation"
  - Validate specific wave: "/vrs-test-e2e --wave 2"
  - Check pipeline status: "validation pipeline status"
slash_command: vrs:test-e2e
context: fork
tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(uv run pytest*)
  - Bash(uv run alphaswarm*)
  - Task
---

# VRS Test E2E

Run end-to-end validation pipeline with multi-wave execution.

## Purpose

Execute the complete validation pipeline against real contracts to verify
the entire system works end-to-end: graph building, pattern matching,
tool integration, agent orchestration, and verdict generation.

## When to Use

- Before releasing a new version
- After significant changes to core modules
- When validating full pipeline integrity
- During milestone completion verification

## Arguments

- **wave**: Specific wave to run (1-3, optional, runs all by default)
- **contracts**: Contract directory (optional, uses test corpus)
- **parallel**: Number of parallel workers (default: 2)

## Waves

### Wave 1: Foundation
- Graph builds successfully
- CLI commands respond
- Tool adapters function
- Pattern files validate

### Wave 2: Integration
- Patterns detect known vulnerabilities
- Tools produce findings
- Findings deduplicate correctly
- Context packs generate

### Wave 3: Full Pipeline
- Multi-agent debate produces verdicts
- Evidence chains are complete
- Reports generate correctly
- No regressions from previous waves

## Quality Gates

Each wave must pass before the next begins:
- Wave 1: All foundation checks green
- Wave 2: >= 80% pattern precision, >= 50% recall
- Wave 3: Verdicts match ground truth on test corpus

## Execution

```bash
# Run full E2E suite
uv run pytest tests/ -k "test_e2e" -v --timeout=300

# Run specific wave
uv run pytest tests/ -k "test_e2e_wave1" -v
```

## Agent Team Spawning (Context Isolation)

When spawning Agent Teams for parallel evaluation, teammates MUST be
context-isolated. Do NOT let them inherit the full project context.

```python
# Create team for the wave
TeamCreate(team_name="e2e-wave-{N}", description="Wave {N} evaluations")

# Spawn teammates with FOCUSED context (not full CLAUDE.md)
Task(
    team_name="e2e-wave-{N}",
    name="worker-{M}",
    subagent_type="general-purpose",
    prompt="""You are a security investigator evaluating a Solidity contract.

TOOLS (use ONLY these):
- `uv run alphaswarm build-kg {contract_path}` — build knowledge graph
- `uv run alphaswarm query "{query}"` — semantic graph query
- `Read` on the contract source ONLY

DO NOT read CLAUDE.md, .planning/*, docs/*, or vulndocs/.
DO NOT modify files outside .vrs/observations/.

Check TaskList for work. Claim, execute, mark complete."""
)
```

**Why**: Teammates with full project context produce unrealistic results.
Real audit users have focused context. Test results must reflect that.

**NEVER** use bare `Task(subagent_type=...)` and call it "Agent Teams".
Agent Teams require `TeamCreate` + `Task(team_name=...)` + named teammates.

## Replaces

- vrs-full-testing (skills-testing)
- vrs-run-validation (skills-testing)
- vrs-parallel (skills-testing)
