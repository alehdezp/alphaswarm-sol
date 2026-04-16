---
name: vrs-test-enforce
description: |
  Enforces testing quality gates and rules during development. Validates
  that changes include proper tests, evidence, and follow quality standards.

  Invoke when:
  - Creating or modifying skills, agents, or workflows
  - Completing a development phase
  - Before marking work as done
  Note: AUTO-INVOKE requires hook-based trigger (3.1c-02 scope, not yet wired).
slash_command: vrs:test-enforce
context: inline
tools:
  - Read
  - Glob
  - Grep
  - Bash(uv run pytest*)
---

# VRS Test Enforce

Enforce testing quality gates during development.

## Purpose

Ensure all changes meet quality standards before they are considered
complete. This skill validates test coverage, evidence quality, and
adherence to project conventions.

## When to Use

- Before marking tasks as done
- When completing a phase or milestone
- When modifying skills or agents
- Before creating pull requests

## Quality Gates

### Gate 1: Test Coverage
- New code has corresponding tests
- Tests are outcome-based (not implementation mirrors)
- Tests use proper fixtures from `tests/conftest.py`

### Gate 2: Conventions
- Skill frontmatter follows `/skill-creator` conventions
- Agent prompts follow graph-first template
- File naming follows project conventions

### Gate 3: Evidence
- Changes are documented in STATE.md if significant
- Pattern changes include precision/recall data
- Skill changes include before/after comparison

### Gate 4: No Regressions
- Existing tests still pass: `uv run pytest tests/ -x`
- No new warnings introduced
- No broken imports

## Execution

```bash
# Quick gate check
uv run pytest tests/ -x --timeout=60

# Full gate check with coverage
uv run pytest tests/ -n auto --dist loadfile -v
```

## Checks Performed

1. **Frontmatter validation**: name, description, slash_command, context, tools
2. **Model tier validation**: Uses canonical names (opus, sonnet, haiku)
3. **Path validation**: No hardcoded absolute paths
4. **Import validation**: No broken imports in modified files
5. **Test existence**: Modified source files have test coverage

## Replaces

- enforce-testing-rules (skills-testing)
- vrs-strict-audit (skills-testing)
- vrs-validate-phase (skills-testing)
