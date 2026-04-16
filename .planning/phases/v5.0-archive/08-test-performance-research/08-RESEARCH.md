# Phase 8: Test Performance Research - Research

**Researched:** 2026-01-20
**Domain:** Python pytest optimization, parallel testing, incremental testing
**Confidence:** HIGH

## Summary

This research investigates techniques to speed up the AlphaSwarm.sol test suite execution (7,104 tests, currently collecting in ~17s). The focus is on local-only optimizations without new CI infrastructure, targeting 2x+ improvement.

The pytest ecosystem offers multiple proven optimization approaches: **parallel execution (pytest-xdist)**, **incremental testing (pytest-testmon)**, **fixture optimization**, **import/collection optimization**, and **profiling tools**. Real-world case studies demonstrate dramatic improvements:
- PyPI/Warehouse: 163s to 30s (81% faster)
- Instawork: 50% reduction via testmon
- Discord: 20s to 2s median test via pytest-hot-reloading daemon

**Primary recommendation:** Start with pytest-xdist parallel execution (easiest win), profile with `--durations`, then evaluate pytest-testmon for incremental testing. For AlphaSwarm.sol specifically, optimize the `load_graph()` fixture caching strategy given 676 usages across 46 test files.

## Standard Stack

The established plugins/tools for pytest performance optimization:

### Core (Must Evaluate)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-xdist | 3.5+ | Parallel test execution across CPUs | De facto standard, maintained by pytest-dev |
| pytest-testmon | 2.1+ | Run only tests affected by code changes | Uses coverage.py for dependency mapping |
| pytest-profiling | 1.7+ | Per-test profiling with heat graphs | Detailed bottleneck identification |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-randomly | 3.15+ | Randomize test order | Detect hidden test dependencies |
| pytest-order | 1.2+ | Control test execution order | Run longest tests first |
| pytest-split | 0.9+ | Split tests for CI distribution | Time-based equal splits |
| pytest-hot-reloading | 0.1+ | Hot reload daemon mode | Long import times (>5s) |
| pytest-socket | 0.7+ | Prevent network access | Force mocking of external calls |
| pytest-monitor | 1.6+ | CPU/memory tracking per test | Resource usage analysis |

### Profiling/Analysis
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `--durations=N` | Show N slowest tests | First profiling step |
| `python -X importtime` | Import time analysis | Slow collection phase |
| hyperfine | Time entire suite runs | Benchmark comparisons |
| pytest-benchmark | Code snippet benchmarking | Micro-optimization validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest-xdist | pytest-parallel | xdist more mature, parallel less maintained |
| pytest-testmon | pytest-incremental | testmon uses coverage (more accurate), incremental uses AST |
| ward | pytest | ward unmaintained, smaller plugin ecosystem |

**Installation (POC evaluation):**
```bash
uv add --dev pytest-xdist pytest-testmon pytest-randomly pytest-order pytest-monitor
```

## Architecture Patterns

### Recommended Optimization Flow
```
1. Measure Baseline
   └── pytest --durations=0 > baseline.txt
   └── time pytest (total wall clock)

2. Profile Collection Phase
   └── pytest --collect-only
   └── python -X importtime -c "import tests"

3. Identify Bottlenecks
   └── pytest --durations=50 (slowest tests)
   └── pytest-monitor (resource hogs)

4. Apply Optimizations (order of effort)
   ├── pytest-xdist -n auto (immediate win)
   ├── Fixture scope optimization (medium effort)
   ├── pytest-testmon (incremental, medium setup)
   └── Import optimization (high effort, high reward)

5. Validate
   └── All tests pass
   └── Coverage unchanged
   └── Benchmark improvement
```

### AlphaSwarm.sol-Specific Pattern: Graph Caching

The test suite uses `load_graph()` with `@lru_cache(maxsize=None)` for BSKG building. This is called 676 times across 46 files. Current pattern:

