#!/usr/bin/env python3
"""
Precision Dashboard Generator

Generates a comprehensive precision/recall dashboard for all VKG patterns.
Part of Phase 4: Testing Infrastructure

Usage:
    uv run python scripts/generate_precision_dashboard.py
    uv run python scripts/generate_precision_dashboard.py --output docs/precision-dashboard.md
    uv run python scripts/generate_precision_dashboard.py --pattern-file patterns/core/reentrancy-basic.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.pattern_test_framework import (
    PatternStatus,
    PatternTestResult,
    PatternTestRunner,
    PatternTestSpec,
    generate_precision_report,
)
from tests.graph_cache import load_graph

# Default test specifications for core patterns
DEFAULT_TEST_SPECS: List[PatternTestSpec] = [
    # Reentrancy patterns
    PatternTestSpec(
        pattern_id="reentrancy-basic",
        must_match=["ReentrancyClassic.withdraw"],
        must_not_match=["ReentrancyCEI.withdrawSafe", "safe/ReentrancySafe.withdrawCEI"],
        description="Basic reentrancy via state update after external call",
    ),
    PatternTestSpec(
        pattern_id="state-write-after-call",
        must_match=["ReentrancyClassic.withdraw"],
        must_not_match=["ReentrancyCEI.withdrawSafe"],
        description="State modification after external call",
    ),
    # Access Control patterns
    PatternTestSpec(
        pattern_id="weak-access-control",
        must_match=["NoAccessGate.setOwner", "NoAccessGate.withdrawAll"],
        must_not_match=["safe/AccessControlSafe.setOwner"],
        description="Privileged functions without access control",
    ),
    PatternTestSpec(
        pattern_id="delegatecall-no-gate",
        must_match=["DelegatecallNoAccessGate.execute"],
        must_not_match=["safe/DelegatecallSafe.execute"],
        description="Delegatecall without access control",
    ),
    PatternTestSpec(
        pattern_id="initializer-no-gate",
        must_match=["UninitializedOwner.initialize"],
        must_not_match=["InitializerGuarded.initialize"],
        description="Initializer callable by anyone",
    ),
    # DoS patterns
    PatternTestSpec(
        pattern_id="dos-unbounded-loop",
        must_match=["LoopDos.distribute"],
        must_not_match=["safe/DosSafe.distributeRewardsBatched"],
        description="Unbounded loop vulnerable to DoS",
    ),
    PatternTestSpec(
        pattern_id="dos-external-call-in-loop",
        must_match=["LoopDos.distribute"],
        must_not_match=["safe/DosSafe.claimPayment"],
        description="External calls inside loop",
    ),
    # MEV patterns
    PatternTestSpec(
        pattern_id="mev-missing-slippage-parameter",
        must_match=["SwapNoSlippage.swap"],
        must_not_match=["SwapWithSlippage.swap", "safe/MevSafe.swapWithSlippage"],
        description="Swap without slippage protection",
    ),
    PatternTestSpec(
        pattern_id="mev-missing-deadline-parameter",
        must_match=["RouterSwapNoChecks.swap"],
        must_not_match=["safe/MevSafe.swapWithDeadline"],
        description="Swap without deadline parameter",
    ),
    # Oracle patterns
    PatternTestSpec(
        pattern_id="oracle-freshness-missing-staleness",
        must_match=["OracleNoStaleness.getPrice"],
        must_not_match=["OracleWithStaleness.getPrice", "safe/OracleSafe.getPrice"],
        description="Oracle data used without staleness check",
    ),
    # Token patterns
    PatternTestSpec(
        pattern_id="token-unchecked-return",
        must_match=["Erc20UncheckedTransfer.unsafeTransfer"],
        must_not_match=["Erc20CheckedTransfer.safeTransfer", "safe/TokenSafe.safeTransfer"],
        description="ERC20 transfer return value not checked",
    ),
    # Crypto patterns
    PatternTestSpec(
        pattern_id="crypto-signature-replay",
        must_match=["SignatureReplayReusable.execute"],
        must_not_match=["SignatureWithNonce.execute", "safe/CryptoSafe.permitWithFullValidation"],
        description="Signature replay attack possible",
    ),
    PatternTestSpec(
        pattern_id="crypto-zero-address-check",
        must_match=["SignatureZeroAddressVuln.verify"],
        must_not_match=["safe/CryptoSafe.verifySignature"],
        description="No zero address check after ecrecover",
    ),
]


class PrecisionDashboardGenerator:
    """Generates precision/recall dashboard for VKG patterns."""

    def __init__(
        self,
        patterns_dir: str = "patterns",
        contracts_dir: str = "tests/contracts",
    ):
        self.patterns_dir = Path(patterns_dir)
        self.contracts_dir = Path(contracts_dir)
        self.runner = PatternTestRunner(patterns_dir)

    def run_tests(
        self,
        specs: Optional[List[PatternTestSpec]] = None,
    ) -> List[PatternTestResult]:
        """Run pattern tests and return results."""
        if specs is None:
            specs = DEFAULT_TEST_SPECS

        results = []
        for spec in specs:
            try:
                result = self.runner.run_spec(spec)
                results.append(result)
            except Exception as e:
                # Create error result
                result = PatternTestResult(
                    pattern_id=spec.pattern_id,
                    spec=spec,
                    errors=[str(e)],
                )
                result.calculate_metrics()
                results.append(result)

        return results

    def generate_markdown(
        self,
        results: List[PatternTestResult],
        include_details: bool = True,
    ) -> str:
        """Generate markdown dashboard from results."""
        lines = [
            "# VKG Pattern Precision Dashboard",
            "",
            f"*Generated: {datetime.now().isoformat()}*",
            "",
            "## Summary",
            "",
        ]

        # Summary statistics
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        by_status = {
            "draft": sum(1 for r in results if r.status == PatternStatus.DRAFT),
            "ready": sum(1 for r in results if r.status == PatternStatus.READY),
            "excellent": sum(1 for r in results if r.status == PatternStatus.EXCELLENT),
        }

        lines.extend([
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Patterns Tested | {total} |",
            f"| Passed | {passed} ({passed/total*100:.1f}%) |" if total > 0 else "| Passed | 0 |",
            f"| Failed | {total - passed} |",
            f"| Draft Status | {by_status['draft']} |",
            f"| Ready Status | {by_status['ready']} |",
            f"| Excellent Status | {by_status['excellent']} |",
            "",
        ])

        # Aggregate metrics
        if results:
            avg_precision = sum(r.precision for r in results) / len(results)
            avg_recall = sum(r.recall for r in results) / len(results)
            avg_f1 = sum(r.f1_score for r in results) / len(results)
            avg_fp_rate = sum(r.fp_rate for r in results) / len(results)

            lines.extend([
                "### Aggregate Metrics",
                "",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Average Precision | {avg_precision:.1%} |",
                f"| Average Recall | {avg_recall:.1%} |",
                f"| Average F1 Score | {avg_f1:.3f} |",
                f"| Average FP Rate | {avg_fp_rate:.1%} |",
                "",
            ])

        # Pattern details table
        lines.extend([
            "## Pattern Results",
            "",
            "| Pattern ID | Status | Precision | Recall | F1 | FP Rate | Passed |",
            "|------------|--------|-----------|--------|-----|---------|--------|",
        ])

        for r in sorted(results, key=lambda x: x.pattern_id):
            status_badge = self._status_badge(r.status)
            passed_icon = "✅" if r.passed else "❌"
            lines.append(
                f"| {r.pattern_id} | {status_badge} | "
                f"{r.precision:.1%} | {r.recall:.1%} | {r.f1_score:.3f} | "
                f"{r.fp_rate:.1%} | {passed_icon} |"
            )

        lines.append("")

        # Detailed breakdown
        if include_details:
            lines.extend([
                "## Detailed Results",
                "",
            ])

            for r in sorted(results, key=lambda x: x.pattern_id):
                lines.extend([
                    f"### {r.pattern_id}",
                    "",
                    f"**Status:** {self._status_badge(r.status)}",
                    "",
                    f"| Metric | Value |",
                    f"|--------|-------|",
                    f"| Precision | {r.precision:.1%} |",
                    f"| Recall | {r.recall:.1%} |",
                    f"| F1 Score | {r.f1_score:.3f} |",
                    f"| FP Rate | {r.fp_rate:.1%} |",
                    f"| TP | {len(r.true_positives)} |",
                    f"| FN | {len(r.false_negatives)} |",
                    f"| TN | {len(r.true_negatives)} |",
                    f"| FP | {len(r.false_positives)} |",
                    "",
                ])

                if r.true_positives:
                    lines.append("**True Positives:**")
                    for tp in r.true_positives:
                        lines.append(f"- `{tp}`")
                    lines.append("")

                if r.false_negatives:
                    lines.append("**False Negatives (Missed):**")
                    for fn in r.false_negatives:
                        lines.append(f"- `{fn}`")
                    lines.append("")

                if r.false_positives:
                    lines.append("**False Positives (Over-matched):**")
                    for fp in r.false_positives:
                        lines.append(f"- `{fp}`")
                    lines.append("")

                if r.errors:
                    lines.append("**Errors:**")
                    for err in r.errors:
                        lines.append(f"- {err}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # Quality thresholds legend
        lines.extend([
            "## Quality Thresholds",
            "",
            "| Status | Precision | Recall | Variation |",
            "|--------|-----------|--------|-----------|",
            "| Draft | < 70% | < 50% | < 60% |",
            "| Ready | >= 70% | >= 50% | >= 60% |",
            "| Excellent | >= 90% | >= 85% | >= 85% |",
            "",
        ])

        return "\n".join(lines)

    def _status_badge(self, status: PatternStatus) -> str:
        """Get markdown badge for status."""
        if status == PatternStatus.EXCELLENT:
            return "🏆 Excellent"
        elif status == PatternStatus.READY:
            return "✅ Ready"
        else:
            return "📝 Draft"

    def generate_json_report(
        self,
        results: List[PatternTestResult],
    ) -> Dict[str, Any]:
        """Generate JSON report from results."""
        return generate_precision_report(results)


def main():
    parser = argparse.ArgumentParser(
        description="Generate VKG Pattern Precision Dashboard"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="docs/precision-dashboard.md",
        help="Output file path (default: docs/precision-dashboard.md)",
    )
    parser.add_argument(
        "--json",
        type=str,
        help="Also output JSON report to this path",
    )
    parser.add_argument(
        "--patterns-dir",
        type=str,
        default="patterns",
        help="Patterns directory (default: patterns)",
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Exclude detailed per-pattern breakdown",
    )
    parser.add_argument(
        "--pattern-id",
        type=str,
        help="Test only specific pattern ID",
    )

    args = parser.parse_args()

    print("VKG Pattern Precision Dashboard Generator")
    print("=" * 40)

    generator = PrecisionDashboardGenerator(patterns_dir=args.patterns_dir)

    # Filter specs if specific pattern requested
    specs = DEFAULT_TEST_SPECS
    if args.pattern_id:
        specs = [s for s in specs if s.pattern_id == args.pattern_id]
        if not specs:
            print(f"Warning: No test spec found for pattern '{args.pattern_id}'")
            print("Running with default specs...")
            specs = DEFAULT_TEST_SPECS

    print(f"\nRunning {len(specs)} pattern tests...")
    results = generator.run_tests(specs)

    # Generate markdown
    markdown = generator.generate_markdown(
        results,
        include_details=not args.no_details,
    )

    # Save markdown
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown)
    print(f"\nMarkdown dashboard saved to: {output_path}")

    # Save JSON if requested
    if args.json:
        json_report = generator.generate_json_report(results)
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(json_report, f, indent=2)
        print(f"JSON report saved to: {json_path}")

    # Print summary
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)

    total = len(results)
    passed = sum(1 for r in results if r.passed)

    print(f"Total patterns tested: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)" if total > 0 else "Passed: 0")
    print(f"Failed: {total - passed}")

    if results:
        avg_precision = sum(r.precision for r in results) / len(results)
        avg_recall = sum(r.recall for r in results) / len(results)
        print(f"Average Precision: {avg_precision:.1%}")
        print(f"Average Recall: {avg_recall:.1%}")

    # Show failed patterns
    failed = [r for r in results if not r.passed]
    if failed:
        print("\nFailed patterns:")
        for r in failed:
            print(f"  - {r.pattern_id}: precision={r.precision:.1%}, recall={r.recall:.1%}")

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
