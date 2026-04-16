#!/usr/bin/env python3
"""
Run performance baselines for GA validation.

Establishes SLA targets and measures KG build + query performance
for regression detection.

Usage:
    uv run python scripts/run_performance_baseline.py \\
        --contracts tests/contracts/ReentrancyClassic.sol \\
        --iterations 3 \\
        --output .vrs/validation/baseline/performance.yaml
"""

from __future__ import annotations

import argparse
import gc
import statistics
import subprocess
import sys
import time
import tracemalloc
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


# SLA Targets for GA Release
SLA_TARGETS = {
    "kg_build": {
        "median_seconds": 30.0,  # < 30s median for standard contracts
        "p95_seconds": 60.0,     # < 60s p95 for all contracts
        "max_seconds": 120.0,    # Hard timeout at 120s
    },
    "query": {
        "median_seconds": 5.0,   # < 5s median for queries
        "p95_seconds": 10.0,     # < 10s p95
        "max_seconds": 30.0,     # Hard timeout at 30s
    },
    "memory": {
        "max_mb": 500.0,         # < 500MB peak memory
    },
}


@dataclass
class TimingStats:
    """Statistics for a timed operation."""
    name: str
    iterations: int
    times_seconds: list[float]
    successes: int = 0
    failures: int = 0

    @property
    def median_seconds(self) -> float:
        return statistics.median(self.times_seconds) if self.times_seconds else 0.0

    @property
    def mean_seconds(self) -> float:
        return statistics.mean(self.times_seconds) if self.times_seconds else 0.0

    @property
    def stdev_seconds(self) -> float:
        return statistics.stdev(self.times_seconds) if len(self.times_seconds) > 1 else 0.0

    @property
    def min_seconds(self) -> float:
        return min(self.times_seconds) if self.times_seconds else 0.0

    @property
    def max_seconds(self) -> float:
        return max(self.times_seconds) if self.times_seconds else 0.0

    @property
    def p95_seconds(self) -> float:
        if not self.times_seconds:
            return 0.0
        if len(self.times_seconds) < 20:
            return self.max_seconds
        sorted_times = sorted(self.times_seconds)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "times_seconds": self.times_seconds,
            "median_seconds": round(self.median_seconds, 3),
            "mean_seconds": round(self.mean_seconds, 3),
            "stdev_seconds": round(self.stdev_seconds, 3),
            "min_seconds": round(self.min_seconds, 3),
            "max_seconds": round(self.max_seconds, 3),
            "p95_seconds": round(self.p95_seconds, 3),
            "successes": self.successes,
            "failures": self.failures,
        }


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    peak_mb: float
    contract_name: str


def time_operation(
    name: str,
    func: Callable[[], bool],
    iterations: int = 3,
    warmup: int = 0,
) -> TimingStats:
    """Time an operation multiple times and return stats.

    Args:
        name: Operation name for reporting
        func: Function to time, returns True on success
        iterations: Number of timed iterations
        warmup: Number of warmup iterations (not counted)
    """
    # Warmup iterations
    for i in range(warmup):
        print(f"  Warmup {i+1}/{warmup}...", end=" ", flush=True)
        try:
            func()
            print("done")
        except Exception as e:
            print(f"failed: {e}")

    times = []
    successes = 0
    failures = 0

    for i in range(iterations):
        gc.collect()

        print(f"  Iteration {i+1}/{iterations}...", end=" ", flush=True)
        start = time.perf_counter()
        try:
            success = func()
            if success:
                successes += 1
            else:
                failures += 1
        except Exception as e:
            print(f"failed: {e}")
            failures += 1
            success = False
        elapsed = time.perf_counter() - start
        times.append(elapsed)

        if success:
            print(f"{elapsed:.2f}s")
        else:
            print(f"{elapsed:.2f}s (FAILED)")

    return TimingStats(
        name=name,
        iterations=iterations,
        times_seconds=times,
        successes=successes,
        failures=failures,
    )


def run_kg_build_baseline(
    contract_path: Path,
    iterations: int = 3,
) -> tuple[TimingStats, MemoryStats | None]:
    """Benchmark KG building for a single contract.

    Returns timing stats and memory stats.
    """
    contract_name = contract_path.name
    memory_stats = None
    peak_memory = 0.0

    def build_kg() -> bool:
        nonlocal peak_memory

        tracemalloc.start()
        try:
            result = subprocess.run(
                ["uv", "run", "alphaswarm", "build-kg", str(contract_path)],
                capture_output=True,
                timeout=SLA_TARGETS["kg_build"]["max_seconds"],
                cwd=str(ROOT),
            )

            _, peak = tracemalloc.get_traced_memory()
            peak_memory = max(peak_memory, peak / 1024 / 1024)

            if result.returncode != 0:
                stderr = result.stderr.decode()[:200]
                print(f"Build failed: {stderr}")
                return False
            return True
        finally:
            tracemalloc.stop()

    print(f"\nBenchmarking KG build: {contract_name}")
    timing = time_operation(f"build-kg:{contract_name}", build_kg, iterations)

    if peak_memory > 0:
        memory_stats = MemoryStats(peak_mb=round(peak_memory, 2), contract_name=contract_name)

    return timing, memory_stats


