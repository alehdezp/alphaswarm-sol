#!/usr/bin/env python3
"""CLI for VulnDocs Reference Extraction and URL Ledger Management.

This script provides commands for:
- Extracting URLs from VulnDocs entries (index.yaml, research/*.md)
- Updating the canonical URL provenance ledger (.vrs/corpus/metadata/urls.yaml)
- Generating provenance coverage reports
- Finding missing provenance entries

Usage:
    python scripts/vulndocs_reference_extract.py extract [--category CATEGORY] [--dry-run]
    python scripts/vulndocs_reference_extract.py report
    python scripts/vulndocs_reference_extract.py missing [--category CATEGORY]

Per Phase 7.2 CONTEXT.md:
- The URL ledger is append-only (never delete for audit trail)
- Every URL must be logged with accessed_at, category, query, agent, extracted fields

Part of Plan 07.2-02: VulnDocs Reference Extraction
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alphaswarm_sol.vulndocs.reference_extract import (
    extract_from_vulndocs,
    update_ledger,
    find_missing_provenance,
    generate_provenance_report,
    URLLedger,
)


# Default paths
DEFAULT_VULNDOCS_ROOT = PROJECT_ROOT / "vulndocs"
DEFAULT_LEDGER_PATH = PROJECT_ROOT / ".vrs" / "corpus" / "metadata" / "urls.yaml"


def cmd_extract(args: argparse.Namespace) -> int:
    """Extract URLs from VulnDocs and update ledger.

    Returns:
        int: Exit code (0 for success)
    """
    vulndocs_root = Path(args.vulndocs_root)
    ledger_path = Path(args.ledger_path)

    print(f"Extracting URLs from: {vulndocs_root}")
    print(f"Ledger path: {ledger_path}")
    print()

    # Extract URLs
    result = extract_from_vulndocs(
        vulndocs_root,
        category_filter=args.category,
        agent="vulndocs_reference_extract",
    )

    print(f"Processed {len(result.source_files)} files")
    print(f"Found {len(result.entries)} unique URLs")
    print(f"Skipped {result.duplicates_skipped} duplicates (within extraction)")
    print()

    if result.errors:
        print("Errors encountered:")
        for err in result.errors:
            print(f"  - {err}")
        print()

    # Update ledger
    if args.dry_run:
        print("[DRY RUN] Would update ledger with:")
    else:
        print("Updating ledger...")

    added, skipped = update_ledger(
        ledger_path,
        result,
        dry_run=args.dry_run,
    )

    print(f"  Added: {added} new entries")
    print(f"  Skipped: {skipped} existing entries")

    if not args.dry_run and added > 0:
        print(f"\nLedger updated: {ledger_path}")

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate provenance coverage report.

    Returns:
        int: Exit code (0 for success)
    """
    vulndocs_root = Path(args.vulndocs_root)
    ledger_path = Path(args.ledger_path)

    print(f"Generating provenance report...")
    print(f"VulnDocs: {vulndocs_root}")
    print(f"Ledger: {ledger_path}")
    print()

    report = generate_provenance_report(vulndocs_root, ledger_path)

    print("=" * 60)
    print("PROVENANCE COVERAGE REPORT")
    print("=" * 60)
    print()
    print(f"Total URLs in VulnDocs: {report['total_urls']}")
    print(f"URLs with provenance:   {report['covered']}")
    print(f"URLs missing:           {report['missing']}")
    print(f"Coverage:               {report['coverage_pct']:.1f}%")
    print(f"Total ledger entries:   {report['ledger_total']}")
    print()

    print("By Category:")
    print("-" * 40)
    for cat, stats in sorted(report["categories"].items()):
        pct = (stats["covered"] / stats["total"] * 100) if stats["total"] else 100
        status = "OK" if pct >= 90 else ("WARN" if pct >= 50 else "GAP")
        print(f"  {cat:20} {stats['covered']:3}/{stats['total']:3} ({pct:5.1f}%) [{status}]")
    print()

    if report["missing_urls"]:
        print("Sample Missing URLs:")
        print("-" * 40)
        for url, category in report["missing_urls"][:10]:
            print(f"  [{category}] {url[:60]}...")
        if len(report["missing_urls"]) > 10:
            print(f"  ... and {len(report['missing_urls']) - 10} more")
        print()

    if report["errors"]:
        print("Errors:")
        print("-" * 40)
        for err in report["errors"]:
            print(f"  {err}")
        print()

    if args.json:
        print("\nJSON Report:")
        print(json.dumps(report, indent=2))

    return 0 if report["missing"] == 0 else 1


