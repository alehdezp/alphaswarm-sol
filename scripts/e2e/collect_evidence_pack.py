#!/usr/bin/env python3
"""
CLI runner for collecting evidence packs from test runs.

This script assembles evidence packs from various artifact sources:
- Transcripts from test captures
- Proof tokens from stage executions
- Debug artifacts from skills/agents
- Tool outputs (SARIF, JSON)
- Ground truth references

Usage:
    python scripts/e2e/collect_evidence_pack.py \\
        --source /tmp/raw-artifacts \\
        --output .vrs/validation/runs/run-001 \\
        --run-id run-001 \\
        --suite-id full-testing

    # With validation
    python scripts/e2e/collect_evidence_pack.py \\
        --output .vrs/validation/runs/run-001 \\
        --validate

    # Dry run
    python scripts/e2e/collect_evidence_pack.py \\
        --source /tmp/raw-artifacts \\
        --output .vrs/validation/runs/run-001 \\
        --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from alphaswarm_sol.testing.evidence_pack import (
    EvidencePackBuilder,
    EvidencePackManifest,
    assemble_evidence_pack,
    load_evidence_pack,
    validate_evidence_pack,
    EVIDENCE_PACK_SCHEMA_VERSION,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def collect_from_source(
    source_dir: Path,
    output_dir: Path,
    run_id: str,
    suite_id: str,
    dry_run: bool = False,
) -> EvidencePackManifest:
    """
    Collect evidence pack from source directory.

    Args:
        source_dir: Directory containing raw artifacts
        output_dir: Output directory for evidence pack
        run_id: Run identifier
        suite_id: Suite identifier
        dry_run: If True, only list what would be collected

    Returns:
        EvidencePackManifest
    """
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)

    if dry_run:
        logger.info("DRY RUN - listing artifacts that would be collected:")
        logger.info("")

        # List transcripts
        transcripts_dir = source_dir / "transcripts"
        if transcripts_dir.exists():
            logger.info("Transcripts:")
            for t in sorted(transcripts_dir.glob("*.txt")):
                logger.info(f"  - {t.name} ({t.stat().st_size} bytes)")
        else:
            logger.info("Transcripts: (none found)")

        # List proof tokens
        proofs_dir = source_dir / "proofs"
        if proofs_dir.exists():
            logger.info("Proof tokens:")
            for p in sorted(proofs_dir.glob("proof-*.json")):
                logger.info(f"  - {p.name}")
        else:
            logger.info("Proof tokens: (none found)")

        # List tool outputs
        tools_dir = source_dir / "tools"
        if tools_dir.exists():
            logger.info("Tool outputs:")
            for t in sorted(tools_dir.glob("*")):
                logger.info(f"  - {t.name}")
        else:
            logger.info("Tool outputs: (none found)")

        # List debug artifacts
        debug_dir = source_dir / "debug"
        if debug_dir.exists():
            logger.info("Debug artifacts:")
            for d in sorted(debug_dir.glob("*.json")):
                logger.info(f"  - {d.name}")
        else:
            logger.info("Debug artifacts: (none found)")

        logger.info("")
        logger.info(f"Would write to: {output_dir}")

        # Return empty manifest for dry run
        return EvidencePackManifest(
            run_id=run_id,
            suite_id=suite_id,
            command="/vrs-audit contracts/",
            duration_ms=0,
            session_id="dry-run",
        )

    # Actual collection
    logger.info(f"Collecting evidence pack from {source_dir}")
    logger.info(f"Output directory: {output_dir}")

    manifest = assemble_evidence_pack(
        source_dir=source_dir,
        output_dir=output_dir,
        run_id=run_id,
        suite_id=suite_id,
    )

    logger.info(f"Evidence pack collected: {output_dir / 'manifest.json'}")
    return manifest


def validate_pack(output_dir: Path) -> bool:
    """
    Validate an existing evidence pack.

    Args:
        output_dir: Directory containing evidence pack

    Returns:
        True if valid
    """
    output_dir = Path(output_dir)
    logger.info(f"Validating evidence pack: {output_dir}")

    is_valid, errors = validate_evidence_pack(output_dir)

    if is_valid:
        logger.info("Evidence pack is VALID")

        # Load and display summary
        manifest = load_evidence_pack(output_dir)
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  Run ID: {manifest.run_id}")
        logger.info(f"  Suite ID: {manifest.suite_id}")
        logger.info(f"  Duration: {manifest.duration_ms}ms")
        logger.info(f"  Transcripts: {len(manifest.transcript_hashes)}")
        logger.info(f"  Proof tokens: {len(manifest.proof_tokens)}")
        logger.info(f"  Debug artifacts: {len(manifest.debug_artifacts)}")
        logger.info(f"  Tool outputs: {len(manifest.tool_outputs)}")
    else:
        logger.error("Evidence pack is INVALID")
        logger.error("")
        logger.error("Validation errors:")
        for error in errors:
            logger.error(f"  - {error}")

    return is_valid


def display_manifest(output_dir: Path) -> None:
    """
    Display evidence pack manifest.

    Args:
        output_dir: Directory containing evidence pack
    """
    output_dir = Path(output_dir)
    manifest = load_evidence_pack(output_dir)

    print(json.dumps(manifest.to_dict(), indent=2))


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect evidence packs from test runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect from source directory
  %(prog)s --source /tmp/artifacts --output .vrs/runs/run-001 --run-id run-001

  # Validate existing pack
  %(prog)s --output .vrs/runs/run-001 --validate

  # Display manifest
  %(prog)s --output .vrs/runs/run-001 --show

  # Dry run
  %(prog)s --source /tmp/artifacts --output .vrs/runs/run-001 --dry-run
""",
    )

    parser.add_argument(
        "--source",
        type=Path,
        help="Source directory containing raw artifacts",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for evidence pack",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Run identifier (auto-generated if not provided)",
    )
    parser.add_argument(
        "--suite-id",
        default="full-testing",
        help="Suite identifier (default: full-testing)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing evidence pack",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display evidence pack manifest",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be collected without copying",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate mode
    if args.validate:
        is_valid = validate_pack(args.output)
        return 0 if is_valid else 1

    # Show mode
    if args.show:
        try:
            display_manifest(args.output)
            return 0
        except FileNotFoundError as e:
            logger.error(str(e))
            return 1

    # Collection mode
    if not args.source:
        logger.error("--source is required for collection mode")
        return 1

    if not args.source.exists():
        logger.error(f"Source directory not found: {args.source}")
        return 1

    # Generate run ID if not provided
    run_id = args.run_id
    if not run_id:
        run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        manifest = collect_from_source(
            source_dir=args.source,
            output_dir=args.output,
            run_id=run_id,
            suite_id=args.suite_id,
            dry_run=args.dry_run,
        )

        if not args.dry_run:
            # Validate after collection
            is_valid, errors = validate_evidence_pack(args.output)
            if not is_valid:
                logger.warning("Evidence pack collected but has validation errors:")
                for error in errors:
                    logger.warning(f"  - {error}")
                return 1

            logger.info("")
            logger.info("Collection complete and validated.")
            logger.info(f"Manifest: {args.output / 'manifest.json'}")

        return 0

    except Exception as e:
        logger.error(f"Collection failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