def run_query_baseline(
    query: str,
    graph_path: Path | None = None,
    iterations: int = 3,
) -> TimingStats:
    """Benchmark query execution.

    If graph_path is None, uses default graph location.
    """
    def run_query() -> bool:
        cmd = ["uv", "run", "alphaswarm", "query", query]
        if graph_path:
            cmd.extend(["--graph", str(graph_path)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=SLA_TARGETS["query"]["max_seconds"],
            cwd=str(ROOT),
        )

        if result.returncode != 0:
            stderr = result.stderr.decode()[:200]
            print(f"Query failed: {stderr}")
            return False
        return True

    query_short = query[:30] + "..." if len(query) > 30 else query
    print(f"\nBenchmarking query: {query_short}")
    return time_operation(f"query:{query_short}", run_query, iterations)


def check_sla_violations(
    kg_benchmarks: list[TimingStats],
    query_benchmarks: list[TimingStats],
    memory_stats: list[MemoryStats],
) -> list[dict[str, Any]]:
    """Check for SLA violations.

    Returns list of violation records.
    """
    violations = []

    # Check KG build SLAs
    for bench in kg_benchmarks:
        if bench.median_seconds > SLA_TARGETS["kg_build"]["median_seconds"]:
            violations.append({
                "type": "kg_build_median",
                "benchmark": bench.name,
                "value": bench.median_seconds,
                "target": SLA_TARGETS["kg_build"]["median_seconds"],
                "severity": "warning",
            })

        if bench.p95_seconds > SLA_TARGETS["kg_build"]["p95_seconds"]:
            violations.append({
                "type": "kg_build_p95",
                "benchmark": bench.name,
                "value": bench.p95_seconds,
                "target": SLA_TARGETS["kg_build"]["p95_seconds"],
                "severity": "error",
            })

    # Check query SLAs
    for bench in query_benchmarks:
        if bench.median_seconds > SLA_TARGETS["query"]["median_seconds"]:
            violations.append({
                "type": "query_median",
                "benchmark": bench.name,
                "value": bench.median_seconds,
                "target": SLA_TARGETS["query"]["median_seconds"],
                "severity": "warning",
            })

    # Check memory SLAs
    for mem in memory_stats:
        if mem.peak_mb > SLA_TARGETS["memory"]["max_mb"]:
            violations.append({
                "type": "memory_peak",
                "benchmark": mem.contract_name,
                "value": mem.peak_mb,
                "target": SLA_TARGETS["memory"]["max_mb"],
                "severity": "error",
            })

    return violations


def compare_with_baseline(
    current: dict[str, Any],
    baseline_path: Path,
    regression_threshold: float = 0.2,
) -> list[dict[str, Any]]:
    """Compare current results with baseline for regression detection.

    Args:
        current: Current benchmark results
        baseline_path: Path to baseline YAML file
        regression_threshold: Percentage increase that triggers regression (0.2 = 20%)

    Returns:
        List of regression records
    """
    if not baseline_path.exists():
        return []

    with open(baseline_path) as f:
        baseline = yaml.safe_load(f)

    regressions = []

    # Build lookup for baseline benchmarks
    baseline_kg = {b["name"]: b for b in baseline.get("kg_benchmarks", [])}
    baseline_query = {b["name"]: b for b in baseline.get("query_benchmarks", [])}

    # Check KG build regressions
    for bench in current.get("kg_benchmarks", []):
        name = bench["name"]
        if name in baseline_kg:
            old_median = baseline_kg[name]["median_seconds"]
            new_median = bench["median_seconds"]
            if old_median > 0 and (new_median - old_median) / old_median > regression_threshold:
                regressions.append({
                    "type": "kg_build_regression",
                    "benchmark": name,
                    "old_median": old_median,
                    "new_median": new_median,
                    "increase_pct": round((new_median - old_median) / old_median * 100, 1),
                })

    # Check query regressions
    for bench in current.get("query_benchmarks", []):
        name = bench["name"]
        if name in baseline_query:
            old_median = baseline_query[name]["median_seconds"]
            new_median = bench["median_seconds"]
            if old_median > 0 and (new_median - old_median) / old_median > regression_threshold:
                regressions.append({
                    "type": "query_regression",
                    "benchmark": name,
                    "old_median": old_median,
                    "new_median": new_median,
                    "increase_pct": round((new_median - old_median) / old_median * 100, 1),
                })

    return regressions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run performance baselines for GA validation"
    )
    parser.add_argument(
        "--contracts",
        nargs="+",
        type=Path,
        help="Contract paths to benchmark (relative to project root)",
    )
    parser.add_argument(
        "--queries",
        nargs="+",
        help="VQL queries to benchmark",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".vrs/validation/baseline/performance.yaml"),
        help="Output YAML file for results",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per benchmark",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        help="Compare against existing baseline for regression detection",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=0,
        help="Number of warmup iterations (not counted)",
    )
    parser.add_argument(
        "--all-contracts",
        action="store_true",
        help="Benchmark all test contracts (use with caution)",
    )

    args = parser.parse_args()

    # Default contracts if none specified
    if args.contracts is None and not args.all_contracts:
        args.contracts = [
            ROOT / "tests/contracts/ReentrancyClassic.sol",
            ROOT / "tests/contracts/TokenCalls.sol",
            ROOT / "tests/contracts/VaultInflation.sol",
        ]
    elif args.all_contracts:
        contracts_dir = ROOT / "tests/contracts"
        args.contracts = list(contracts_dir.glob("*.sol"))[:10]  # Limit to 10 for safety

    # Default queries
    if args.queries is None:
        args.queries = [
            "FIND functions WHERE visibility = public AND writes_state",
            "FIND functions WHERE has_external_call AND NOT has_reentrancy_guard",
        ]

    print("=" * 60)
    print("PERFORMANCE BASELINE RUNNER - GA Validation")
    print("=" * 60)
    print(f"Iterations: {args.iterations}")
    print(f"Contracts: {len(args.contracts)}")
    print(f"Queries: {len(args.queries)}")
    print(f"Output: {args.output}")
    print()

    # Run KG build benchmarks
    kg_benchmarks: list[TimingStats] = []
    memory_stats: list[MemoryStats] = []

    for contract in args.contracts:
        contract_path = contract if contract.is_absolute() else ROOT / contract
        if not contract_path.exists():
            print(f"WARNING: Contract not found: {contract_path}")
            continue

        timing, mem = run_kg_build_baseline(contract_path, args.iterations)
        kg_benchmarks.append(timing)
        if mem:
            memory_stats.append(mem)

    # Run query benchmarks
    query_benchmarks: list[TimingStats] = []

    for query in args.queries:
        timing = run_query_baseline(query, iterations=args.iterations)
        query_benchmarks.append(timing)

    # Build results dict
    results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "iterations": args.iterations,
        "sla_targets": SLA_TARGETS,
        "kg_benchmarks": [b.to_dict() for b in kg_benchmarks],
        "query_benchmarks": [b.to_dict() for b in query_benchmarks],
        "memory_stats": [asdict(m) for m in memory_stats],
    }

    # Check SLA violations
    violations = check_sla_violations(kg_benchmarks, query_benchmarks, memory_stats)
    results["sla_violations"] = violations

    # Check regressions if baseline provided
    regressions = []
    if args.compare:
        regressions = compare_with_baseline(results, args.compare)
        results["regressions"] = regressions

    # Save results
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(results, f, default_flow_style=False, sort_keys=False)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print("\nKG Build Performance:")
    for bench in kg_benchmarks:
        status = "PASS" if bench.median_seconds <= SLA_TARGETS["kg_build"]["median_seconds"] else "WARN"
        print(f"  [{status}] {bench.name}: median={bench.median_seconds:.2f}s "
              f"(target < {SLA_TARGETS['kg_build']['median_seconds']}s)")

    print("\nQuery Performance:")
    for bench in query_benchmarks:
        status = "PASS" if bench.median_seconds <= SLA_TARGETS["query"]["median_seconds"] else "WARN"
        print(f"  [{status}] {bench.name}: median={bench.median_seconds:.2f}s "
              f"(target < {SLA_TARGETS['query']['median_seconds']}s)")

    if violations:
        print(f"\nSLA VIOLATIONS ({len(violations)}):")
        for v in violations:
            print(f"  [{v['severity'].upper()}] {v['type']}: {v['benchmark']} "
                  f"({v['value']:.2f} > {v['target']})")
    else:
        print("\nAll SLAs met!")

    if regressions:
        print(f"\nREGRESSIONS ({len(regressions)}):")
        for r in regressions:
            print(f"  {r['type']}: {r['benchmark']} "
                  f"({r['old_median']:.2f}s -> {r['new_median']:.2f}s, +{r['increase_pct']}%)")

    print(f"\nBaseline saved to: {output_path}")

    # Return exit code based on violations
    if any(v["severity"] == "error" for v in violations):
        return 1
    if regressions:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
