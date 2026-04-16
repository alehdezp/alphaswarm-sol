# Phase 6 Plan 01: AlphaSwarm.sol Rebrand Summary

**Completed:** 2026-01-22
**Duration:** 17 minutes
**Tasks:** 3/3

---

## One-liner

Complete rebrand from True VKG to AlphaSwarm.sol with 0.5.0 version, dual CLI entry points (alphaswarm/aswarm), .vrs config directory, and vrs-* agent/skill prefixes.

---

## What Was Done

### Task 1: Rename source directory and update pyproject.toml
- **Commit:** ccdf376
- Renamed `src/true_vkg/` to `src/alphaswarm_sol/`
- Updated `pyproject.toml`:
  - Package name: `true-vkg` -> `alphaswarm-sol`
  - Version: `4.0.0` -> `0.5.0`
  - Description: AI-native smart contract security analysis
  - Entry points: `alphaswarm` and `aswarm` (dual CLI)
  - Wheel package path updated
- Added dynamic version using `importlib.metadata` in `__init__.py`

### Task 2: Mass update all Python imports and references
- **Commit:** ccdf376
- Updated ~1,948 import references across 586 files
- Replaced `from true_vkg` -> `from alphaswarm_sol`
- Replaced `import true_vkg` -> `import alphaswarm_sol`
- Replaced `.true_vkg/` paths -> `.vrs/` paths
- Updated CLI help text and docstrings
- Updated deprecation warnings with new module names

### Task 3: Update documentation, agents, skills, and config
- **Commit:** 29b5c9e
- Renamed `.vkg/` -> `.vrs/` config directory
- Updated 1,037 files with new branding
- Renamed 13 agent files from `vkg-*` to `vrs-*`:
  - vrs-attacker, vrs-defender, vrs-verifier
  - vrs-supervisor, vrs-integrator, vrs-test-builder
  - vrs-pattern-architect, vrs-docs-curator, vrs-security-research, vrs-real-world-auditor
- Renamed skill directories from `vkg-*` to `vrs-*`
- Updated all skill prefixes from `/vkg:*` to `/vrs-*`
- Rewrote `.vrs/AGENTS.md` with comprehensive AlphaSwarm.sol interface
- Updated README.md with new package name and examples
- Updated CLAUDE.md with new file paths and references
- Updated pattern files and GitHub workflows

### Fix Commit
- **Commit:** a115b88
- Fixed `src.vrs` import error in `tests/vulndocs/test_schema.py`
- Added `--version` / `-v` CLI flag for version display

---

## Verification Results

| Check | Result |
|-------|--------|
| `import alphaswarm_sol` | 0.5.0 |
| `alphaswarm --version` | AlphaSwarm.sol 0.5.0 |
| `aswarm --version` | AlphaSwarm.sol 0.5.0 |
| true_vkg in src/ | 0 references |
| .vrs/ directory | EXISTS |
| .vrs/AGENTS.md | vrs-* agents documented |
| Core tests | 87 passed |

---

## Files Changed

### Created
- `.vrs/AGENTS.md` (rewritten for AlphaSwarm.sol)

### Renamed
- `src/true_vkg/` -> `src/alphaswarm_sol/` (entire directory tree)
- `.vkg/` -> `.vrs/` (config directory)
- `.claude/agents/vkg-*.md` -> `.claude/agents/vrs-*.md` (13 files)
- `.claude/skills/vkg-*` -> `.claude/skills/vrs-*` (4 directories)

### Modified
- `pyproject.toml` - package name, version, entry points
- `README.md` - all CLI examples and references
- `CLAUDE.md` - all file paths and agent names
- 586 Python files - imports and string references
- 1,037 documentation/config files - branding updates

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Package name | `alphaswarm-sol` | PyPI naming convention (hyphen) |
| Module name | `alphaswarm_sol` | Python import convention (underscore) |
| Config directory | `.vrs/` | VRS = Vulnerability Reasoning System |
| Version | `0.5.0` | Pre-1.0 signals maturing product |
| Dual CLI | `alphaswarm` + `aswarm` | Full name + short alias |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing --version CLI flag**
- **Found during:** Task 2 verification
- **Issue:** CLI had no `--version` flag as specified in success criteria
- **Fix:** Added version_callback with `--version` / `-v` option to CLI main
- **Files modified:** `src/alphaswarm_sol/cli/main.py`
- **Commit:** a115b88

**2. [Rule 1 - Bug] Incorrect import in vulndocs test**
- **Found during:** Full test suite run
- **Issue:** `tests/vulndocs/test_schema.py` had `src.vrs.vulndocs` import (invalid path)
- **Fix:** Changed to `alphaswarm_sol.vulndocs`
- **Files modified:** `tests/vulndocs/test_schema.py`
- **Commit:** a115b88

---

## Pre-existing Test Failures

8 tests failed due to pre-existing YAML parsing issues in pattern files (not related to rebrand):
- `yaml.composer.ComposerError: expected a single document in the stream`
- These tests expect `yaml.safe_load` but pattern files have multiple documents (`---` separators)
- Tracked for future fix, not a regression from this rebrand

---

## Next Steps

1. Plan 06-02: Research-style architecture documentation
2. Plan 06-03: PyPI publishing workflow setup
3. Plan 06-04: Docker image creation
4. Plan 06-05: Fresh install validation

---

## Commits

| Hash | Type | Description |
|------|------|-------------|
| ccdf376 | refactor | Mass update Python imports |
| 29b5c9e | docs | Update docs, agents, skills, config |
| a115b88 | fix | Import error fix + CLI --version |