```python
@lru_cache(maxsize=None)
def load_graph(contract_path: str):
    """Load BSKG from contract file with LRU caching."""
    return VKGBuilder(ROOT).build(full_path)
```

**Optimization potential:**
- LRU cache is process-local; with pytest-xdist, each worker rebuilds graphs
- Consider session-scoped fixture with `--dist loadfile` to group tests by contract
- Or disk-based caching for cross-process graph reuse

### Pattern: Parallel-Safe Fixtures
```python
# Source: pytest-xdist documentation
@pytest.fixture(scope="session")
def expensive_resource(tmp_path_factory, worker_id):
    """Session fixture that works with xdist workers."""
    if worker_id == "master":
        # Not running in parallel
        return create_resource()

    # Running in parallel - use worker-specific path
    root_tmp_dir = tmp_path_factory.getbasetemp().parent
    fn = root_tmp_dir / "data.json"

    with FileLock(str(fn) + ".lock"):
        if fn.is_file():
            return load_resource(fn)
        else:
            resource = create_resource()
            save_resource(fn, resource)
            return resource
```

### Pattern: Fixture Scope Optimization
```python
# Source: pytest fixture documentation

# BAD: Database connection per test
@pytest.fixture
def db_connection():
    conn = create_connection()
    yield conn
    conn.close()

# GOOD: Connection per module, truncate per test
@pytest.fixture(scope="module")
def db_connection():
    conn = create_connection()
    yield conn
    conn.close()

@pytest.fixture(autouse=True)
def clean_tables(db_connection):
    yield
    db_connection.truncate_all()
```

### Anti-Patterns to Avoid
- **Function-scoped expensive fixtures:** Graph building for every test instead of caching
- **Top-level imports of heavy libraries:** Slither imports at module level slow collection
- **Sleep-based waiting:** Use condition polling instead of `time.sleep()`
- **Shared mutable state with xdist:** Tests failing randomly in parallel mode

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel execution | Threading/multiprocessing | pytest-xdist | Process isolation, load balancing, mature |
| Test dependency tracking | AST parsing | pytest-testmon | Uses coverage.py, handles edge cases |
| Random ordering | Random.shuffle | pytest-randomly | Reproducible seeds, xdist compatible |
| Time-based splitting | Manual grouping | pytest-split | Execution time analysis, algorithm options |
| Hot reloading | importlib hacks | pytest-hot-reloading | jurigged integration, pytest hooks |
| Resource monitoring | Manual timing | pytest-monitor | CPU, memory, statistical analysis |

**Key insight:** Test optimization is a well-studied problem. Custom solutions miss edge cases around subprocess management, coverage integration, and pytest lifecycle hooks.

## Common Pitfalls

### Pitfall 1: xdist with Session Fixtures
**What goes wrong:** Session-scoped fixtures run once per worker, not once total
**Why it happens:** Each xdist worker is a separate process
**How to avoid:** Use `--dist loadfile` or `--dist loadscope`, or implement FileLock pattern
**Warning signs:** Tests pass in serial, fail/slow in parallel

### Pitfall 2: Coverage with xdist
**What goes wrong:** `coverage run -m pytest -n auto` reports 0% coverage
**Why it happens:** Bypasses pytest-cov's xdist integration
**How to avoid:** Always use `pytest --cov` with xdist, never `coverage run`
**Warning signs:** CI coverage drops when enabling parallel

### Pitfall 3: testmon Data Staleness
**What goes wrong:** testmon skips tests that should run
**Why it happens:** Dependency database out of sync, changed files not tracked
**How to avoid:** Regenerate `.testmondata` periodically, commit it to repo
**Warning signs:** Bugs slip through after refactoring

### Pitfall 4: Import-Time Side Effects
**What goes wrong:** Collection phase takes as long as test execution
**Why it happens:** Heavy libraries imported at module level trigger slow init
**How to avoid:** Defer imports, use `python -X importtime` to find offenders
**Warning signs:** `pytest --collect-only` is slow

