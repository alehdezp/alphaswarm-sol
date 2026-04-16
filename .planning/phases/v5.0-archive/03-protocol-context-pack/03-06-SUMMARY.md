---
phase: 03
plan: 06
subsystem: context-pack-cli
tags: [cli, tests, integration, typer, pytest]
requires: ["03-04"]
provides:
  - CLI commands for context pack management
  - Integration tests for full context pack workflow
affects: ["04-*"]
tech-stack:
  added: []
  patterns: [typer-subcommand, pytest-fixtures, integration-tests]
key-files:
  created:
    - src/true_vkg/cli/context.py
    - tests/test_context_pack.py
  modified:
    - src/true_vkg/cli/main.py
    - src/true_vkg/context/__init__.py
decisions:
  - key: cli-architecture
    choice: Typer subcommand pattern
    why: Consistent with existing CLI commands (beads, vulndocs)
  - key: test-scope
    choice: Full integration coverage
    why: Tests cover schema, storage, analysis, evidence/bead integration, CLI
metrics:
  duration: 562s
  completed: 2026-01-20
---

# Phase 03 Plan 06: CLI and Tests Summary

CLI commands and integration tests for protocol context packs.

## One-Liner

Context pack CLI (generate/show/update/list/delete/export) + 41 integration tests covering full workflow

## What Was Built

### CLI Commands (src/true_vkg/cli/context.py - 797 LOC)

Created Typer subcommand `context_app` with commands:

| Command | Purpose |
|---------|---------|
| `generate` | Create context pack from code + docs |
| `show` | Display context pack (full or by section) |
| `update` | Incremental update preserving human edits |
| `list` | List all stored context packs |
| `delete` | Delete a context pack |
| `export` | Export to YAML or JSON file |

CLI features:
- Integration with `ContextPackBuilder` for generation
- Support for both human-readable and JSON output
- Section-level display for targeted retrieval (roles, assumptions, invariants, etc.)
- Confidence level formatting with indicators ([+], [?], [ ])
- Protocol override options (--name, --type)
- Force overwrite support

### Integration Tests (tests/test_context_pack.py - 919 LOC)

41 pytest tests organized into test classes:

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestContextPackSchema | 10 | Creation, serialization, sections, queries, merge |
| TestContextPackStorage | 6 | Save/load, list, sections, update, summary |
| TestCodeAnalyzer | 2 | Operation/role mappings |
| TestEvidenceIntegration | 4 | Context provider, accepted risk check, violations |
| TestBeadIntegration | 4 | Context inheritance, prompt formatting |
| TestContextPackBuilder | 3 | Minimal build, config, result properties |
| TestFoundationTypes | 8 | Confidence, Role, Assumption, etc. |
| TestCLIIntegration | 2 | Command registration |
| TestEndToEndWorkflow | 2 | Full lifecycle, incremental updates |

### Main App Registration

Updated `src/true_vkg/cli/main.py`:
- Import `context_app` from `cli.context`
- Register with `app.add_typer(context_app, name="context")`

## Key Links Verified

| From | To | Via | Pattern |
|------|----|----|---------|
| cli/context.py | context/builder.py | import ContextPackBuilder | `from true_vkg.context import ContextPackBuilder` |
| cli/main.py | cli/context.py | register subcommand | `app.add_typer(context_app, name="context")` |

## Verification Results

```bash
# CLI module verification
$ uv run python -c "from true_vkg.cli.context import context_app; print('Commands:', [c.name for c in context_app.registered_commands])"
Commands: ['generate', 'show', 'update', 'list', 'delete', 'export']

# Main app registration
$ uv run python -c "from true_vkg.cli.main import app; print('context' in [g.name for g in app.registered_groups])"
True

# CLI help works
$ uv run alphaswarm context --help
# Shows 6 commands with descriptions

# Tests pass
$ uv run pytest tests/test_context_pack.py -v
41 passed in 0.75s
```

## Commits

| Hash | Type | Description |
|------|------|-------------|
| c43839d | feat | Add context pack CLI commands (797 LOC) |
| 793e311 | test | Add context pack integration tests (919 LOC) |

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

### Created
- `src/true_vkg/cli/context.py` (797 lines)
  - CLI commands: generate, show, update, list, delete, export
  - Helper functions for formatted display
  - Section printers for targeted output

- `tests/test_context_pack.py` (919 lines)
  - 41 integration tests
  - Fixtures for sample types
  - Full workflow coverage

### Modified
- `src/true_vkg/cli/main.py` (+2 lines)
  - Import and register context_app

## Usage Examples

```bash
# Generate context pack
uv run alphaswarm context generate ./src

# With custom name and type
uv run alphaswarm context generate ./src --name "MyProtocol" --type lending

# Show full pack
uv run alphaswarm context show ./src

# Show specific section
uv run alphaswarm context show ./src --section roles

# JSON output
uv run alphaswarm context show ./src --json

# List all packs
uv run alphaswarm context list

# Update after code changes
uv run alphaswarm context update ./src

# Export to file
uv run alphaswarm context export --output my-context.yaml
```

## Next Phase Readiness

Phase 03 Plan 06 completes the Protocol Context Pack phase. Ready for:

1. **Phase 04: Orchestration Layer** - Context packs can now be used by agents
2. Context CLI enables standalone context generation
3. Integration tests verify full workflow for reliability

## Test Coverage Additions

New test file adds comprehensive coverage:
- Schema validation and serialization
- Storage operations (YAML persistence)
- Code analyzer mappings
- Evidence and bead integration providers
- CLI command registration
- End-to-end workflows

All 41 tests pass, providing regression protection for the entire context pack system.
