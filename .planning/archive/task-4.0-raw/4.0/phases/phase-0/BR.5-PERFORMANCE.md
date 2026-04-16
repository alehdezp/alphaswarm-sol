# BR.5: Performance Optimizations

**Status:** TODO
**Priority:** SHOULD
**Estimated Hours:** 12-16h
**Depends On:** BR.3 (detectors), BR.4 (pipeline)
**Unlocks:** Phase completion

---

## Objective

Achieve 20% minimum speedup on DVDeFi corpus through targeted optimizations. Current builder has several performance issues identified in code review.

---

## Current Performance Issues

### Issue 1: Repeated source_text.lower() calls

**Location:** Throughout `_add_functions` (1382 lines)

**Problem:** `source_text.lower()` is called multiple times per function for different checks.

```python
# Called here
source_text_clean = ...
source_text_lower = source_text_clean.lower()

# Then used in many places
if "deadline" in source_text_lower:
if "slippage" in source_text_lower:
if "oracle" in source_text_lower:
# ... 20+ more uses
```

**Fix:** Cache at FunctionContext creation, never recompute.

---

### Issue 2: Regex patterns compiled at runtime

**Location:** Various detection methods

**Problem:** `re.search(pattern, text)` compiles pattern each call.

```python
# Slow: compiles every call
if re.search(r"deadline|expir|valid", source_text, re.IGNORECASE):
```

**Fix:** Precompile in constants.py (done in BR.2), use compiled pattern.

---

### Issue 3: Repeated token list iterations

**Location:** Throughout builder.py

**Problem:** Same token checks repeated for every function.

```python
# Each iteration checks same tokens
has_only_owner = any(
    "onlyowner" in m.lower() or ("only" in m.lower() and "owner" in m.lower())
    for m in modifiers
)
```

**Fix:** Use frozenset intersection (O(1) average) instead of iteration.

---

### Issue 4: Expensive analysis without prerequisites

**Location:** Oracle detection, loop analysis

**Problem:** Full analysis runs even when prerequisites absent.

```python
# Runs full oracle analysis even if no oracle call
def _detect_oracle_signals(fn):
    # 50 lines of analysis...
```

**Fix:** Short-circuit when prerequisites missing.

```python
def _detect_oracle_signals(fn, function_ctx):
    if not function_ctx.has_oracle_call:  # Quick check first
        return {}
    # Full analysis only when needed
```

---

### Issue 5: Source file reads not cached

**Location:** `_source_location`, `_source_text`

**Problem:** Same source file read multiple times for different functions.

```python
# Called for every function, reads file each time
source_text = self._get_source_text(fn)
```

**Fix:** Use LRU cache keyed by (file, start_line, end_line).

---

## Implementation Plan

### OPT.1: Source text caching (3h)

```python
# In builder.py or new cache module

import functools

@functools.lru_cache(maxsize=1024)
def _get_source_text_cached(file_path: str, line_start: int, line_end: int) -> str:
    """Cached source text retrieval."""
    lines = self._source_cache.get(file_path)
    if lines is None:
        lines = Path(file_path).read_text().splitlines()
        self._source_cache[file_path] = lines
    return "\n".join(lines[line_start - 1:line_end])
```

### OPT.2: Precomputed lowercase text (2h)

In FunctionContext (already in BR.1):
```python
@dataclass(frozen=True)
class FunctionContext:
    source_text: str
    source_text_lower: str  # Computed once at context creation
```

### OPT.3: Set-based modifier checks (2h)

```python
# Before (O(n*m) worst case)
has_only_owner = any(
    "onlyowner" in m.lower() or ...
    for m in modifiers
)

# After (O(n) with set membership O(1))
modifier_set = frozenset(m.lower() for m in modifiers)
has_only_owner = bool(modifier_set & OWNER_MODIFIER_TOKENS)
```

### OPT.4: Short-circuit expensive analysis (4h)

Add quick-check methods to each detector:

```python
class OracleDetector(DetectorBase):
    def should_run(self, function_ctx: FunctionContext) -> bool:
        """Quick check if detector is relevant."""
        # Skip if no oracle-related tokens in source
        if not function_ctx.has_oracle_call:
            return False
        return True

    def detect(self, ...):
        if not self.should_run(function_ctx):
            return DetectorResult()  # Empty result, skip analysis
        # Full analysis...
```

### OPT.5: Parallel detector execution (4h)

For Tier 1 detectors (no dependencies), run in parallel:

```python
import concurrent.futures

def run_tier_parallel(
    self,
    tier_detectors: List[str],
    contract_ctx: ContractContext,
    function_ctx: FunctionContext,
    slither_fn: Any,
) -> Dict[str, DetectorResult]:
    """Run independent detectors in parallel."""
    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                self._detectors[name].detect,
                contract_ctx,
                function_ctx,
                slither_fn
            ): name
            for name in tier_detectors
        }

        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            results[name] = future.result()

    return results
```

