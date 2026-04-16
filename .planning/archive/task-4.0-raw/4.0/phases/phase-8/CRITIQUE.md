# Phase 8 Brutal Critique

## Critical Issues Found

### 1. MISSING: Where Does Metric Data Come From?
**Severity: BLOCKER**

The entire phase assumes metrics can be "recorded" but never explains:
- How does `record_detection` know what was "expected"?
- Where is the ground truth for false positives?
- Who marks findings as confirmed vs rejected?
- How does scaffold compilation get tracked?

**Reality Check:** Without a labeled benchmark dataset, you CANNOT calculate precision/recall. Task 8.1 defines metrics, but Task 8.2 tries to implement calculation without explaining data sources.

**Fix Required:** Add explicit data source tasks before metric calculation.

---

### 2. Task 8.2 is MONOLITHIC (6h estimate is fiction)
**Severity: HIGH**

Task 8.2 "Metrics Tracker Implementation" tries to:
1. Define 8 different record_* methods
2. Calculate 8 different metrics (each with edge cases)
3. Handle persistence
4. Manage historical data

This is at least 3-4 separate tasks. The estimate of 6h assumes zero edge cases, zero bugs, zero testing.

---

### 3. Task 8.3-8.4-8.5 Dependency Chain is Unclear
**Severity: MEDIUM**

The dependency graph shows:
```
8.2 -> 8.3 (Historical Storage) -> 8.4 (Alerting) and 8.5 (CLI)
```

But CLI commands in 8.5 include `vkg metrics history` which needs historical storage. And `vkg metrics alerts` needs alerting. So the dependency is actually:
- 8.5 depends on BOTH 8.3 AND 8.4
- Not what the graph shows

---

### 4. NO EXISTING METRICS MODULE
**Severity: HIGH**

File locations say `src/true_vkg/metrics/` but `ls src/true_vkg/` shows NO metrics directory exists. Need to clarify:
- Create new module from scratch
- Schema for metric storage
- Integration points with existing CLI

---

### 5. "Scaffold Compile Rate" Metric is Undefined
**Severity: MEDIUM**

Metric 4 says "compiled / total_scaffolds" but:
- What is a scaffold? (Not defined anywhere in Phase 8)
- Where do scaffolds come from? (Phase 11? Phase 6 Beads?)
- How do you know if a scaffold "compiled"?

This metric cannot be implemented without Phase 6/11 dependencies.

---

### 6. Task 8.6 Dashboard is Marked "Optional" but Has 6h Estimate
**Severity: LOW**

If it's optional, don't estimate 6h. If you're spending 6h, it's not optional. Decide.

---

### 7. Performance Baseline (8.8) Has No Existing Baseline
**Severity: MEDIUM**

Task 8.8 says "Record in: benchmarks/performance_baseline.json" but:
- File doesn't exist
- No schema defined
- No tooling to measure described metrics

"Measurement Protocol" shows manual commands, not automated tooling.

---

### 8. CI Integration (8.7) Depends on GitHub Actions but No Auth Setup
**Severity: HIGH**

Task 8.7 creates `.github/workflows/metrics.yml` but:
- No mention of secrets management
- No mention of where metrics are stored between runs
- No mention of how PR comments are authenticated

---

## Recommendations

1. **Split Task 8.2** into 8.2a (recording), 8.2b (calculation), 8.2c (persistence)
2. **Add Task 8.0**: Data Source Setup - create labeled benchmark or explain data sources
3. **Fix Dependency Graph** to show accurate dependencies
4. **Define Scaffold** in glossary or link to Phase 6/11
5. **Create Module Skeleton** task before implementation tasks
6. **Add Integration Points** section showing CLI, benchmark, Bead connections