### Pitfall 5: pytest-randomly Breaking Tests
**What goes wrong:** Tests fail when run in random order
**Why it happens:** Hidden dependencies between tests
**How to avoid:** This is actually valuable - fix the tests! Use `--randomly-seed=X` to reproduce
**Warning signs:** Flaky tests in CI

### Pitfall 6: Graph Caching with Parallel Workers (AlphaSwarm.sol Specific)
**What goes wrong:** Each xdist worker rebuilds the same BSKG graphs
**Why it happens:** `@lru_cache` is process-local, doesn't share across workers
**How to avoid:** Use `--dist loadfile` to group tests by contract, or implement disk cache
**Warning signs:** Parallel execution provides less speedup than expected

## Code Examples

Verified patterns from official sources:

### Basic xdist Usage
```bash
# Source: pytest-xdist documentation
# Auto-detect CPU cores
pytest -n auto

# Specific worker count
pytest -n 4

# Group by file (good for shared fixtures)
pytest -n auto --dist loadfile

# Group by scope (class/module)
pytest -n auto --dist loadscope
```

### xdist Configuration in pyproject.toml
```toml
# Source: pytest-xdist documentation
[tool.pytest.ini_options]
addopts = "-n auto --dist loadfile"
```

### testmon Usage
```bash
# Source: pytest-testmon documentation
# First run: build dependency database
pytest --testmon

# Subsequent runs: only affected tests
pytest --testmon

# Force full run
pytest --testmon-forceselect
```

### Profiling Slow Tests
```bash
# Source: pytest documentation
# Show 10 slowest tests
pytest --durations=10

# Show all test durations (with -vv for small durations)
pytest --durations=0 -vv

# With profiling
pytest --profile --profile-svg tests/
```

### Import Time Analysis
```bash
# Source: Python documentation
# Analyze import times
python -X importtime -c "import true_vkg" 2>&1 | head -50

# Visualize at: https://kmichel.github.io/python-importtime-graph/
```

### Python 3.12+ Coverage Optimization
```bash
# Source: coverage.py documentation, Trail of Bits case study
# Use sys.monitoring for faster coverage (Python 3.12+)
COVERAGE_CORE=sysmon pytest --cov=true_vkg

# Or in pyproject.toml
[tool.coverage.run]
core = "sysmon"  # Python 3.14+ defaults to this
```

### pytest-monitor Usage
```bash
# Source: pytest-monitor documentation
# Track resource usage
pytest --monitor

# Results stored in .pymon SQLite database
```

