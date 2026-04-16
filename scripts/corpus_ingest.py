#!/usr/bin/env python3
"""
Corpus Ingestion CLI - Reproducible corpus population from pinned sources.

Usage:
    uv run python scripts/corpus_ingest.py                    # Ingest all sources
    uv run python scripts/corpus_ingest.py --category vulnerable
    uv run python scripts/corpus_ingest.py --dry-run          # Preview only
    uv run python scripts/corpus_ingest.py --list-sources     # List available sources

Examples:
    # Preview what would be ingested
    uv run python scripts/corpus_ingest.py --dry-run

    # Ingest only vulnerable contracts
    uv run python scripts/corpus_ingest.py --category vulnerable

    # Ingest specific sources
    uv run python scripts/corpus_ingest.py --sources dvdefi-v3,ethernaut

    # Show corpus statistics
    uv run python scripts/corpus_ingest.py --stats
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from alphaswarm_sol.testing.corpus.ingest import CorpusIngest, IngestSummary


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def print_summary(summary: IngestSummary) -> None:
    """Print ingestion summary."""
    print("\n" + "=" * 60)
    print("CORPUS INGESTION SUMMARY")
    print("=" * 60)
    print(f"Started:   {summary.started_at}")
    print(f"Completed: {summary.completed_at}")
    print(f"Dry run:   {summary.dry_run}")
    print()
    print(f"Sources processed:      {summary.sources_processed}")
    print(f"Contracts found:        {summary.total_contracts_found}")
    print(f"Contracts ingested:     {summary.total_contracts_ingested}")
    print()

    if summary.results:
        print("Per-source results:")
        print("-" * 60)
        for result in summary.results:
            status = "OK" if result.success else "FAIL"
            commit = result.commit_sha[:8] if result.commit_sha else "N/A"
            print(f"  [{status}] {result.source_id}: {result.contracts_ingested}/{result.contracts_found} contracts @ {commit}")
            if result.error:
                print(f"         Error: {result.error}")
            if result.ground_truth_stubs:
                for stub in result.ground_truth_stubs:
                    print(f"         Ground truth stub: {stub}")
        print()

    if summary.errors:
        print("Errors:")
        print("-" * 60)
        for error in summary.errors:
            print(f"  - {error}")
        print()

    if summary.dry_run:
        print("NOTE: Dry run mode - no files were copied or database updated.")
        print("      Run without --dry-run to perform actual ingestion.")


def list_sources(ingest: CorpusIngest, category: str | None = None) -> None:
    """List available sources."""
    print("\n" + "=" * 60)
    print("AVAILABLE CORPUS SOURCES")
    print("=" * 60)

    sources = list(ingest.list_sources(category=category))

    if not sources:
        print("No sources found.")
        return

    for source in sources:
        pinned = "pinned" if source.commit_sha else "unpinned"
        print(f"\n[{source.category}] {source.id} ({pinned})")
        print(f"  URL:      {source.repo_url}")
        print(f"  Path:     {source.local_path}")
        print(f"  Expected: {source.expected_contracts} contracts")
        if source.commit_sha:
            print(f"  Commit:   {source.commit_sha[:8]}")
        if source.vulnerability_classes:
            print(f"  Vulns:    {', '.join(source.vulnerability_classes)}")
        if source.notes:
            print(f"  Notes:    {source.notes}")

    print()


def show_stats(ingest: CorpusIngest) -> None:
    """Show corpus statistics."""
    print("\n" + "=" * 60)
    print("CORPUS STATISTICS")
    print("=" * 60)

    stats = ingest.get_stats()
    print(f"Total contracts:    {stats['total_contracts']}")
    print(f"Ground truth items: {stats['total_ground_truth']}")
    print(f"Test runs:          {stats['test_runs']}")
    print()

    if stats["by_category"]:
        print("By category:")
        for cat, count in stats["by_category"].items():
            print(f"  {cat}: {count}")
    else:
        print("No contracts in corpus yet.")

    print()


def main() -> int:
    """Run corpus ingestion CLI."""
    parser = argparse.ArgumentParser(
        description="Corpus ingestion - reproducible population from pinned sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to sources.yaml manifest (default: .vrs/corpus/metadata/sources.yaml)",
    )
    parser.add_argument(
        "--category",
        choices=["vulnerable", "safe", "adversarial", "mutations", "recent-audits"],
        help="Filter to only sources of this category",
    )
    parser.add_argument(
        "--sources",
        help="Comma-separated list of source IDs to ingest",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be ingested without making changes",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List available sources and exit",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show corpus statistics and exit",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Initialize ingestion engine
    try:
        ingest = CorpusIngest(manifest_path=args.manifest)
    except Exception as e:
        print(f"ERROR: Failed to initialize ingestion engine: {e}")
        return 1

    # Handle info commands
    if args.list_sources:
        list_sources(ingest, category=args.category)
        return 0

    if args.stats:
        show_stats(ingest)
        return 0

    # Parse source IDs
    source_ids = None
    if args.sources:
        source_ids = [s.strip() for s in args.sources.split(",")]

    # Run ingestion
    print("Starting corpus ingestion...")
    try:
        summary = ingest.run(
            category=args.category,
            source_ids=source_ids,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"ERROR: Ingestion failed: {e}")
        return 1

    print_summary(summary)

    # Return exit code based on errors
    if summary.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
