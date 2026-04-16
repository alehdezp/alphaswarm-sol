"""
Benchmark Runner

Executes benchmark suites and collects results.
"""

from __future__ import annotations

import time
import structlog
from pathlib import Path
from typing import Any

from alphaswarm_sol.benchmark.suite import BenchmarkSuite, Challenge, load_suite
from alphaswarm_sol.benchmark.results import BenchmarkResults, ChallengeResult
from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.kg.store import GraphStore
from alphaswarm_sol.queries.executor import QueryExecutor
from alphaswarm_sol.queries.intent import parse_intent
from alphaswarm_sol.queries.planner import QueryPlanner


logger = structlog.get_logger()


class BenchmarkRunner:
    """Runs benchmark suites against VKG."""

    def __init__(
        self,
        project_root: Path | None = None,
        pattern_dir: Path | None = None,
        verbose: bool = False,
    ):
        self.project_root = project_root or Path.cwd()
        self.pattern_dir = pattern_dir
        self.verbose = verbose
        self._executor = QueryExecutor(pattern_dir=pattern_dir)

    def run_suite(self, suite_name: str) -> BenchmarkResults:
        """Run a complete benchmark suite."""
        suite = load_suite(suite_name)
        results = BenchmarkResults(
            suite_name=suite.name,
            suite_version=suite.version,
        )

        try:
            from importlib.metadata import version
            results.vkg_version = version("alphaswarm")
        except Exception:
            results.vkg_version = "0.0.0-dev"

        start_time = time.time()

        for challenge in suite.challenges:
            logger.info("running_challenge", challenge=challenge.id)
            result = self._run_challenge(challenge)
            results.add_result(result)

            if self.verbose:
                status_icon = "✓" if result.is_detected else "✗"
                print(f"  {status_icon} {challenge.id}: {result.status}")

        results.total_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "benchmark_complete",
            suite=suite_name,
            detection_rate=results.detection_rate,
            detected=results.detected_count,
            total=results.total_challenges,
        )

        return results

    def _run_challenge(self, challenge: Challenge) -> ChallengeResult:
        """Run a single challenge."""
        start_time = time.time()

        # Handle non-applicable challenges
        if challenge.status == "not-applicable":
            return ChallengeResult(
                challenge_id=challenge.id,
                status="skipped",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            # Build graph for challenge
            source_path = self.project_root / challenge.source_path
            if not source_path.exists():
                return ChallengeResult(
                    challenge_id=challenge.id,
                    status="error",
                    error_message=f"Source path not found: {source_path}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            builder = VKGBuilder(source_path)
            graph = builder.build(source_path)

            # Run pattern queries
            patterns_matched = []
            patterns_missed = []

            for expected in challenge.expected_detections:
                pattern_query = f"pattern:{expected.pattern}"
                try:
                    intent = parse_intent(pattern_query, pattern_dir=self.pattern_dir)
                    plan = QueryPlanner().build(intent)
                    result = self._executor.execute(graph, plan)

                    # Check if pattern matched
                    matches = result.get("matches", [])
                    if matches:
                        patterns_matched.append(expected.pattern)
                    else:
                        patterns_missed.append(expected.pattern)
                except Exception as e:
                    logger.warning(
                        "pattern_query_failed",
                        pattern=expected.pattern,
                        error=str(e),
                    )
                    patterns_missed.append(expected.pattern)

            # Determine overall status
            if patterns_matched:
                status = "detected"
            elif challenge.status == "not-detected":
                status = "not-detected"
            else:
                status = "not-detected"

            return ChallengeResult(
                challenge_id=challenge.id,
                status=status,
                expected_detections=len(challenge.expected_detections),
                actual_detections=len(patterns_matched),
                patterns_matched=patterns_matched,
                patterns_missed=patterns_missed,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(
                "challenge_failed",
                challenge=challenge.id,
                error=str(e),
            )
            return ChallengeResult(
                challenge_id=challenge.id,
                status="error",
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def run_challenge(self, suite_name: str, challenge_id: str) -> ChallengeResult:
        """Run a single challenge by ID."""
        suite = load_suite(suite_name)
        challenge = suite.get_challenge(challenge_id)

        if challenge is None:
            return ChallengeResult(
                challenge_id=challenge_id,
                status="error",
                error_message=f"Challenge not found: {challenge_id}",
            )

        return self._run_challenge(challenge)


def run_benchmark(
    suite_name: str,
    project_root: Path | None = None,
    pattern_dir: Path | None = None,
    output_path: Path | None = None,
    verbose: bool = False,
) -> BenchmarkResults:
    """Convenience function to run a benchmark suite."""
    runner = BenchmarkRunner(
        project_root=project_root,
        pattern_dir=pattern_dir,
        verbose=verbose,
    )
    results = runner.run_suite(suite_name)

    if output_path:
        results.save(output_path)

    return results
