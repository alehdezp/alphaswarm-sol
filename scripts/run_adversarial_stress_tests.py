#!/usr/bin/env python3
"""Adversarial and Mutation Stress Test Runner.

Stress tests detection pipeline against adversarial and mutation-heavy
corpora to validate robustness before GA release.

Usage:
    # Run stress tests with defaults
    python scripts/run_adversarial_stress_tests.py

    # Generate counterfactuals first then run
    python scripts/run_adversarial_stress_tests.py --generate-counterfactuals

    # Specify output path
    python scripts/run_adversarial_stress_tests.py --output .vrs/testing/reports/stress.json

    # Limit contracts per segment
    python scripts/run_adversarial_stress_tests.py --max-contracts 10

Segments tested:
- adversarial: Hand-crafted near-miss contracts and counterfactuals
- mutations: Auto-generated semantic-preserving variants
- safe: Hard-negative contracts that should NOT trigger findings

Output:
- JSON report with precision/recall per segment
- Gaps logged to .vrs/testing/gaps/ for failures
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SegmentResult:
    """Results for a single corpus segment."""

    segment: str
    contracts_tested: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    failure_modes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "segment": self.segment,
            "contracts_tested": self.contracts_tested,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "failure_modes": self.failure_modes,
        }


@dataclass
class StressTestReport:
    """Complete stress test report."""

    run_id: str
    timestamp: str
    segments: Dict[str, SegmentResult]
    overall_precision: float
    overall_recall: float
    overall_f1: float
    ga_recommendation: str
    gaps_created: List[str]
    duration_seconds: float
    config: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "segments": {k: v.to_dict() for k, v in self.segments.items()},
            "overall": {
                "precision": round(self.overall_precision, 4),
                "recall": round(self.overall_recall, 4),
                "f1_score": round(self.overall_f1, 4),
            },
            "ga_recommendation": self.ga_recommendation,
            "gaps_created": self.gaps_created,
            "duration_seconds": round(self.duration_seconds, 2),
            "config": self.config,
        }


class AdversarialStressTestRunner:
    """Runner for adversarial and mutation stress tests."""

    # GA thresholds
    PRECISION_THRESHOLD = 0.85
    RECALL_THRESHOLD = 0.85

    def __init__(
        self,
        corpus_root: Path,
        output_path: Path,
        max_contracts: int = 50,
        generate_counterfactuals: bool = False,
    ):
        """Initialize stress test runner.

        Args:
            corpus_root: Root path to corpus contracts
            output_path: Path for JSON report output
            max_contracts: Maximum contracts per segment
            generate_counterfactuals: Whether to generate new counterfactuals
        """
        self.corpus_root = corpus_root
        self.output_path = output_path
        self.max_contracts = max_contracts
        self.generate_counterfactuals = generate_counterfactuals
        self.gaps_created: List[str] = []
        self._graph_cache_dir = Path(".vrs/testing/graphs/stress")

    def run(self) -> StressTestReport:
        """Execute full stress test suite.

        Returns:
            StressTestReport with all segment results
        """
        start_time = time.time()
        run_id = f"stress-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        print(f"Starting adversarial stress tests (run: {run_id})")
        print(f"Corpus root: {self.corpus_root}")
        print(f"Max contracts per segment: {self.max_contracts}")
        print()

        # Optionally generate counterfactuals
        if self.generate_counterfactuals:
            self._generate_counterfactuals()

        # Run tests for each segment
        segments: Dict[str, SegmentResult] = {}

        # Adversarial segment
        print("Testing adversarial segment...")
        adversarial_result = self._test_segment("adversarial")
        segments["adversarial"] = adversarial_result
        print(f"  Precision: {adversarial_result.precision:.2%}")
        print(f"  Recall: {adversarial_result.recall:.2%}")
        print()

        # Mutations segment (if populated)
        print("Testing mutations segment...")
        mutations_result = self._test_segment("mutations")
        segments["mutations"] = mutations_result
        print(f"  Precision: {mutations_result.precision:.2%}")
        print(f"  Recall: {mutations_result.recall:.2%}")
        print()

        # Safe segment (FP testing)
        print("Testing safe segment (false positive check)...")
        safe_result = self._test_safe_segment()
        segments["safe"] = safe_result
        print(f"  False Positives: {safe_result.false_positives}")
        print(f"  Precision: {safe_result.precision:.2%}")
        print()

        # Compute overall metrics
        total_tp = sum(s.true_positives for s in segments.values())
        total_fp = sum(s.false_positives for s in segments.values())
        total_fn = sum(s.false_negatives for s in segments.values())

        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
        overall_f1 = (
            2 * overall_precision * overall_recall / (overall_precision + overall_recall)
            if (overall_precision + overall_recall) > 0
            else 0.0
        )

        # Determine GA recommendation
        ga_recommendation = self._determine_ga_recommendation(
            segments, overall_precision, overall_recall
        )

        duration = time.time() - start_time

        report = StressTestReport(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            segments=segments,
            overall_precision=overall_precision,
            overall_recall=overall_recall,
            overall_f1=overall_f1,
            ga_recommendation=ga_recommendation,
            gaps_created=self.gaps_created,
            duration_seconds=duration,
            config={
                "max_contracts": self.max_contracts,
                "generate_counterfactuals": self.generate_counterfactuals,
                "corpus_root": str(self.corpus_root),
            },
        )

        # Write report
        self._write_report(report)

        return report

    def _generate_counterfactuals(self) -> None:
        """Generate counterfactual contracts from vulnerable corpus."""
        print("Generating counterfactuals from corpus...")
        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/counterfactual_factory.py",
                    "--from-corpus",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                print(f"  Warning: counterfactual generation failed: {result.stderr[:200]}")
            else:
                print("  Counterfactuals generated successfully")
        except Exception as e:
            print(f"  Warning: counterfactual generation error: {e}")
        print()

    def _test_segment(self, segment: str) -> SegmentResult:
        """Test a single corpus segment.

        Args:
            segment: Segment name (adversarial, mutations)

        Returns:
            SegmentResult with metrics
        """
        segment_path = self.corpus_root / segment
        if not segment_path.exists():
            return SegmentResult(
                segment=segment,
                contracts_tested=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                precision=1.0,
                recall=1.0,
                f1_score=1.0,
            )

        # Collect all Solidity files
        sol_files = list(segment_path.rglob("*.sol"))[:self.max_contracts]

        if not sol_files:
            return SegmentResult(
                segment=segment,
                contracts_tested=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                precision=1.0,
                recall=1.0,
                f1_score=1.0,
            )

        # Track metrics
        total_tp = 0
        total_fp = 0
        total_fn = 0
        failure_modes: List[Dict[str, Any]] = []

        for sol_file in sol_files:
            result = self._test_contract(sol_file, segment)
            total_tp += result["tp"]
            total_fp += result["fp"]
            total_fn += result["fn"]

            if result.get("failure_mode"):
                failure_modes.append(result["failure_mode"])

        # Compute segment metrics
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        # Create gaps for failures
        if precision < self.PRECISION_THRESHOLD or recall < self.RECALL_THRESHOLD:
            gap_id = self._create_gap(
                segment=segment,
                precision=precision,
                recall=recall,
                failure_modes=failure_modes,
            )
            if gap_id:
                self.gaps_created.append(gap_id)

        return SegmentResult(
            segment=segment,
            contracts_tested=len(sol_files),
            true_positives=total_tp,
            false_positives=total_fp,
            false_negatives=total_fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            failure_modes=failure_modes[:10],  # Limit stored failure modes
        )

    def _test_safe_segment(self) -> SegmentResult:
        """Test safe contracts segment (hard negatives).

        Safe contracts should produce NO findings. Any findings are false positives.

        Returns:
            SegmentResult for safe segment
        """
        segment_path = self.corpus_root / "safe"
        if not segment_path.exists():
            return SegmentResult(
                segment="safe",
                contracts_tested=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                precision=1.0,
                recall=1.0,
                f1_score=1.0,
            )

        # Collect all Solidity files
        sol_files = list(segment_path.rglob("*.sol"))[:self.max_contracts]

        if not sol_files:
            return SegmentResult(
                segment="safe",
                contracts_tested=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                precision=1.0,
                recall=1.0,
                f1_score=1.0,
            )

        # For safe contracts: any finding is a false positive
        total_fp = 0
        failure_modes: List[Dict[str, Any]] = []

        for sol_file in sol_files:
            findings = self._run_detection(sol_file)
            if findings:
                total_fp += len(findings)
                failure_modes.append({
                    "contract": str(sol_file.name),
                    "type": "false_positive_on_safe",
                    "findings": [f.get("pattern_id", "unknown") for f in findings[:3]],
                })

        # For safe segment: precision = (tested - FP) / tested, recall = 1.0 (no vulns to find)
        contracts_tested = len(sol_files)
        # Treat safe contracts as having 0 expected vulnerabilities
        # TP = 0 (no vulnerabilities to correctly identify)
        # FP = any findings on safe contracts
        # FN = 0 (nothing to miss)
        precision = 1.0 if total_fp == 0 else 0.0
        recall = 1.0  # Vacuously true - no vulnerabilities to miss

        # Create gap if FPs detected
        if total_fp > 0:
            gap_id = self._create_gap(
                segment="safe",
                precision=precision,
                recall=recall,
                failure_modes=failure_modes,
                is_fp_issue=True,
            )
            if gap_id:
                self.gaps_created.append(gap_id)

        return SegmentResult(
            segment="safe",
            contracts_tested=contracts_tested,
            true_positives=0,
            false_positives=total_fp,
            false_negatives=0,
            precision=precision,
            recall=recall,
            f1_score=precision,  # For safe segment, F1 == precision
            failure_modes=failure_modes[:10],
        )

    def _test_contract(self, sol_file: Path, segment: str) -> Dict[str, Any]:
        """Test a single contract.

        Args:
            sol_file: Path to Solidity file
            segment: Segment name for context

        Returns:
            Dict with tp, fp, fn counts and optional failure_mode
        """
        # Get expected findings based on segment and file metadata
        expected = self._get_expected_findings(sol_file, segment)
        actual = self._run_detection(sol_file)

        # Compare findings
        tp = 0
        fp = 0
        fn = 0
        failure_mode = None

        # Match expected vs actual
        actual_patterns = {f.get("pattern_id", "") for f in actual}
        expected_patterns = {e.get("pattern") for e in expected}

        tp = len(actual_patterns & expected_patterns)
        fp = len(actual_patterns - expected_patterns)
        fn = len(expected_patterns - actual_patterns)

        # Record failure modes
        if fp > 0 or fn > 0:
            failure_mode = {
                "contract": str(sol_file.name),
                "segment": segment,
                "expected": list(expected_patterns),
                "actual": list(actual_patterns),
                "missed": list(expected_patterns - actual_patterns),
                "spurious": list(actual_patterns - expected_patterns),
            }

        return {"tp": tp, "fp": fp, "fn": fn, "failure_mode": failure_mode}

    def _get_expected_findings(self, sol_file: Path, segment: str) -> List[Dict[str, Any]]:
        """Get expected findings for a contract.

        For adversarial/counterfactual: check metadata files
        For mutations: inherit from base contract

        Args:
            sol_file: Path to Solidity file
            segment: Segment name

        Returns:
            List of expected findings with pattern IDs
        """
        expected: List[Dict[str, Any]] = []

        # Check for metadata file
        metadata_dir = sol_file.parent / "metadata"
        metadata_file = metadata_dir / f"{sol_file.stem}.yaml"

        if metadata_file.exists():
            try:
                import yaml
                metadata = yaml.safe_load(metadata_file.read_text())
                status = metadata.get("expected_vulnerability_status", "unknown")
                if status == "vulnerable":
                    # Extract expected patterns from metadata
                    cf_type = metadata.get("counterfactual_type", "")
                    if cf_type:
                        # Map counterfactual type to expected patterns
                        pattern_map = {
                            "guard_inversion": ["access-control-weak"],
                            "cei_order_swap": ["reentrancy-classic"],
                            "grace_period": ["oracle-staleness"],
                            "helper_depth": ["access-control-hidden"],
                            "chain_condition": ["chain-specific-bypass"],
                        }
                        patterns = pattern_map.get(cf_type, [])
                        for p in patterns:
                            expected.append({"pattern": p})
            except Exception:
                pass

        # If no metadata, infer from file naming conventions
        if not expected:
            stem_lower = sol_file.stem.lower()

            # Common vulnerability indicators in filenames
            vuln_indicators = {
                "reentrancy": "reentrancy-classic",
                "reentrance": "reentrancy-classic",
                "vulnerable": "unknown-vulnerability",
                "unsafe": "unsafe-operation",
                "oracle": "oracle-manipulation",
                "flashloan": "flash-loan-attack",
                "access": "access-control-weak",
            }

            for indicator, pattern in vuln_indicators.items():
                if indicator in stem_lower and "safe" not in stem_lower:
                    expected.append({"pattern": pattern})
                    break

        return expected

    def _run_detection(self, sol_file: Path) -> List[Dict[str, Any]]:
        """Run detection pipeline on a contract.

        Args:
            sol_file: Path to Solidity file

        Returns:
            List of findings from detection pipeline
        """
        try:
            # Build graph
            self._graph_cache_dir.mkdir(parents=True, exist_ok=True)
            suffix = hashlib.sha1(str(sol_file).encode("utf-8")).hexdigest()[:8]
            output_dir = self._graph_cache_dir / f"{sol_file.stem}-{suffix}"

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "alphaswarm",
                    "build-kg",
                    str(sol_file),
                    "--out",
                    str(output_dir),
                    "--format",
                    "toon",
                    "--overwrite",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return []

            # Find graph file
            graph_path = output_dir / "graph.toon"
            if not graph_path.exists():
                graph_path = output_dir / "graph.json"
            if not graph_path.exists():
                return []

            # Run pattern detection
            query_result = subprocess.run(
                [
                    "uv",
                    "run",
                    "alphaswarm",
                    "query",
                    "--graph",
                    str(graph_path),
                    "pattern:*",
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if query_result.returncode != 0:
                return []

            # Parse findings
            try:
                findings = json.loads(query_result.stdout)
                if isinstance(findings, dict):
                    findings = findings.get("findings", [])
                return findings if isinstance(findings, list) else []
            except json.JSONDecodeError:
                return []

        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []

    def _create_gap(
        self,
        segment: str,
        precision: float,
        recall: float,
        failure_modes: List[Dict[str, Any]],
        is_fp_issue: bool = False,
    ) -> Optional[str]:
        """Create a gap entry for segment failures.

        Args:
            segment: Segment name
            precision: Segment precision
            recall: Segment recall
            failure_modes: List of failure details
            is_fp_issue: True if this is primarily a FP issue

        Returns:
            Gap ID if created, None otherwise
        """
        try:
            from alphaswarm_sol.testing.gaps import GapTracker, GapCategory, GapSeverity

            tracker = GapTracker()

            if is_fp_issue:
                category = GapCategory.FALSE_POSITIVE
                title = f"High false positive rate in {segment} segment"
                description = (
                    f"Detection pipeline produced {len(failure_modes)} false positives "
                    f"on safe contracts in the {segment} segment."
                )
                root_cause = "Pattern matching too aggressive on safe variants"
            elif recall < self.RECALL_THRESHOLD:
                category = GapCategory.DETECTION
                title = f"Low recall in {segment} segment"
                description = (
                    f"Recall {recall:.2%} below threshold {self.RECALL_THRESHOLD:.0%} "
                    f"for {segment} segment."
                )
                root_cause = "Patterns miss adversarial/mutated vulnerability variants"
            else:
                category = GapCategory.FALSE_POSITIVE
                title = f"Low precision in {segment} segment"
                description = (
                    f"Precision {precision:.2%} below threshold {self.PRECISION_THRESHOLD:.0%} "
                    f"for {segment} segment."
                )
                root_cause = "Patterns trigger on non-vulnerable code"

            severity = GapSeverity.HIGH if segment == "adversarial" else GapSeverity.MEDIUM

            gap = tracker.create_gap(
                title=title,
                category=category,
                severity=severity,
                description=description,
                root_cause=root_cause,
                affected_component=f"pattern_engine/{segment}",
                discovered_by="adversarial_stress_tests",
            )

            return gap.gap_id

        except ImportError:
            print("  Warning: Could not create gap (module not found)")
            return None
        except Exception as e:
            print(f"  Warning: Could not create gap: {e}")
            return None

    def _determine_ga_recommendation(
        self,
        segments: Dict[str, SegmentResult],
        overall_precision: float,
        overall_recall: float,
    ) -> str:
        """Determine GA gate recommendation based on results.

        Args:
            segments: Results by segment
            overall_precision: Overall precision
            overall_recall: Overall recall

        Returns:
            "pass", "conditional", or "fail" with explanation
        """
        issues = []

        # Check overall thresholds
        if overall_precision < self.PRECISION_THRESHOLD:
            issues.append(f"overall precision {overall_precision:.2%} < {self.PRECISION_THRESHOLD:.0%}")
        if overall_recall < self.RECALL_THRESHOLD:
            issues.append(f"overall recall {overall_recall:.2%} < {self.RECALL_THRESHOLD:.0%}")

        # Check segment-specific issues
        for name, result in segments.items():
            if name == "safe" and result.false_positives > 0:
                issues.append(f"{result.false_positives} FPs on safe contracts")
            elif name == "adversarial" and result.recall < 0.80:
                issues.append(f"adversarial recall {result.recall:.2%} too low")

        if not issues:
            return "pass"
        elif len(issues) <= 2 and overall_precision >= 0.80 and overall_recall >= 0.80:
            return f"conditional: {'; '.join(issues)}"
        else:
            return f"fail: {'; '.join(issues)}"

    def _write_report(self, report: StressTestReport) -> None:
        """Write report to JSON file.

        Args:
            report: StressTestReport to write
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(
            json.dumps(report.to_dict(), indent=2),
            encoding="utf-8",
        )
        print(f"Report written to: {self.output_path}")


