# Complete Legacy Infrastructure Migration Inventory for AlphaSwarm.sol

**Date:** 2026-02-08
**Status:** MIGRATION COMPLETE (2026-02-09) — All legacy infrastructure removed
**Context:** Historical inventory from migration to Claude Code Agent Teams
**Source:** Exhaustive codebase search across 459 files with legacy infrastructure references

> **NOTE (2026-02-09):** This inventory is historical. All legacy testing infrastructure has been fully deprecated and removed. Retained for research context only.

---

## Executive Summary

**Total Files with legacy infrastructure References:** 459 files
**Production Code to Migrate:** ~2900 LOC -> ~1500 LOC (50% reduction expected)
**Core Python Modules:** 19 files (346 occurrences)
**Skills & Agents:** 15 files (215 occurrences)
**Testing Scripts:** 39 files (408 occurrences)
**Planning/Docs:** 271+ files (extensive documentation)

---

## Category Breakdown

### 1. PRODUCTION CODE (MUST MIGRATE) - Priority: CRITICAL

#### Core Python Modules (19 files, 346 occurrences)

| File | LOC | References | Purpose | Priority |
|------|-----|------------|---------|----------|
| `src/alphaswarm_sol/testing/legacy infrastructure_harness.py` | 664 | 63 | Strict legacy infrastructure harness for test orchestration, session creation, pane role mapping, transcript capture with SHA-256 hashing | **P0** |
| `src/alphaswarm_sol/testing/workflow/legacy infrastructure_controller.py` | 637 | 79 | legacy infrastructure controller for Claude Code workflow testing | **P0** |
| `src/alphaswarm_sol/testing/workflow/legacy infrastructure_cli_wrapper.py` | 487 | 54 | legacy infrastructure-cli wrapper for reliable Claude Code testing | **P0** |
| `src/alphaswarm_sol/testing/full_testing_orchestrator.py` | ~1000 | 41 | Master orchestrator for /vrs-full-testing | **P0** |
| `src/alphaswarm_sol/testing/workflow/__init__.py` | - | 17 | Workflow module exports | **P0** |
| `src/alphaswarm_sol/testing/proof_tokens.py` | - | 15 | Proof token generation with legacy infrastructure transcript validation | **P1** |
| `src/alphaswarm_sol/testing/failure_catalog.py` | - | 10 | Failure cataloging for legacy infrastructure-based runs | **P1** |
| `src/alphaswarm_sol/testing/master_orchestrator.py` | - | 9 | Master orchestrator coordinating legacy infrastructure sessions | **P1** |
| `src/alphaswarm_sol/testing/evidence_pack.py` | - | 8 | Evidence pack creation from legacy infrastructure transcripts | **P1** |
| `src/alphaswarm_sol/testing/full_testing_schema.py` | - | 8 | Schema definitions for legacy infrastructure-based testing | **P1** |
| `src/alphaswarm_sol/testing/flexible/session_state.py` | - | 8 | Session state management for legacy infrastructure sessions | **P1** |
| `src/alphaswarm_sol/testing/workflow/self_improving_runner.py` | - | 8 | Self-improving runner using legacy infrastructure-cli | **P2** |
| `src/alphaswarm_sol/testing/flexible/component_runner.py` | - | 4 | Component runner with legacy infrastructure isolation | **P2** |
| `src/alphaswarm_sol/testing/flexible/parallel_runner.py` | - | 4 | Parallel test execution in legacy infrastructure panes | **P2** |
| `src/alphaswarm_sol/testing/fix_retest_loop.py` | - | 2 | Fix/retest loop coordination via legacy infrastructure | **P3** |
| `src/alphaswarm_sol/testing/agentic_runner.py` | - | 1 | Agentic test runner mentions legacy infrastructure | **P3** |
| `src/alphaswarm_sol/testing/supervision_loop.py` | - | 1 | Supervision loop for legacy infrastructure sessions | **P3** |
| `src/alphaswarm_sol/skills/registry.yaml` | - | 13 | Skill registry with legacy infrastructure-based skill definitions | **P1** |
| `src/alphaswarm_sol/testing/flexible/task_registry.yaml` | - | 1 | Task registry for legacy infrastructure-based tests | **P3** |

---

#### Skills (13 files, 194 occurrences)

| File | Refs | Purpose | Action |
|------|------|---------|--------|
| `.claude/skills/vrs-agentic-testing.md` | 58 | Agentic self-testing via legacy infrastructure-cli | **MIGRATE** |
| `.claude/skills/vrs-legacy infrastructure-testing.md` | 33 | Self-improving Claude Code testing via legacy infrastructure-cli | **MIGRATE** |
| `.claude/skills/vrs-full-testing.md` | 31 | Master orchestrator for E2E validation | **MIGRATE** |
| `.claude/skills/vrs-legacy infrastructure-runner.md` | 20 | Execute commands in isolated legacy infrastructure sessions | **MIGRATE** |
| `.claude/skills/enforce-testing-rules.md` | 18 | Testing rules enforcement with legacy infrastructure requirements | **MIGRATE** |
| `.claude/skills/vrs-validate-phase.md` | 7 | Phase validation via legacy infrastructure | **MIGRATE** |
| `.claude/skills/vrs-parallel.md` | 6 | Parallel execution in legacy infrastructure panes | **MIGRATE** |
| `.claude/skills/vrs-self-test.md` | 7 | Self-testing infrastructure | **MIGRATE** to Agent Teams + controller |
| `.claude/skills/vrs-workflow-test.md` | 5 | Workflow testing via legacy infrastructure | **MIGRATE** |
| `.claude/skills/vrs-run-validation.md` | 4 | Validation runner using legacy infrastructure | **MIGRATE** |
| `.claude/skills/vrs-strict-audit.md` | 3 | Strict audit mode with legacy infrastructure validation | **MIGRATE** |
| `.claude/skills/vrs-resume.md` | 2 | Resume workflows using legacy infrastructure sessions | **MIGRATE** |
| `.claude/skills/vrs-component.md` | 1 | Component testing via legacy infrastructure | **MIGRATE** |

