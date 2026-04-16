---
name: vrs-test-component
description: |
  Tests individual VRS components (graph builder, pattern matcher, tool
  adapters, context packer) in isolation using pytest with targeted test
  selection and dependency validation.

  Invoke when user wants to:
  - Test specific component: "/vrs-test-component kg/builder"
  - Run focused validation: "test pattern matching"
  - Validate dependencies: "check tool adapter health"
slash_command: vrs:test-component
context: fork
tools:
  - Read
  - Glob
  - Grep
  - Bash(uv run pytest*)
  - Bash(uv run alphaswarm*)
---

# VRS Test Component

Test individual VRS components in isolation.

## Purpose

Run targeted tests against specific components without executing the full
pipeline. Useful for rapid iteration during development.

## When to Use

- After modifying a specific module
- During component-level development
- When debugging a specific failure
- For quick smoke tests

## Arguments

- **component**: Component to test (e.g., `kg/builder`, `tools/slither`, `patterns`)
- **verbose**: Show detailed output (default: true)

## Components

| Component | Test Path | What it Tests |
|-----------|-----------|---------------|
| `kg/builder` | `tests/test_test_builder.py`, `tests/test_context_builder.py`, `tests/test_vulndocs_builder.py` | Graph construction |
| `patterns` | `tests/test_patterns.py`, `tests/test_pattern_taxonomy.py`, `tests/test_pattern_loading_regression.py` | Pattern matching |
| `tools` | `tests/vulndocs/` (tool-related tests) | Tool adapters |
| `context` | `tests/test_context_pack.py`, `tests/test_context_expansion.py` | Context pack generation |
| `orchestration` | `tests/test_orchestration.py`, `tests/test_orchestration_schemas.py` | Pool/bead management |
| `labels` | `tests/test_label*.py` | Semantic labeling |

## Execution

```bash
# Test graph builder
uv run pytest tests/test_test_builder.py tests/test_context_builder.py tests/test_vulndocs_builder.py -v -n auto

# Test pattern matching
uv run pytest tests/test_patterns.py tests/test_pattern_taxonomy.py tests/test_pattern_loading_regression.py -v -n auto

# Test context packs
uv run pytest tests/test_context_pack.py tests/test_context_expansion.py -v -n auto

# Test all with parallel execution
uv run pytest tests/ -n auto --dist loadfile
```

## Dependency Validation

Before running component tests, verify:
1. Required test contracts exist in `tests/contracts/`
2. Graph cache is available (or will be built)
3. External tools are installed (for tool adapter tests)

## Replaces

- vrs-component (skills-testing)
- vrs-self-test (skills-testing)
- vrs-environment (skills-testing)