def main() -> int:
    """Run adversarial stress tests CLI."""
    parser = argparse.ArgumentParser(
        description="Run adversarial and mutation stress tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--generate-counterfactuals",
        action="store_true",
        help="Generate counterfactuals before testing",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".vrs/testing/reports/adversarial-mutation.json"),
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--max-contracts",
        type=int,
        default=50,
        help="Maximum contracts to test per segment",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path(".vrs/corpus/contracts"),
        help="Root path to corpus contracts",
    )

    args = parser.parse_args()

    runner = AdversarialStressTestRunner(
        corpus_root=args.corpus_root,
        output_path=args.output,
        max_contracts=args.max_contracts,
        generate_counterfactuals=args.generate_counterfactuals,
    )

    report = runner.run()

    # Print summary
    print()
    print("=" * 60)
    print("STRESS TEST SUMMARY")
    print("=" * 60)
    print(f"Overall Precision: {report.overall_precision:.2%}")
    print(f"Overall Recall:    {report.overall_recall:.2%}")
    print(f"Overall F1:        {report.overall_f1:.2%}")
    print()
    print(f"GA Recommendation: {report.ga_recommendation.upper()}")
    print()

    if report.gaps_created:
        print(f"Gaps created: {', '.join(report.gaps_created)}")
    else:
        print("No gaps created")

    print(f"Duration: {report.duration_seconds:.1f}s")
    print("=" * 60)

    # Exit code based on recommendation
    if report.ga_recommendation == "pass":
        return 0
    elif report.ga_recommendation.startswith("conditional"):
        return 0  # Conditional is still acceptable
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
