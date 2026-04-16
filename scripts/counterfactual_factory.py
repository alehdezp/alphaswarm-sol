#!/usr/bin/env python3
"""Counterfactual Factory CLI.

Generate near-miss counterfactual variants of contracts for testing
pattern detection robustness.

Usage:
    python scripts/counterfactual_factory.py [--dry-run] [--source PATH]
    python scripts/counterfactual_factory.py --list  # List existing counterfactuals
    python scripts/counterfactual_factory.py --generate-hard-negatives

Examples:
    # Dry run to preview generation
    python scripts/counterfactual_factory.py --dry-run

    # Generate from specific source
    python scripts/counterfactual_factory.py --source tests/contracts/Reentrancy.sol

    # Generate from corpus vulnerable contracts
    python scripts/counterfactual_factory.py --from-corpus

    # List existing counterfactuals
    python scripts/counterfactual_factory.py --list

    # Generate hard-negative suite
    python scripts/counterfactual_factory.py --generate-hard-negatives
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def main() -> int:
    """Run counterfactual factory CLI."""
    parser = argparse.ArgumentParser(
        description="Generate counterfactual contract variants for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview generation without writing files",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Path to source contract for counterfactual generation",
    )
    parser.add_argument(
        "--from-corpus",
        action="store_true",
        help="Generate from corpus vulnerable contracts",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".vrs/corpus/contracts/adversarial/counterfactual"),
        help="Output directory for counterfactuals",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing counterfactuals",
    )
    parser.add_argument(
        "--generate-hard-negatives",
        action="store_true",
        help="Generate hard-negative suite",
    )
    parser.add_argument(
        "--types",
        type=str,
        nargs="+",
        help="Counterfactual types to generate (guard_inversion, cei_order_swap, etc.)",
    )

    args = parser.parse_args()

    # Import here to avoid startup penalty
    try:
        from alphaswarm_sol.testing.mutations import (
            CounterfactualGenerator,
            CounterfactualType,
            create_hard_negative_contract,
        )
    except ImportError as e:
        print(f"ERROR: Failed to import mutations module: {e}", file=sys.stderr)
        print("Make sure alphaswarm_sol is installed.", file=sys.stderr)
        return 1

    generator = CounterfactualGenerator(output_dir=args.output_dir)

    # List existing counterfactuals
    if args.list:
        counterfactuals = generator.list_counterfactuals()
        if not counterfactuals:
            print("No counterfactuals found.")
            return 0

        print(f"Found {len(counterfactuals)} counterfactuals:")
        print()
        for cf in counterfactuals:
            print(f"  ID: {cf.get('counterfactual_id')}")
            print(f"  Type: {cf.get('counterfactual_type')}")
            print(f"  Base: {cf.get('base_contract_id')}")
            print(f"  Status: {cf.get('expected_vulnerability_status')}")
            print(f"  Diff: {cf.get('semantic_diff')}")
            print()
        return 0

    # Generate hard-negative suite
    if args.generate_hard_negatives:
        print("Generating hard-negative suite...")

        hard_negatives = [
            {
                "name": "ReentrancyWithGuard",
                "vulnerability_class": "reentrancy",
                "safe_variant": "Has nonReentrant modifier",
            },
            {
                "name": "OwnershipWithTimelock",
                "vulnerability_class": "access-control",
                "safe_variant": "Has 48-hour timelock on ownership transfer",
            },
            {
                "name": "OracleWithStalenessCheck",
                "vulnerability_class": "oracle-staleness",
                "safe_variant": "Validates updatedAt within acceptable range",
            },
            {
                "name": "FlashLoanWithCooldown",
                "vulnerability_class": "flash-loan-governance",
                "safe_variant": "Has 2-block cooldown after token transfer",
            },
            {
                "name": "DelegateCallWithWhitelist",
                "vulnerability_class": "delegatecall",
                "safe_variant": "Only calls whitelisted implementation addresses",
            },
            {
                "name": "ExternalCallWithCEI",
                "vulnerability_class": "cei-violation",
                "safe_variant": "Follows Check-Effect-Interaction pattern",
            },
            {
                "name": "HelperCallWithInlinedCheck",
                "vulnerability_class": "helper-depth-bypass",
                "safe_variant": "Access check inlined, not in separate helper",
            },
            {
                "name": "L2SequencerWithGrace",
                "vulnerability_class": "l2-sequencer-grace",
                "safe_variant": "Has proper grace period after sequencer restart",
            },
        ]

        output_dir = Path(".vrs/corpus/contracts/safe")

        if args.dry_run:
            print("[DRY RUN] Would create:")
            for hn in hard_negatives:
                print(f"  - HardNegative_{hn['name']}.sol")
            return 0

        for hn in hard_negatives:
            path = create_hard_negative_contract(
                name=hn["name"],
                vulnerability_class=hn["vulnerability_class"],
                safe_variant=hn["safe_variant"],
                output_dir=output_dir,
            )
            print(f"  Created: {path}")

        print(f"\nGenerated {len(hard_negatives)} hard-negative contracts")
        return 0

    # Generate counterfactuals from source
    if args.source:
        if not args.source.exists():
            print(f"ERROR: Source file not found: {args.source}", file=sys.stderr)
            return 1

        # Parse types if specified
        cf_types = None
        if args.types:
            cf_types = []
            for t in args.types:
                try:
                    cf_types.append(CounterfactualType(t))
                except ValueError:
                    print(f"ERROR: Unknown counterfactual type: {t}", file=sys.stderr)
                    print(f"Valid types: {[t.value for t in CounterfactualType]}")
                    return 1

        base_id = args.source.stem.lower().replace(" ", "-")

        print(f"Generating counterfactuals from: {args.source}")
        print(f"Base contract ID: {base_id}")
        print(f"Output directory: {args.output_dir}")
        print()

        if args.dry_run:
            print("[DRY RUN] Would generate counterfactuals of types:")
            types_to_show = cf_types or list(CounterfactualType)
            for cf_type in types_to_show:
                print(f"  - {cf_type.value}")
            return 0

        results = generator.generate_counterfactuals(
            source_path=args.source,
            base_contract_id=base_id,
            types=cf_types,
        )

        if not results:
            print("No counterfactuals generated (no applicable patterns found)")
            return 0

        print(f"Generated {len(results)} counterfactuals:")
        for result in results:
            status = result.expected_vulnerability_status.value
            print(f"  [{status.upper():10}] {result.counterfactual_id}")
            print(f"             {result.description}")

        return 0

    # Generate from corpus
    if args.from_corpus:
        corpus_vuln_dir = Path(".vrs/corpus/contracts/vulnerable")
        if not corpus_vuln_dir.exists():
            print(f"ERROR: Corpus vulnerable directory not found: {corpus_vuln_dir}")
            return 1

        sol_files = list(corpus_vuln_dir.rglob("*.sol"))
        if not sol_files:
            print("No Solidity files found in corpus vulnerable directory")
            return 1

        print(f"Found {len(sol_files)} vulnerable contracts in corpus")
        print()

        if args.dry_run:
            print("[DRY RUN] Would process:")
            for sol_file in sol_files[:10]:
                print(f"  - {sol_file.name}")
            if len(sol_files) > 10:
                print(f"  ... and {len(sol_files) - 10} more")
            return 0

        total_generated = 0
        for sol_file in sol_files:
            base_id = sol_file.stem.lower().replace(" ", "-")
            try:
                results = generator.generate_counterfactuals(
                    source_path=sol_file,
                    base_contract_id=base_id,
                )
                if results:
                    total_generated += len(results)
                    print(f"  {sol_file.name}: {len(results)} counterfactuals")
            except Exception as e:
                print(f"  {sol_file.name}: ERROR - {e}", file=sys.stderr)

        print()
        print(f"Total counterfactuals generated: {total_generated}")
        return 0

    # No action specified
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
