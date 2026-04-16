---
phase: 08-test-performance-research
plan: 02
subsystem: testing
tags: [pytest, xdist, parallelization, performance, benchmark]

# Dependency graph
requires:
  - phase: 08-01
    provides: "baseline test execution timing (1178.75s)"
provides:
  - pytest-xdist dev dependency installed
  - parallel execution benchmark results (3.79x speedup)
  - optimal configuration identified (-n auto --dist loadfile)
affects: [08-03-PLAN, 08-04-PLAN]

# Tech tracking
tech-stack:
  added: [pytest-xdist>=3.8.0]
  patterns:
    - "loadfile distribution for LRU cache optimization"
    - "auto worker detection for CPU-based scaling"

key-files:
  created:
    - .planning/phases/08-test-performance-research/08-02-xdist-results.txt
  modified:
    - pyproject.toml

key-decisions:
  - "loadfile mode is fastest (315s vs 334s) due to LRU cache locality"
  - "auto worker count (10 on M2 Pro) is optimal"
  - "ADOPT pytest-xdist with 3.79x speedup exceeding 2x target"
  - "CI-only config recommended to avoid local overhead"

patterns-established:
  - "loadfile groups tests by source file for cache efficiency"
  - "Parallel testing maintains same failure set as serial"

# Metrics
duration: 62min
completed: 2026-01-20
---

# Phase 8 Plan 2: pytest-xdist Parallelization POC Summary

**pytest-xdist POC achieves 3.79x speedup (311s vs 1178s baseline) using -n auto --dist loadfile configuration**

## Performance

- **Duration:** 62 min (including 7 benchmark runs)
- **Started:** 2026-01-20T23:47:46Z
- **Completed:** 2026-01-21T00:50:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Installed pytest-xdist>=3.8.0 with execnet dependency
- Benchmarked 3 distribution modes (load, loadfile, loadscope)
- Benchmarked 4 worker counts (2, 4, 8, auto)
- Achieved 3.79x speedup with optimal configuration
- Verified no new test failures from parallelization

## Task Commits

Each task was committed atomically:

1. **Task 1: Install pytest-xdist and run initial benchmark** - `8cc4c0c` (perf)
2. **Task 2: Test distribution modes and optimize configuration** - `16d1808` (perf)
3. **Task 3: Verify all tests pass and document recommendations** - `830a8b8` (perf)

## Files Created/Modified

- `pyproject.toml` - Added pytest-xdist>=3.8.0 to dev dependencies
- `.planning/phases/08-test-performance-research/08-02-xdist-results.txt` - Full benchmark data

## Benchmark Results

### Distribution Mode Comparison (-n auto)

| Mode | Time | Notes |
|------|------|-------|
| load | 334s | Round-robin (default) |
| loadfile | 315s | **BEST** - groups by file |
| loadscope | 331s | Groups by class/module |

### Worker Count Scaling (loadfile mode)

| Workers | Time | Speedup |
|---------|------|---------|
| 2 | 599s | 1.97x |
| 4 | 393s | 3.0x |
| 8 | 331s | 3.56x |
| auto (10) | 315s | 3.74x |
| Final validation | 311s | **3.79x** |

### Performance Summary

| Metric | Value |
|--------|-------|
| Baseline (serial) | 1178.75s (19m 38s) |
| Best parallel | 311.34s (5m 11s) |
| Speedup | 3.79x |
| Reduction | 73.6% |
| Target (2x) | **EXCEEDED** |

## Why loadfile Mode is Fastest

The `loadfile` distribution mode outperforms others because:

1. **LRU Cache Locality**: Tests in `tests/graph_cache.py` use `@lru_cache` on `load_graph()`. When tests from the same file run on the same worker, the graph construction cost is amortized.

2. **Reduced IPC**: Fewer graph objects need to be serialized between workers since each worker handles complete test files.

3. **Predictable Load**: File-based grouping creates more balanced work distribution than random round-robin.

## Decisions Made

1. **loadfile mode over load/loadscope**: 6% faster due to LRU cache optimization
2. **auto worker count**: Let xdist detect optimal parallelism for the machine
3. **ADOPT recommendation**: 3.79x speedup justifies adding to dev workflow
4. **CI-only as alternative**: Option to keep local runs serial for debugging

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all benchmarks completed successfully with consistent results.

## Recommended Configuration

For pyproject.toml (enables parallel by default):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = ["examples"]
markers = ["semgrep: semgrep coverage and parity tests"]
addopts = "-n auto --dist loadfile"
```

Alternative (CI-only, keeps local serial):

```bash
# CI command
pytest tests/ -n auto --dist loadfile
```

## Compatibility

- **No fixture isolation issues**: Same 266 failures as baseline (pre-existing, not from xdist)
- **No thread-safety problems**: Consistent results across all runs
- **No flaky tests**: Same failure set in every benchmark

## Next Phase Readiness

Ready for Plan 08-03 (Fixture Optimization POC):
- xdist baseline established (311s best time)
- Fixture setup identified in 08-01 as secondary optimization target
- Plan 08-04 will compare all POC results

**Key metric for 08-04:**
- pytest-xdist: 311s (3.79x speedup)

---
*Phase: 08-test-performance-research*
*Completed: 2026-01-20*
