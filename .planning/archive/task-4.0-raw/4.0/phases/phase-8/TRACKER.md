# Phase 8: Metrics & Observability

**Status:** COMPLETE (core) - optional tasks pending
**Priority:** MEDIUM - Can't improve what you can't measure
**Last Updated:** 2026-01-08
**Author:** BSKG Team

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 7 complete (learning works) |
| Exit Gate | All 8 metrics tracked, alerting works, CI integration complete |
| Philosophy Pillars | Self-Improvement, Knowledge Graph, Agentic Automation |
| Threat Model Categories | Observability across all detection categories |
| Estimated Hours | 42h (revised from 38h) |
| Actual Hours | [Tracked as work progresses] |
| Task Count | 12 tasks (revised from 10) |
| Test Count Target | 40+ tests |

---

## CRITIQUE SUMMARY

See `CRITIQUE.md` for detailed issues found. Key fixes:

1. **Added Task 8.0** - Module setup (was missing - module doesn't exist)
2. **Split Task 8.2** into 8.2a (recording) and 8.2b (calculation)
3. **Added data source documentation** - Original never explained where metric data comes from
4. **Fixed dependency graph** - Was inaccurate
5. **Clarified scaffold dependency** - Requires Phase 6 Beads

---

## 1. OBJECTIVES

### 1.1 Primary Objective

Track 8 key metrics that measure VKG's effectiveness, with alerting on degradation and CI integration to prevent regressions.

### 1.2 Secondary Objectives

1. Establish historical storage for trend analysis
2. Create alerting system for metric degradation
3. Build dashboard for metric visualization
4. Integrate metrics into CI pipeline
5. Define and enforce performance budgets

### 1.3 Philosophy Alignment

| Pillar | How This Phase Contributes |
|--------|---------------------------|
| Knowledge Graph | Metrics validate graph quality |
| NL Query System | Query latency is a key metric |
| Agentic Automation | Autonomy rate measures LLM effectiveness |
| Self-Improvement | Metrics enable data-driven improvement |
| Task System (Beads) | Escalation rate tracks bead effectiveness |

### 1.4 Success Metrics

| Metric | Target | Minimum | How to Measure |
|--------|--------|---------|----------------|
| Detection Rate | >= 80% | >= 70% | detected / total_expected (from MANIFEST.yaml) |
| False Positive Rate | < 15% | < 20% | FP / (FP + TP) |
| Pattern Precision | avg > 85% | avg > 75% | TP / (TP + FP) per pattern |
| LLM Autonomy | >= 70% | >= 50% | auto_resolved / total_findings |

### 1.5 Non-Goals (Explicit Scope Boundaries)

- NOT building a full analytics platform (basic metrics only)
- NOT implementing real-time streaming metrics (batch collection)
- NOT creating public dashboards (internal use only)
- NOT optimizing for metrics (avoiding Goodhart's Law)

---

## 2. RESEARCH REQUIREMENTS

### 2.1 Required Research Before Implementation

| ID | Research Topic | Output | Est. Hours | Status |
|----|---------------|--------|------------|--------|
| R8.1 | Metric Collection Best Practices | Collection patterns | 3h | TODO |
| R8.2 | Performance Baseline Methods | Baselining approach | 2h | TODO |

### 2.2 Knowledge Gaps

- [x] Where does ground truth come from? -> MANIFEST.yaml files
- [ ] How to prevent metrics gaming?
- [ ] What sampling rate for performance metrics?
- [ ] How to handle missing data in historical storage?

---

## 3. TASK DECOMPOSITION

### 3.1 Task Dependency Graph (CORRECTED)

```
8.0 (Module Setup)
    │
    ├── 8.1 (Define Metrics with Data Sources)
    │       │
    │       ├── 8.2a (Recording Infrastructure)
    │       │       │
    │       │       └── 8.2b (Calculation Engine)
    │       │               │
    │       │               ├── 8.3 (Historical Storage)
    │       │               │       │
    │       │               │       ├── 8.4 (Alerting)
    │       │               │       │       │
    │       │               │       │       └── 8.7 (CI Integration)
    │       │               │       │
    │       │               │       └── 8.5 (CLI Commands)
    │       │               │               │
    │       │               │               └── 8.6 (Dashboard - Optional)
    │       │               │
    │       │               └── R8.2 ── 8.8 (Baselines) ── 8.9 (Budgets) ── 8.10 (Budget Alerts)
```

### 3.2 Task Registry (REVISED)

| ID | Task | Est. | Priority | Depends On | Status | Task File |
|----|------|------|----------|------------|--------|-----------|
| 8.0 | Module Setup | 2h | MUST | - | DONE (28 tests) | `tasks/8.0-module-setup.md` |
| 8.1 | Define Metrics + Data Sources | 3h | MUST | 8.0 | DONE (21 tests) | `tasks/8.1-define-metrics.md` |
| 8.2a | Recording Infrastructure | 3h | MUST | 8.1 | DONE (25 tests) | `tasks/8.2a-metric-recording.md` |
| 8.2b | Calculation Engine | 4h | MUST | 8.2a | DONE (89 tests) | `tasks/8.2b-metric-calculation.md` |
| 8.3 | Historical Storage | 4h | MUST | 8.2b | DONE (103 tests) | tasks/8.3-historical-storage.md |
| 8.4 | Alerting System | 4h | MUST | 8.3 | DONE (116 tests) | tasks/8.4-alerting.md |
| 8.5 | CLI Commands | 4h | MUST | 8.3 | DONE (17 tests) | tasks/8.5-cli-commands.md |
| 8.6 | Dashboard | 4h | SHOULD | 8.5 | TODO | tasks/8.6-dashboard.md |
| 8.7 | CI Integration | 4h | MUST | 8.4 | DONE (25 tests) | tasks/8.7-ci-integration.md |
| 8.8 | Performance Baselines | 4h | SHOULD | R8.2 | TODO | tasks/8.8-baselines.md |
| 8.9 | Performance Budgets | 3h | SHOULD | 8.8 | TODO | tasks/8.9-budgets.md |
| 8.10 | Budget Alerting | 2h | SHOULD | 8.9 | TODO | tasks/8.10-budget-alerts.md |

### 3.3 Critical Dependencies on Other Phases

| Metric | Phase Dependency | If Unavailable |
|--------|------------------|----------------|
| Scaffold Compile Rate | Phase 6 (Beads) | SKIP metric |
| LLM Autonomy | Phase 6 + Phase 11 | SKIP metric |
| Token Efficiency | Phase 11 (LLM) | SKIP metric |
| Escalation Rate | Phase 6 (Beads) | SKIP metric |

**Core metrics (no dependencies):** Detection Rate, FP Rate, Pattern Precision, Time to Detection

---

## 4. TEST SUITE REQUIREMENTS

### 4.1 Test Categories

| Category | Count Target | Coverage Target | Location |
|----------|--------------|-----------------|----------|
| Unit Tests | 25 | 80% | `tests/test_metrics.py` |
| Integration Tests | 10 | - | `tests/test_metrics.py` |
| Performance Tests | 5 | - | `tests/test_performance.py` |

### 4.2 Test Fixtures Required

- [ ] `tests/fixtures/metrics_sample.json` - Sample metric data
- [ ] `tests/fixtures/history/` - Sample historical data
- [ ] `tests/projects/*/MANIFEST.yaml` - Ground truth for detection (CRITICAL)

---

## 5. IMPLEMENTATION GUIDELINES

### 5.1 File Locations

| Component | Location | Naming Convention |
|-----------|----------|-------------------|
| Metrics Module | `src/true_vkg/metrics/` | `snake_case.py` |
| Tests | `tests/test_metrics.py` | `test_*.py` |
| CLI | `src/true_vkg/cli/metrics.py` | N/A |
| Data | `.vrs/metrics/` | `*.json` |

### 5.2 Module Structure

```
src/true_vkg/metrics/
    __init__.py          # Exports
    types.py             # MetricName, MetricValue, MetricSnapshot
    definitions.py       # Metric definitions with data sources
    events.py            # Event dataclasses
    event_store.py       # Event persistence
    recorder.py          # Recording singleton
    calculator.py        # Metric calculation
    tracker.py           # Unified interface
    storage.py           # Historical storage
    alerting.py          # Alert logic
    dashboard.py         # ASCII dashboard
    budgets.py           # Performance budgets
```

---

## 6. COMPLETION CHECKLIST

### 6.1 Exit Criteria

- [ ] All tasks completed
- [ ] All tests passing
- [ ] All 8 metrics tracked (4 core + 4 dependent)
- [ ] Historical storage works
- [ ] Alerting fires correctly
- [ ] CI integration works
- [ ] Documentation updated

**Gate Keeper:** Deliberately degrade a metric. Verify alert fires and CI blocks.

### 6.2 Artifacts Produced

| Artifact | Location | Purpose |
|----------|----------|---------|
| Metrics module | `src/true_vkg/metrics/` | Core implementation |
| Tests | `tests/test_metrics.py` | Validation |
| CI workflow | `.github/workflows/metrics.yml` | CI integration |
| Documentation | `docs/reference/metrics.md` | Metric definitions |

---

## 7. TASK FILES

All tasks have self-contained task files in `tasks/` directory:

| File | Description |
|------|-------------|
| `tasks/8.0-module-setup.md` | Create metrics module skeleton |
| `tasks/8.1-define-metrics.md` | Define 8 metrics with data sources |
| `tasks/8.2a-metric-recording.md` | Event recording infrastructure |
| `tasks/8.2b-metric-calculation.md` | Metric calculation engine |

**Pick up any task file independently.** Each contains:
- Full implementation steps
- Code examples
- Validation criteria
- Test requirements
- Files to create/modify

---

*Phase 8 Tracker | Version 3.0 | 2026-01-07*
*Revised after brutal critique - see CRITIQUE.md*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P8.P.1 | Add dispute + escalation metrics | `docs/PHILOSOPHY.md`, `src/true_vkg/metrics/` | P1.P.4 | Metric list | Phase 16 release thresholds | Metrics are internal only | New dispute type |
| P8.P.2 | Define evidence packet completeness metrics | `docs/PHILOSOPHY.md`, `src/true_vkg/metrics/` | P1.P.1 | Completeness score + threshold | Phase 20 completeness gate | Evidence packet schema versioned | Missing field trend |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P8.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P8.R.2 | Task necessity review for P8.P.* | `task/4.0/phases/phase-8/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P8.P.1-P8.P.2 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 16/20 | Redundant task discovered |
| P8.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P8.P.1-P8.P.2 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P8.R.4 | Ensure metrics are internal (non-marketing) | `docs/PHILOSOPHY.md` | P8.P.1 | Metrics scope note | Scope referenced in release docs | Avoid marketing metrics | Metrics misuse detected |

### Dynamic Task Spawning (Alignment)

**Trigger:** Metric regression detected.
**Spawn:** Add root-cause analysis task.
**Example spawned task:** P8.P.3 Investigate dispute metric regression.
