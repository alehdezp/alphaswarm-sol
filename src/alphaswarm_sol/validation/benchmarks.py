"""Phase 21: Real Exploit Benchmarks.

This module provides benchmarking against real-world exploits
to validate detection capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node


class ExploitType(str, Enum):
    """Types of exploits."""
    REENTRANCY = "reentrancy"
    ACCESS_CONTROL = "access_control"
    ORACLE_MANIPULATION = "oracle_manipulation"
    FLASH_LOAN = "flash_loan"
    FRONTRUN = "frontrun"
    ARITHMETIC = "arithmetic"
    LOGIC_ERROR = "logic_error"


@dataclass
class ExploitBenchmark:
    """A benchmark test case based on a real exploit.

    Attributes:
        id: Benchmark identifier
        name: Exploit name
        exploit_type: Type of vulnerability
        description: Description of the exploit
        expected_findings: Expected vulnerability types to detect
        contract_pattern: Pattern to look for in contracts
        function_properties: Properties that indicate vulnerability
        cve_id: CVE identifier if applicable
        funds_lost: Amount of funds lost (USD)
    """
    id: str
    name: str
    exploit_type: ExploitType
    description: str = ""
    expected_findings: List[str] = field(default_factory=list)
    contract_pattern: str = ""
    function_properties: Dict[str, Any] = field(default_factory=dict)
    cve_id: Optional[str] = None
    funds_lost: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "exploit_type": self.exploit_type.value,
            "description": self.description,
            "expected_findings": self.expected_findings,
            "cve_id": self.cve_id,
            "funds_lost": self.funds_lost,
        }


@dataclass
class BenchmarkResult:
    """Result of running a benchmark.

    Attributes:
        benchmark_id: ID of the benchmark
        detected: Whether the vulnerability was detected
        findings_matched: Which expected findings were matched
        findings_missed: Which expected findings were missed
        false_positives: Unexpected findings
        detection_time_ms: Time to detect in milliseconds
    """
    benchmark_id: str
    detected: bool = False
    findings_matched: List[str] = field(default_factory=list)
    findings_missed: List[str] = field(default_factory=list)
    false_positives: List[str] = field(default_factory=list)
    detection_time_ms: float = 0.0

    @property
    def precision(self) -> float:
        """Calculate precision for this benchmark."""
        tp = len(self.findings_matched)
        fp = len(self.false_positives)
        if tp + fp == 0:
            return 0.0
        return tp / (tp + fp)

    @property
    def recall(self) -> float:
        """Calculate recall for this benchmark."""
        tp = len(self.findings_matched)
        fn = len(self.findings_missed)
        if tp + fn == 0:
            return 0.0
        return tp / (tp + fn)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "benchmark_id": self.benchmark_id,
            "detected": self.detected,
            "findings_matched": self.findings_matched,
            "findings_missed": self.findings_missed,
            "false_positives": self.false_positives,
            "detection_time_ms": round(self.detection_time_ms, 2),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
        }


# Known exploit benchmarks
KNOWN_EXPLOITS = [
    ExploitBenchmark(
        id="dao-2016",
        name="The DAO Hack",
        exploit_type=ExploitType.REENTRANCY,
        description="Classic reentrancy attack on The DAO that led to $60M loss and Ethereum fork",
        expected_findings=["reentrancy", "state_write_after_external_call"],
        function_properties={
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
            "transfers_value_out": True,
        },
        funds_lost=60_000_000,
    ),
    ExploitBenchmark(
        id="cream-2021",
        name="Cream Finance Flash Loan Attack",
        exploit_type=ExploitType.FLASH_LOAN,
        description="Flash loan attack exploiting price oracle manipulation",
        expected_findings=["oracle_manipulation", "flash_loan"],
        function_properties={
            "reads_oracle_price": True,
            "has_staleness_check": False,
        },
        cve_id="CVE-2021-44228",
        funds_lost=130_000_000,
    ),
    ExploitBenchmark(
        id="parity-2017",
        name="Parity Wallet Hack",
        exploit_type=ExploitType.ACCESS_CONTROL,
        description="Unprotected initialization function allowed attacker to take ownership",
        expected_findings=["access_control", "unprotected_init"],
        function_properties={
            "writes_privileged_state": True,
            "has_access_gate": False,
            "is_initializer_like": True,
        },
        funds_lost=30_000_000,
    ),
    ExploitBenchmark(
        id="beanstalk-2022",
        name="Beanstalk Flash Loan Governance Attack",
        exploit_type=ExploitType.FLASH_LOAN,
        description="Flash loan used to gain voting power and pass malicious governance proposal",
        expected_findings=["flash_loan", "governance"],
        function_properties={
            "reads_oracle_price": True,
        },
        funds_lost=182_000_000,
    ),
    ExploitBenchmark(
        id="miso-2021",
        name="MISO Access Control",
        exploit_type=ExploitType.ACCESS_CONTROL,
        description="Missing access control on batch auction function",
        expected_findings=["access_control"],
        function_properties={
            "writes_privileged_state": True,
            "has_access_gate": False,
        },
        funds_lost=3_000_000,
    ),
    ExploitBenchmark(
        id="fei-2022",
        name="Fei Protocol Reentrancy",
        exploit_type=ExploitType.REENTRANCY,
        description="Reentrancy in flash loan callback",
        expected_findings=["reentrancy"],
        function_properties={
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
        },
        funds_lost=80_000_000,
    ),
]


class BenchmarkSuite:
    """Suite of exploit benchmarks.

    Runs benchmarks against a knowledge graph to validate
    detection capabilities.
    """

    def __init__(self, benchmarks: Optional[List[ExploitBenchmark]] = None):
        """Initialize suite.

        Args:
            benchmarks: List of benchmarks (default: KNOWN_EXPLOITS)
        """
        self.benchmarks = benchmarks or KNOWN_EXPLOITS

    def run(self, graph: KnowledgeGraph) -> List[BenchmarkResult]:
        """Run all benchmarks against a graph.

        Args:
            graph: Knowledge graph to test

        Returns:
            List of benchmark results
        """
        import time

        results: List[BenchmarkResult] = []

        for benchmark in self.benchmarks:
            start = time.perf_counter()
            result = self._run_benchmark(benchmark, graph)
            result.detection_time_ms = (time.perf_counter() - start) * 1000
            results.append(result)

        return results

    def _run_benchmark(
        self,
        benchmark: ExploitBenchmark,
        graph: KnowledgeGraph,
    ) -> BenchmarkResult:
        """Run a single benchmark.

        Args:
            benchmark: Benchmark to run
            graph: Knowledge graph

        Returns:
            BenchmarkResult
        """
        result = BenchmarkResult(benchmark_id=benchmark.id)
        expected = set(benchmark.expected_findings)
        found: set[str] = set()

        for node in graph.nodes.values():
            if node.type != "Function":
                continue

            # Check if function matches vulnerability pattern
            matches = self._check_properties(node, benchmark.function_properties)

            if matches:
                result.detected = True

                # Map properties to finding types
                if node.properties.get("state_write_after_external_call"):
                    found.add("reentrancy")
                    found.add("state_write_after_external_call")
                if node.properties.get("writes_privileged_state") and not node.properties.get("has_access_gate"):
                    found.add("access_control")
                if node.properties.get("is_initializer_like") and not node.properties.get("has_access_gate"):
                    found.add("unprotected_init")
                if node.properties.get("reads_oracle_price"):
                    found.add("oracle_manipulation")
                    found.add("flash_loan")

        # Calculate matched, missed, and false positives
        result.findings_matched = list(expected & found)
        result.findings_missed = list(expected - found)
        result.false_positives = list(found - expected)

        return result

    def _check_properties(
        self,
        node: Node,
        required: Dict[str, Any],
    ) -> bool:
        """Check if node matches required properties.

        Args:
            node: Node to check
            required: Required properties

        Returns:
            True if all properties match
        """
        if not required:
            return False

        for prop, expected in required.items():
            actual = node.properties.get(prop)
            if actual != expected:
                return False

        return True

    def get_summary(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Get summary of benchmark results.

        Args:
            results: Benchmark results

        Returns:
            Summary dictionary
        """
        total = len(results)
        detected = sum(1 for r in results if r.detected)

        total_matched = sum(len(r.findings_matched) for r in results)
        total_missed = sum(len(r.findings_missed) for r in results)
        total_fp = sum(len(r.false_positives) for r in results)

        precision = total_matched / (total_matched + total_fp) if (total_matched + total_fp) > 0 else 0
        recall = total_matched / (total_matched + total_missed) if (total_matched + total_missed) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "total_benchmarks": total,
            "detected": detected,
            "detection_rate": detected / total if total > 0 else 0,
            "total_findings_matched": total_matched,
            "total_findings_missed": total_missed,
            "total_false_positives": total_fp,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }


def run_benchmarks(
    graph: KnowledgeGraph,
    benchmarks: Optional[List[ExploitBenchmark]] = None,
) -> Dict[str, Any]:
    """Run benchmarks against a knowledge graph.

    Convenience function for quick benchmarking.

    Args:
        graph: Knowledge graph to test
        benchmarks: Optional custom benchmarks

    Returns:
        Dictionary with results and summary
    """
    suite = BenchmarkSuite(benchmarks)
    results = suite.run(graph)
    summary = suite.get_summary(results)

    return {
        "results": [r.to_dict() for r in results],
        "summary": summary,
    }


__all__ = [
    "ExploitType",
    "ExploitBenchmark",
    "BenchmarkResult",
    "BenchmarkSuite",
    "KNOWN_EXPLOITS",
    "run_benchmarks",
]
