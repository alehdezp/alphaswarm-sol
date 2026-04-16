#!/usr/bin/env python3
"""Corpus Coverage Audit CLI.

Run coverage audit across taxonomy, operations, and labels.

Usage:
    python scripts/corpus_coverage.py [--dry-run] [--output PATH] [--no-gaps]
    python scripts/corpus_coverage.py --report  # Show existing report
    python scripts/corpus_coverage.py --summary  # Quick summary only

Examples:
    # Dry run to preview audit
    python scripts/corpus_coverage.py --dry-run

    # Full audit with gap creation
    python scripts/corpus_coverage.py

    # Audit without creating gaps
    python scripts/corpus_coverage.py --no-gaps

    # Show existing coverage report
    python scripts/corpus_coverage.py --report
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def main() -> int:
    """Run corpus coverage audit CLI."""
    parser = argparse.ArgumentParser(
        description="Corpus coverage audit for taxonomy, operations, and labels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview audit without saving files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for coverage.yaml (default: .vrs/corpus/metadata/coverage.yaml)",
    )
    parser.add_argument(
        "--no-gaps",
        action="store_true",
        help="Don't create Gap records",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show existing coverage report",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show quick summary only",
    )
    parser.add_argument(
        "--corpus-version",
        type=str,
        default="v1",
        help="Corpus version string (default: v1)",
    )
    parser.add_argument(
        "--vulndocs-dir",
        type=Path,
        default=Path("vulndocs"),
        help="Path to vulndocs directory",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path(".vrs/corpus"),
        help="Path to corpus directory",
    )

    args = parser.parse_args()

    # Show existing report
    if args.report:
        report_path = args.output or (args.corpus_dir / "metadata" / "coverage.yaml")
        if not report_path.exists():
            print(f"ERROR: Coverage report not found at {report_path}", file=sys.stderr)
            print("Run without --report to generate a new report.", file=sys.stderr)
            return 1

        content = yaml.safe_load(report_path.read_text())
        print(yaml.dump(content, default_flow_style=False, sort_keys=False))
        return 0

    # Import here to avoid startup penalty when just showing help
    try:
        from alphaswarm_sol.testing.corpus.coverage import (
            CoverageAuditor,
            run_coverage_audit,
        )
    except ImportError as e:
        print(f"ERROR: Failed to import coverage module: {e}", file=sys.stderr)
        print("Make sure alphaswarm_sol is installed.", file=sys.stderr)
        return 1

    # Run audit
    print("Running coverage audit...")
    print(f"  VulnDocs: {args.vulndocs_dir}")
    print(f"  Corpus: {args.corpus_dir}")
    print()

    try:
        report = run_coverage_audit(
            vulndocs_dir=args.vulndocs_dir,
            corpus_dir=args.corpus_dir,
            output_path=args.output,
            create_gaps=not args.no_gaps,
            corpus_version=args.corpus_version,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"ERROR: Audit failed: {e}", file=sys.stderr)
        return 1

    # Print summary
    print("=" * 60)
    print("COVERAGE AUDIT SUMMARY")
    print("=" * 60)
    print()

    print(f"Generated: {report.generated_at}")
    print(f"Corpus Version: {report.corpus_version}")
    print()

    print("COVERAGE METRICS:")
    print(f"  Categories:  {report.category_coverage_pct:.1f}%")
    print(f"  Operations:  {report.operation_coverage_pct:.1f}%")
    print(f"  Labels:      {report.label_coverage_pct:.1f}%")
    print()

    print("CONTRACTS:")
    print(f"  Total:       {report.total_contracts}")
    print(f"  Vulnerable:  {report.vulnerable_contracts}")
    print(f"  Safe:        {report.safe_contracts}")
    print()

    # Show gaps summary if not summary-only mode
    if not args.summary:
        print("GAPS IDENTIFIED:")
        gap_counts = {"taxonomy": 0, "operation": 0, "label": 0}
        for gap in report.gaps:
            gap_type = gap.get("type", "unknown")
            gap_counts[gap_type] = gap_counts.get(gap_type, 0) + 1

        for gap_type, count in sorted(gap_counts.items()):
            if count > 0:
                print(f"  {gap_type.capitalize()}: {count}")

        print()
        print(f"Total gaps: {len(report.gaps)}")
        print()

        # Show top gaps by severity
        high_severity = [g for g in report.gaps if g.get("severity") == "high"]
        if high_severity:
            print("HIGH SEVERITY GAPS:")
            for gap in high_severity[:5]:
                print(f"  - {gap.get('description', 'Unknown')}")
            if len(high_severity) > 5:
                print(f"  ... and {len(high_severity) - 5} more")
            print()

    if args.dry_run:
        print("[DRY RUN] No files were saved.")
    else:
        output_path = args.output or (args.corpus_dir / "metadata" / "coverage.yaml")
        print(f"Report saved to: {output_path}")
        if not args.no_gaps:
            print("Gap records created in: .vrs/testing/gaps/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
