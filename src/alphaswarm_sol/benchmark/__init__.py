"""
Benchmark Module

Provides automated benchmarking infrastructure for VKG vulnerability detection.

Usage:
    uv run alphaswarm benchmark run --suite dvd
    uv run alphaswarm benchmark compare --baseline main
    uv run alphaswarm benchmark dashboard
"""

from alphaswarm_sol.benchmark.runner import BenchmarkRunner
from alphaswarm_sol.benchmark.suite import BenchmarkSuite, Challenge
from alphaswarm_sol.benchmark.results import BenchmarkResults

__all__ = ["BenchmarkRunner", "BenchmarkSuite", "Challenge", "BenchmarkResults"]