---

#### Agents (2 files, 21 occurrences)

| File | Refs | Purpose | Action |
|------|------|---------|--------|
| `.claude/agents/vrs-claude-controller.md` | 17 | legacy infrastructure-based Claude Code workflow controller | **MIGRATE** (critical) |
| `.claude/agents/vrs-self-improver.md` | 3 | Self-improvement agent using legacy infrastructure | **MIGRATE** |

---

### 2. CONFIGURATION FILES (MUST UPDATE)

| File | Refs | Purpose | Action |
|------|------|---------|--------|
| `configs/legacy infrastructure_cli_markers.yaml` | 43 | Required legacy infrastructure-cli markers for E2E tests | **REWRITE** |
| `configs/skill_tool_policies.yaml` | 15 | Skill tool policies with legacy infrastructure rules | **UPDATE** |
| `scripts/e2e/legacy infrastructure_harness_config.yaml` | 16 | Harness configuration for legacy infrastructure E2E tests | **MIGRATE** |
| `configs/gate_runner.yaml` | 2 | Gate runner config | **UPDATE** |
| `configs/fresh_env_matrix.yaml` | 1 | Fresh environment matrix | **UPDATE** |

---

### 3. SELF-TEST INFRASTRUCTURE (DEPRECATED — migrate to Agent Teams + controller)

#### Test Files (18 files, 138 occurrences)

| File | Refs | Action |
|------|------|--------|
| `tests/e2e/test_legacy infrastructure_harness_smoke.py` | 25 | **DELETE** — replaced by controller tests |
| `tests/e2e/test_workflow_infrastructure.py` | 42 | **DELETE** — replaced by controller tests |
| `tests/test_legacy infrastructure_cli_wrapper.py` | 19 | **DELETE** — replaced by controller tests |
| `tests/test_component_runner.py` | 6 | **DELETE** — replaced by controller tests |
| `tests/test_session_state.py` | 4 | **DELETE** — replaced by controller tests |
| `tests/test_parallel_runner.py` | 3 | **DELETE** — replaced by controller tests |
| `tests/test_self_improving_runner.py` | 2 | **DELETE** — replaced by controller tests |
| + 11 more test/scenario files | ~37 | **DELETE/MIGRATE** |

#### Test Scripts (39 files, 408 occurrences)

All `scripts/e2e/` shell scripts — **DELETE**. Testing infrastructure moves to Agent Teams + `claude-code-controller` (npm v0.6.1).

---

### 4. DOCUMENTATION (UPDATE TEXT) - 323+ files

#### Critical (Auto-loaded by CLAUDE.md)

| File | Refs | Priority |
|------|------|----------|
| **CLAUDE.md** | ~15 | **CRITICAL** - Replace legacy infrastructure testing section |
| `.planning/testing/rules/canonical/RULES-ESSENTIAL.md` | 29 | **CRITICAL** - Auto-invoke rules |
| `.planning/testing/rules/canonical/legacy infrastructure-cli-instructions.md` | 50 | **HIGH** - Mark SELF-TEST ONLY |
| `.planning/testing/rules/canonical/TESTING-FRAMEWORK.md` | 35 | **HIGH** |
| `.planning/testing/rules/canonical/VALIDATION-RULES.md` | 16 | **HIGH** |

#### Moderate (14 testing guides, 20+ testing docs)

All `.planning/testing/guides/*.md` and `.planning/testing/*.md` files.

#### Bulk Update (271 phase plan files)

Distributed across phases 05.x through 07.3.4. Most are text-only updates.

---

## Migration by Priority

| Priority | Files | Action | Week |
|----------|-------|--------|------|
| **P0** | 5 Python + 1 agent + 2 docs | Core infrastructure replacement | 1-2 |
| **P1** | 8 Python + 12 skills + 5 configs | Skills and workflow migration | 3-4 |
| **P2** | 4 Python + 76 former self-test (delete) | Delete legacy infrastructure self-test code, secondary modules | 5 |
| **P3** | 323+ docs | Documentation bulk update | 6 |

**Total estimated effort:** 6 weeks

---

## File Count Summary

| Category | Files | Action |
|----------|-------|--------|
| MIGRATE (production) | 39 | Replace with Agent Teams |
| DELETE (former self-test) | 76 | Replaced by Agent Teams + controller |
| UPDATE (documentation) | 323+ | Text replacement |
| ARCHIVE | ~10 | Old transcripts, reports |
| **TOTAL** | **459** | |