---

## Benchmark Methodology

### Setup

```bash
# Download benchmark corpus (if not present)
bash scripts/download_benchmark_corpus.sh

# Create benchmark script
cat > scripts/benchmark_builder.py << 'EOF'
"""Benchmark builder performance on DVDeFi corpus."""

import time
import json
from pathlib import Path
from true_vkg.kg.builder import VKGBuilder

DVDEFI_PATH = Path("examples/damm-vuln-defi/src")
CHALLENGES = [
    "unstoppable", "truster", "naive-receiver", "side-entrance",
    "the-rewarder", "selfie", "puppet", "puppet-v2", "puppet-v3",
    "free-rider", "backdoor", "climber"
]

def benchmark():
    results = []

    for challenge in CHALLENGES:
        path = DVDEFI_PATH / challenge
        if not path.exists():
            continue

        builder = VKGBuilder(path)

        start = time.perf_counter()
        graph = builder.build(path)
        elapsed = time.perf_counter() - start

        results.append({
            "challenge": challenge,
            "time_seconds": elapsed,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
        })

        print(f"{challenge}: {elapsed:.2f}s ({len(graph.nodes)} nodes)")

    # Summary
    total = sum(r["time_seconds"] for r in results)
    print(f"\nTotal: {total:.2f}s")
    print(f"Average: {total/len(results):.2f}s per challenge")

    # Save results
    with open("benchmarks/builder_performance.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    benchmark()
EOF
```

### Baseline Measurement

```bash
# Run baseline benchmark (before optimizations)
uv run python scripts/benchmark_builder.py
cp benchmarks/builder_performance.json benchmarks/builder_performance_baseline.json
```

### Post-Optimization Measurement

```bash
# Run after each optimization
uv run python scripts/benchmark_builder.py

# Compare
uv run python -c "
import json
baseline = json.load(open('benchmarks/builder_performance_baseline.json'))
current = json.load(open('benchmarks/builder_performance.json'))

baseline_total = sum(r['time_seconds'] for r in baseline)
current_total = sum(r['time_seconds'] for r in current)

improvement = (baseline_total - current_total) / baseline_total * 100
print(f'Baseline: {baseline_total:.2f}s')
print(f'Current:  {current_total:.2f}s')
print(f'Improvement: {improvement:.1f}%')
"
```

---

## Success Criteria

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Total time reduction | >= 20% | Benchmark script comparison |
| Per-challenge average | < 2.0s | Benchmark output |
| Memory usage | No increase > 10% | `tracemalloc` profiling |
| Graph fingerprint | Identical | Fingerprint comparison |

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/true_vkg/kg/builder.py` | MODIFY - Add caching, short-circuits |
| `src/true_vkg/kg/pipeline.py` | MODIFY - Add parallel execution |
| `src/true_vkg/kg/contexts.py` | MODIFY - Precompute more values |
| `scripts/benchmark_builder.py` | CREATE |
| `benchmarks/builder_performance_baseline.json` | CREATE |
| `benchmarks/builder_performance.json` | CREATE |

---

## Validation Commands

```bash
# Baseline
uv run python scripts/benchmark_builder.py
cp benchmarks/builder_performance.json benchmarks/baseline.json

# After optimizations
uv run python scripts/benchmark_builder.py

# Verify fingerprint unchanged
uv run pytest tests/test_fingerprint.py -v

# Verify full suite passes
uv run pytest tests/ -v
```

---

## Acceptance Criteria

- [ ] 20% minimum speedup measured on DVDeFi corpus
- [ ] Graph fingerprint identical (CRITICAL)
- [ ] All tests pass
- [ ] No memory regression > 10%
- [ ] Benchmark results saved

---

## Rollback Procedure

If fingerprint changes or tests fail:

```bash
# Revert all changes
git checkout HEAD -- src/true_vkg/kg/

# Verify baseline restored
uv run python scripts/benchmark_builder.py
uv run pytest tests/test_fingerprint.py -v
```

---

## Performance Monitoring in CI

Add to `.github/workflows/ci.yml`:

```yaml
- name: Performance benchmark
  run: |
    uv run python scripts/benchmark_builder.py
    # Fail if regression > 10%
    uv run python -c "
    import json
    baseline = json.load(open('benchmarks/builder_performance_baseline.json'))
    current = json.load(open('benchmarks/builder_performance.json'))
    baseline_total = sum(r['time_seconds'] for r in baseline)
    current_total = sum(r['time_seconds'] for r in current)
    regression = (current_total - baseline_total) / baseline_total * 100
    if regression > 10:
        print(f'Performance regression: {regression:.1f}%')
        exit(1)
    "
```

---

*Task BR.5 | Version 1.0 | 2026-01-07*