def cmd_missing(args: argparse.Namespace) -> int:
    """List URLs missing from provenance ledger.

    Returns:
        int: Exit code (0 if none missing, 1 if missing)
    """
    vulndocs_root = Path(args.vulndocs_root)
    ledger_path = Path(args.ledger_path)

    missing = find_missing_provenance(vulndocs_root, ledger_path)

    if args.category:
        missing = [(url, cat) for url, cat in missing if cat.startswith(args.category)]

    if not missing:
        print("No missing provenance entries found.")
        return 0

    print(f"Found {len(missing)} URLs missing from provenance ledger:")
    print()

    # Group by category
    by_category: dict[str, list[str]] = {}
    for url, category in missing:
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(url)

    for category in sorted(by_category.keys()):
        urls = by_category[category]
        print(f"[{category}] ({len(urls)} URLs)")
        for url in urls[:5]:
            print(f"  - {url}")
        if len(urls) > 5:
            print(f"  ... and {len(urls) - 5} more")
        print()

    return 1


def cmd_stats(args: argparse.Namespace) -> int:
    """Show ledger statistics.

    Returns:
        int: Exit code (0 for success)
    """
    ledger_path = Path(args.ledger_path)

    if not ledger_path.exists():
        print(f"Ledger not found: {ledger_path}")
        return 1

    ledger = URLLedger(ledger_path)

    print(f"Ledger: {ledger_path}")
    print(f"Schema version: {ledger.schema_version}")
    print(f"Total entries: {len(ledger.entries)}")
    print()

    # Categorize
    by_category: dict[str, int] = {}
    by_agent: dict[str, int] = {}
    extracted_count = 0

    for entry in ledger.entries:
        cat = entry.category.split("/")[0] if "/" in entry.category else entry.category
        by_category[cat] = by_category.get(cat, 0) + 1
        by_agent[entry.agent] = by_agent.get(entry.agent, 0) + 1
        if entry.extracted:
            extracted_count += 1

    print("By Category:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  {cat:25} {count:4}")
    print()

    print("By Agent:")
    for agent, count in sorted(by_agent.items(), key=lambda x: -x[1]):
        print(f"  {agent:35} {count:4}")
    print()

    print(f"Extracted: {extracted_count}/{len(ledger.entries)} ({extracted_count/len(ledger.entries)*100:.1f}%)")

    return 0


def main() -> int:
    """Main entry point.

    Returns:
        int: Exit code
    """
    parser = argparse.ArgumentParser(
        description="VulnDocs Reference Extraction and Provenance Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract URLs and update ledger (dry run)
  python scripts/vulndocs_reference_extract.py extract --dry-run

  # Extract URLs for a specific category
  python scripts/vulndocs_reference_extract.py extract --category oracle

  # Generate coverage report
  python scripts/vulndocs_reference_extract.py report

  # List missing provenance entries
  python scripts/vulndocs_reference_extract.py missing

  # Show ledger statistics
  python scripts/vulndocs_reference_extract.py stats
""",
    )

    parser.add_argument(
        "--vulndocs-root",
        default=str(DEFAULT_VULNDOCS_ROOT),
        help=f"Path to vulndocs directory (default: {DEFAULT_VULNDOCS_ROOT})",
    )
    parser.add_argument(
        "--ledger-path",
        default=str(DEFAULT_LEDGER_PATH),
        help=f"Path to URL ledger (default: {DEFAULT_LEDGER_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # extract command
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract URLs from VulnDocs and update ledger",
    )
    extract_parser.add_argument(
        "--category",
        help="Filter by category (e.g., 'oracle', 'reentrancy')",
    )
    extract_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually update the ledger",
    )
    extract_parser.set_defaults(func=cmd_extract)

    # report command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate provenance coverage report",
    )
    report_parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON",
    )
    report_parser.set_defaults(func=cmd_report)

    # missing command
    missing_parser = subparsers.add_parser(
        "missing",
        help="List URLs missing from provenance ledger",
    )
    missing_parser.add_argument(
        "--category",
        help="Filter by category (e.g., 'oracle', 'reentrancy')",
    )
    missing_parser.set_defaults(func=cmd_missing)

    # stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show ledger statistics",
    )
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
