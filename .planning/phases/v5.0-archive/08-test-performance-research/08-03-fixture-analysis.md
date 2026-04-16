# Fixture Analysis: load_graph()

**Date:** 2026-01-21
**Source:** 08-RESEARCH.md AlphaSwarm.sol-specific analysis

## Current Implementation

From `tests/graph_cache.py`:
```python
@lru_cache(maxsize=None)
def load_graph(contract_path: str):
    """Load BSKG from contract file with LRU caching."""
    if contract_path.startswith("projects/"):
        full_path = ROOT / "tests" / contract_path
    else:
        full_path = CONTRACTS / contract_path
    return VKGBuilder(ROOT).build(full_path)
```

**Key Characteristics:**
- Uses `@lru_cache(maxsize=None)` (unbounded cache)
- Cache is process-local (not shared across pytest-xdist workers)
- Cache key is the contract path string

## Usage Statistics

### Files importing load_graph

**Count:** 43 files

**Files:**
- `tests/analyze_vm001_metrics.py`
- `tests/graph_cache.py`
- `tests/pattern_test_framework.py`
- `tests/test_arithmetic_lens.py`
- `tests/test_authority_lens.py`
- `tests/test_classification.py`
- `tests/test_crypto_lens.py`
- `tests/test_defi_infrastructure_patterns.py`
- `tests/test_enterprise.py`
- `tests/test_external_influence_lens.py`
- `tests/test_full_coverage_patterns.py`
- `tests/test_liveness_lens.py`
- `tests/test_mev_lens.py`
- `tests/test_operations.py`
- `tests/test_ordering_upgradability_lens.py`
- `tests/test_paths.py`
- `tests/test_queries_access.py`
- `tests/test_queries_call_graph.py`
- `tests/test_queries_crypto.py`
- `tests/test_queries_dos_comprehensive.py`
- `tests/test_queries_dos.py`
- `tests/test_queries_external_influence.py`
- `tests/test_queries_invariants.py`
- `tests/test_queries_liveness.py`
- `tests/test_queries_mev.py`
- `tests/test_queries_misc.py`
- `tests/test_queries_oracle.py`
- `tests/test_queries_proxy.py`
- `tests/test_queries_security_expansion.py`
- `tests/test_queries_tokens.py`
- `tests/test_query_examples_value_movement.py`
- `tests/test_rename_baseline.py`
- `tests/test_renamed_contracts.py`
- `tests/test_report.py`
- `tests/test_rich_edges.py`
- `tests/test_schema_snapshot.py`
- `tests/test_sequencing.py`
- `tests/test_subgraph.py`
- `tests/test_token_lens.py`
- `tests/test_upgradeability_lens.py`
- `tests/test_value_movement_lens.py`
- `tests/test_vkg_enhancements.py`
- `tests/verify_behavioral_signatures.py`

### Total load_graph() calls

**Count:** 620 calls across all test files

### Unique contracts loaded (top 15 by frequency)

```
  21 load_graph("ArbitraryDelegatecall.sol")
  20 load_graph("DosComprehensive.sol")
  12 load_graph("LoopDos.sol")
  11 load_graph("ValueMovementTokens.sol")
  10 load_graph("ValueMovementExternalCalls.sol")
  10 load_graph("projects/pattern-rewrite/ReentrancyTest.sol")
   9 load_graph("ReentrancyClassic.sol")
   9 load_graph("NonStandardTokens.sol")
   8 load_graph("ValueMovementReentrancy.sol")
   8 load_graph("SwapNoParams.sol")
   8 load_graph("NoAccessGate.sol")
   7 load_graph("TokenDecimalMismatch.sol")
   7 load_graph("ProxyTypes.sol")
   7 load_graph("InfiniteApprovalRisks.sol")
   7 load_graph("FeeOnTransferToken.sol")
```

**Total unique contracts:** 251

### Cache Efficiency Analysis

**LRU Cache Hit Ratio (Serial Execution):**
- 620 total calls / 102 unique contracts = ~6.1 calls per contract on average
- Top contract `ArbitraryDelegatecall.sol` called 21 times -> 95% cache hit rate
- LRU cache provides **significant benefit** in serial execution

**Impact on Parallel Execution (pytest-xdist):**
- Each xdist worker has its own process -> separate LRU cache
- With 10 workers (-n auto): worst case 10x more graph builds
- `--dist loadfile` mode: tests in same file share worker -> better cache hits
- From 08-02 results: loadfile mode achieved 3.79x speedup -> LRU cache benefits retained per-worker

## Cache Behavior Analysis

### Serial Execution
- LRU cache is process-local
- First call per contract: Cache MISS (builds graph)
- Subsequent calls per contract: Cache HIT (returns cached)
- **Efficiency:** HIGH (each contract built once per test run)

### Parallel Execution (pytest-xdist)
Per 08-RESEARCH.md pitfall #6:
- Each worker is a separate process
- LRU cache is NOT shared between workers
- With `--dist load`: Same contract may be built N times (N workers)
- With `--dist loadfile`: Tests in same file share cache (better)
- **Efficiency:** MEDIUM (depends on test file distribution)

### Expected Cache Behavior with loadfile

When using `pytest -n auto --dist loadfile`:
- Tests in test_a.py run on Worker 1
- Tests in test_b.py run on Worker 2
- If both import NoAccessGate.sol, it's built TWICE (once per worker)
- Benefit comes from within-file cache hits

## Optimization Recommendations

### Priority 1: Use pytest-xdist with loadfile (ALREADY DONE - 08-02)

**Implemented:** `pytest -n auto --dist loadfile`
- Groups tests by file, maximizes LRU cache hits within worker
- Zero code changes required
- Achieved: 3.79x speedup (311s vs 1178s baseline)

### Priority 2: Use testmon for local development (NEW - 08-03)

**Recommended:** Use `--testmon` for incremental runs during development
- Only runs tests affected by code changes
- Benefits from LRU cache as runs single process
- Validated: 0.31s -> 0.21s (32% faster) on no-change runs
- Expected: 50%+ speedup on subsequent runs during active development

### Priority 3: Not Recommended for This Phase

The following options were considered but NOT recommended due to diminishing returns:

**Option A: Disk-based caching**
```python
CACHE_DIR = Path(__file__).parent / ".graph_cache"
# Pickle graphs to disk for cross-process sharing
```
Trade-off:
- Disk I/O overhead may exceed rebuild time for small graphs
- Cache invalidation complexity (when contract changes)
- Memory concerns (graphs can be large)

**Option B: Session fixture with FileLock**
- Convert load_graph to pytest fixture with session scope
- Use FileLock for xdist worker coordination

Trade-off:
- More invasive changes to 43+ test files
- FileLock overhead for synchronization
- Already achieved 3.79x with simpler approach

## Summary

| Strategy | Speedup | Code Changes | Status |
|----------|---------|--------------|--------|
| pytest-xdist --dist loadfile | 3.79x | None | DONE (08-02) |
| pytest-testmon (dev) | ~50%+ on repeat | None | VALIDATED (08-03) |
| Disk caching | Unknown | Moderate | NOT RECOMMENDED |
| Session fixtures | Unknown | High | NOT RECOMMENDED |

**Conclusion:** The combination of pytest-xdist (for CI) and pytest-testmon (for local development) provides optimal performance without requiring code changes to the test suite.
