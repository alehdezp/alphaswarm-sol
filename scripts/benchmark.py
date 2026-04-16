#!/usr/bin/env python3
"""
Performance Benchmarking Script

Measures VKG build performance including:
- Build time per contract
- Memory usage
- Graph size (nodes/edges)

Part of Phase 0: Foundation & Baseline
"""

import argparse
import gc
import json
import os
import sys
import time
import tracemalloc
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alphaswarm_sol.kg.builder import VKGBuilder


@dataclass
class BenchmarkResult:
    """Result of benchmarking a single contract."""
    contract_path: str
    contract_name: str
    build_time_seconds: float
    peak_memory_mb: float
    node_count: int
    edge_count: int
    success: bool
    error: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Summary of all benchmark results."""
    timestamp: str
    total_contracts: int
    successful_builds: int
    failed_builds: int
    total_build_time_seconds: float
    average_build_time_seconds: float
    max_build_time_seconds: float
    min_build_time_seconds: float
    total_peak_memory_mb: float
    average_peak_memory_mb: float
    max_peak_memory_mb: float
    total_nodes: int
    total_edges: int
    results: List[Dict[str, Any]] = field(default_factory=list)


def benchmark_contract(contract_path: Path) -> BenchmarkResult:
    """Benchmark building VKG for a single contract."""
    gc.collect()
    tracemalloc.start()

    start_time = time.perf_counter()
    success = True
    error = None
    node_count = 0
    edge_count = 0

    try:
        builder = VKGBuilder(ROOT)
        graph = builder.build(contract_path)
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)
    except Exception as e:
        success = False
        error = str(e)

    end_time = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return BenchmarkResult(
        contract_path=str(contract_path),
        contract_name=contract_path.name,
        build_time_seconds=end_time - start_time,
        peak_memory_mb=peak / 1024 / 1024,
        node_count=node_count,
        edge_count=edge_count,
        success=success,
        error=error
    )


def benchmark_all_contracts(contracts_dir: Path, pattern: str = "*.sol") -> List[BenchmarkResult]:
    """Benchmark all contracts in a directory."""
    results = []
    contracts = list(contracts_dir.rglob(pattern))

    # Filter out already-known problematic patterns
    contracts = [c for c in contracts if not any(p in str(c) for p in [".vrs", "__pycache__"])]

    print(f"Found {len(contracts)} contracts to benchmark")

    for i, contract in enumerate(contracts, 1):
        print(f"[{i}/{len(contracts)}] Benchmarking: {contract.name}...", end=" ", flush=True)
        result = benchmark_contract(contract)
        results.append(result)

        if result.success:
            print(f"{result.build_time_seconds:.2f}s, {result.peak_memory_mb:.1f}MB, "
                  f"{result.node_count} nodes, {result.edge_count} edges")
        else:
            print(f"FAILED: {result.error[:50]}...")

    return results


def generate_summary(results: List[BenchmarkResult]) -> BenchmarkSummary:
    """Generate summary from benchmark results."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    build_times = [r.build_time_seconds for r in successful]
    memory_usage = [r.peak_memory_mb for r in successful]

    return BenchmarkSummary(
        timestamp=datetime.now().isoformat(),
        total_contracts=len(results),
        successful_builds=len(successful),
        failed_builds=len(failed),
        total_build_time_seconds=sum(build_times) if build_times else 0,
        average_build_time_seconds=sum(build_times) / len(build_times) if build_times else 0,
        max_build_time_seconds=max(build_times) if build_times else 0,
        min_build_time_seconds=min(build_times) if build_times else 0,
        total_peak_memory_mb=sum(memory_usage) if memory_usage else 0,
        average_peak_memory_mb=sum(memory_usage) / len(memory_usage) if memory_usage else 0,
        max_peak_memory_mb=max(memory_usage) if memory_usage else 0,
        total_nodes=sum(r.node_count for r in successful),
        total_edges=sum(r.edge_count for r in successful),
        results=[asdict(r) for r in results]
    )


def print_summary(summary: BenchmarkSummary):
    """Print benchmark summary."""
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Timestamp: {summary.timestamp}")
    print(f"Total contracts: {summary.total_contracts}")
    print(f"Successful builds: {summary.successful_builds}")
    print(f"Failed builds: {summary.failed_builds}")
    print()
    print("Build Time:")
    print(f"  Total: {summary.total_build_time_seconds:.2f}s")
    print(f"  Average: {summary.average_build_time_seconds:.2f}s")
    print(f"  Min: {summary.min_build_time_seconds:.2f}s")
    print(f"  Max: {summary.max_build_time_seconds:.2f}s")
    print()
    print("Memory Usage:")
    print(f"  Average peak: {summary.average_peak_memory_mb:.1f}MB")
    print(f"  Max peak: {summary.max_peak_memory_mb:.1f}MB")
    print()
    print("Graph Size:")
    print(f"  Total nodes: {summary.total_nodes}")
    print(f"  Total edges: {summary.total_edges}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Benchmark VKG build performance')
    parser.add_argument('--contracts-dir', type=Path,
                        default=ROOT / 'tests' / 'contracts',
                        help='Directory containing Solidity contracts')
    parser.add_argument('--pattern', default='*.sol',
                        help='Glob pattern for contract files')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'benchmarks' / 'baseline.json',
                        help='Output JSON file for results')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of contracts to benchmark')
    parser.add_argument('--single', type=Path, default=None,
                        help='Benchmark a single contract')

    args = parser.parse_args()

    if args.single:
        print(f"Benchmarking single contract: {args.single}")
        results = [benchmark_contract(args.single)]
    else:
        print(f"Benchmarking contracts in: {args.contracts_dir}")
        results = benchmark_all_contracts(args.contracts_dir, args.pattern)

        if args.limit:
            results = results[:args.limit]

    summary = generate_summary(results)
    print_summary(summary)

    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(asdict(summary), f, indent=2)
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()