### Fixture Scope Comparison
```python
# Source: pytest fixture documentation

# Function scope (default) - runs for each test
@pytest.fixture(scope="function")
def fresh_data(): ...

# Module scope - runs once per test file
@pytest.fixture(scope="module")
def shared_connection(): ...

# Session scope - runs once per pytest invocation
@pytest.fixture(scope="session")
def expensive_setup(): ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Serial execution | pytest-xdist parallel | Standard since 2015 | 2-10x speedup |
| sys.settrace coverage | sys.monitoring (3.12+) | Python 3.12, Dec 2023 | 50%+ coverage overhead reduction |
| Manual test selection | pytest-testmon | Mature since 2020 | 50%+ local development speedup |
| File-watching restart | Hot reloading daemon | 2023-2024 | 10x iteration speed (Discord) |
| pytest-ordering | pytest-order | 2021 | pytest-ordering deprecated |
| pytest-lazy-fixture | pytest-lazy-fixtures | 2023 | Original unmaintained |

**Deprecated/outdated:**
- pytest-ordering: Use pytest-order instead
- pytest-lazy-fixture: Use pytest-lazy-fixtures instead
- pytest-parallel: Less maintained than pytest-xdist
- ward: Creator no longer actively maintaining

## Open Questions

Things that couldn't be fully resolved:

1. **Slither compilation caching with pytest**
   - What we know: Slither uses crytic-compile for AST generation
   - What's unclear: Whether compilation results can be cached across test runs
   - Recommendation: Profile whether Slither compilation is a bottleneck; if so, investigate crytic-compile caching or pre-compiled artifact storage

2. **Optimal xdist distribution for AlphaSwarm.sol**
   - What we know: `--dist loadfile` groups tests by file, `loadscope` by class/module
   - What's unclear: Which distribution minimizes graph rebuild overhead given `load_graph()` caching
   - Recommendation: POC both modes, measure graph cache hit rates

3. **pytest-testmon vs pytest-incremental accuracy**
   - What we know: testmon uses coverage.py (more accurate), incremental uses AST
   - What's unclear: Which handles the BSKG codebase better (dynamic imports, Slither integration)
   - Recommendation: POC pytest-testmon first (more widely used), fall back to incremental if issues

## Sources

### Primary (HIGH confidence)
- [pytest-xdist official documentation](https://pytest-xdist.readthedocs.io/en/stable/distribution.html) - Distribution modes, configuration
- [pytest fixture documentation](https://docs.pytest.org/en/stable/how-to/fixtures.html) - Scope optimization
- [pytest-testmon GitHub](https://github.com/tarpas/pytest-testmon) - Incremental testing
- [coverage.py sys.monitoring](https://nedbatchelder.com/blog/202312/coveragepy_with_sysmonitoring.html) - Python 3.12+ optimization

### Secondary (MEDIUM confidence)
- [Trail of Bits PyPI optimization](https://blog.trailofbits.com/2025/05/01/making-pypis-test-suite-81-faster/) - Case study, 163s to 30s
- [Instawork testmon case study](https://engineering.instawork.com/test-impact-analysis-the-secret-to-faster-pytest-runs-e44021306603) - 50% reduction
- [awesome-pytest-speedup](https://github.com/zupo/awesome-pytest-speedup) - Comprehensive technique list
- [pytest-with-eric runtime improvements](https://pytest-with-eric.com/pytest-advanced/pytest-improve-runtime/) - 13 techniques

### Tertiary (LOW confidence)
- [Discord pytest daemon](https://discord.com/blog/pytest-daemon-10x-local-test-iteration-speed) - Hot reloading pattern (specific to Discord's setup)
- [pytest-hot-reloading](https://github.com/JamesHutchison/pytest-hot-reloading) - Daemon implementation (may not suit all codebases)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest-xdist and testmon are industry standard
- Architecture: HIGH - Fixture scoping and xdist patterns well-documented
- Pitfalls: HIGH - Common issues documented in official docs and case studies
- AlphaSwarm.sol-specific: MEDIUM - Load_graph caching needs profiling to validate

**Research date:** 2026-01-20
**Valid until:** 2026-03-20 (60 days - stable domain, slow-moving ecosystem)

---

## Quick Reference: POC Priority Order

Based on research, recommended POC implementation order:

1. **pytest-xdist** (HIGH priority, LOW effort)
   - Expected: 50-80% speedup
   - Command: `pytest -n auto`
   - Risk: Session fixtures may need adjustment

2. **--durations profiling** (HIGH priority, NO effort)
   - Purpose: Identify actual bottlenecks before optimizing
   - Command: `pytest --durations=50`

3. **Fixture scope audit** (MEDIUM priority, MEDIUM effort)
   - Focus on `load_graph()` usage pattern
   - Expected: Depends on current cache hit rate

4. **pytest-testmon** (MEDIUM priority, LOW effort)
   - Expected: 50%+ speedup for incremental runs
   - Command: `pytest --testmon`
   - Risk: Initial database build takes full run

5. **Python 3.12+ coverage optimization** (LOW priority, NO effort)
   - Applicable if using coverage
   - Command: `COVERAGE_CORE=sysmon pytest --cov`

6. **pytest-hot-reloading** (LOW priority, MEDIUM effort)
   - Only if import time >5s
   - Validate: `python -X importtime` first
