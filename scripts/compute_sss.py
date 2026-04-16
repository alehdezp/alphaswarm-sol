#!/usr/bin/env python3
"""Compute Semantic Stability Score (SSS) for GA Validation (Plan 07.3-02).

Compares behavioral signatures between original and obfuscated contracts
to validate that detection is truly name-agnostic.

SSS = |intersection of signatures| / |union of signatures|

Purpose: Prove "Names lie. Behavior does not." - PHILOSOPHY.md Pillar 2
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


@dataclass
class ContractComparison:
    """Comparison result for a single contract pair."""

    original_name: str
    obfuscated_name: str
    original_signatures: List[str]
    obfuscated_signatures: List[str]
    intersection_size: int
    union_size: int
    sss: float
    status: str  # "pass" or "fail"


@dataclass
class PatternComparison:
    """SSS comparison aggregated by pattern."""

    pattern: str
    contract_count: int
    avg_sss: float
    min_sss: float
    max_sss: float
    pass_count: int
    fail_count: int


@dataclass
class SSSReport:
    """Full SSS validation report."""

    generated_at: str
    manifest_path: str
    total_contracts: int
    contracts_processed: int
    contracts_skipped: int
    overall_sss: float
    min_sss: float
    max_sss: float
    threshold: float
    passes_gate: bool

    contract_comparisons: List[ContractComparison]
    pattern_breakdown: List[PatternComparison]
    failed_patterns: List[str]


def extract_signatures_from_graph(graph: Any) -> List[str]:
    """Extract behavioral signatures from a KnowledgeGraph.

    Args:
        graph: KnowledgeGraph object

    Returns:
        List of behavioral signature strings
    """
    signatures = []

    for node_id, node in graph.nodes.items():
        if node.type.lower() != "function":
            continue

        sig = node.properties.get("behavioral_signature", "")
        if sig:
            signatures.append(sig)

    return signatures


def build_graph(contract_path: Path) -> Optional[Any]:
    """Build knowledge graph for a contract.

    Args:
        contract_path: Path to .sol file

    Returns:
        KnowledgeGraph or None on failure
    """
    from alphaswarm_sol.kg.builder.core import VKGBuilder

    if not contract_path.exists():
        return None

    try:
        builder = VKGBuilder(
            contract_path.parent,
            exclude_dependencies=True,
            generate_completeness_report=False,
        )
        return builder.build(contract_path)
    except Exception as e:
        print(f"  WARN: Graph build failed for {contract_path.name}: {str(e)[:100]}")
        return None


def compute_sss(original_sigs: List[str], obfuscated_sigs: List[str]) -> Tuple[float, int, int]:
    """Compute Semantic Stability Score between two signature sets.

    Args:
        original_sigs: Signatures from original contract
        obfuscated_sigs: Signatures from obfuscated contract

    Returns:
        Tuple of (sss_score, intersection_size, union_size)
    """
    # Use sets for comparison
    orig_set = set(original_sigs)
    obf_set = set(obfuscated_sigs)

    intersection = orig_set & obf_set
    union = orig_set | obf_set

    if not union:
        return 1.0, 0, 0  # Both empty = perfect match

    sss = len(intersection) / len(union)
    return sss, len(intersection), len(union)


def run_sss_validation(
    manifest_path: Path,
    obfuscated_dir: Path,
    original_base_dir: Path,
    threshold: float = 0.85,
) -> SSSReport:
    """Run SSS validation on contract pairs from manifest.

    Args:
        manifest_path: Path to MANIFEST.yaml
        obfuscated_dir: Directory containing obfuscated contracts
        original_base_dir: Base directory for resolving original paths
        threshold: SSS threshold for passing (default: 0.85)

    Returns:
        SSSReport with validation results
    """
    # Load manifest
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    contracts = manifest.get("contracts", [])
    total = len(contracts)
    print(f"Loaded manifest with {total} contract pairs")

    comparisons: List[ContractComparison] = []
    pattern_stats: Dict[str, List[float]] = {}
    processed = 0
    skipped = 0

    for entry in contracts:
        original_rel = entry.get("original", "")
        obfuscated_name = entry.get("obfuscated", "")
        expected_vulns = entry.get("expected_vulnerabilities", [])

        original_path = original_base_dir / original_rel
        obfuscated_path = obfuscated_dir / obfuscated_name

        print(f"\nProcessing: {Path(original_rel).name} vs {obfuscated_name}")

        # Build graphs
        orig_graph = build_graph(original_path)
        obf_graph = build_graph(obfuscated_path)

        if orig_graph is None or obf_graph is None:
            print(f"  SKIP: Could not build graph(s)")
            skipped += 1
            continue

        # Extract signatures
        orig_sigs = extract_signatures_from_graph(orig_graph)
        obf_sigs = extract_signatures_from_graph(obf_graph)

        print(f"  Original signatures: {orig_sigs}")
        print(f"  Obfuscated signatures: {obf_sigs}")

        # Compute SSS
        sss, inter_size, union_size = compute_sss(orig_sigs, obf_sigs)
        status = "pass" if sss >= threshold else "fail"

        print(f"  SSS: {sss:.2f} (intersection={inter_size}, union={union_size}) [{status.upper()}]")

        comparisons.append(ContractComparison(
            original_name=Path(original_rel).name,
            obfuscated_name=obfuscated_name,
            original_signatures=orig_sigs,
            obfuscated_signatures=obf_sigs,
            intersection_size=inter_size,
            union_size=union_size,
            sss=sss,
            status=status,
        ))

        # Track by pattern
        for vuln in expected_vulns:
            if vuln not in pattern_stats:
                pattern_stats[vuln] = []
            pattern_stats[vuln].append(sss)

        processed += 1

    # Compute overall stats
    all_sss = [c.sss for c in comparisons]
    overall_sss = sum(all_sss) / len(all_sss) if all_sss else 0.0
    min_sss = min(all_sss) if all_sss else 0.0
    max_sss = max(all_sss) if all_sss else 0.0

    # Build pattern breakdown
    pattern_breakdown: List[PatternComparison] = []
    for pattern, scores in sorted(pattern_stats.items()):
        pc = PatternComparison(
            pattern=pattern,
            contract_count=len(scores),
            avg_sss=sum(scores) / len(scores) if scores else 0.0,
            min_sss=min(scores) if scores else 0.0,
            max_sss=max(scores) if scores else 0.0,
            pass_count=sum(1 for s in scores if s >= threshold),
            fail_count=sum(1 for s in scores if s < threshold),
        )
        pattern_breakdown.append(pc)

    # Find failed patterns
    failed_patterns = [p.pattern for p in pattern_breakdown if p.min_sss < threshold]

    # Determine gate status
    passes_gate = overall_sss >= threshold

    return SSSReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        manifest_path=str(manifest_path),
        total_contracts=total,
        contracts_processed=processed,
        contracts_skipped=skipped,
        overall_sss=overall_sss,
        min_sss=min_sss,
        max_sss=max_sss,
        threshold=threshold,
        passes_gate=passes_gate,
        contract_comparisons=comparisons,
        pattern_breakdown=pattern_breakdown,
        failed_patterns=failed_patterns,
    )


def serialize_report(report: SSSReport) -> Dict[str, Any]:
    """Serialize report to JSON-compatible dict."""
    return {
        "generated_at": report.generated_at,
        "manifest_path": report.manifest_path,
        "total_contracts": report.total_contracts,
        "contracts_processed": report.contracts_processed,
        "contracts_skipped": report.contracts_skipped,
        "overall_sss": report.overall_sss,
        "min_sss": report.min_sss,
        "max_sss": report.max_sss,
        "threshold": report.threshold,
        "passes_gate": report.passes_gate,
        "contract_comparisons": [asdict(c) for c in report.contract_comparisons],
        "pattern_breakdown": [asdict(p) for p in report.pattern_breakdown],
        "failed_patterns": report.failed_patterns,
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compute Semantic Stability Score (SSS) for obfuscated contracts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(".vrs/testing/corpus/obfuscated/MANIFEST.yaml"),
        help="Path to manifest YAML file",
    )
    parser.add_argument(
        "--obfuscated-dir",
        type=Path,
        default=Path(".vrs/testing/corpus/obfuscated"),
        help="Directory containing obfuscated contracts",
    )
    parser.add_argument(
        "--original-base",
        type=Path,
        default=Path("."),
        help="Base directory for resolving original contract paths",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="SSS threshold for passing (default: 0.85)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".vrs/testing/reports/semantic-stability.json"),
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without writing output",
    )

    args = parser.parse_args()

    # Validate paths
    if not args.manifest.exists():
        print(f"ERROR: Manifest not found: {args.manifest}")
        return 1

    if not args.obfuscated_dir.exists():
        print(f"ERROR: Obfuscated directory not found: {args.obfuscated_dir}")
        return 1

    print("=" * 60)
    print("SEMANTIC STABILITY SCORE (SSS) VALIDATION")
    print("=" * 60)
    print()

    # Run validation
    report = run_sss_validation(
        manifest_path=args.manifest,
        obfuscated_dir=args.obfuscated_dir,
        original_base_dir=args.original_base,
        threshold=args.threshold,
    )

    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print(f"Contracts processed:  {report.contracts_processed}/{report.total_contracts}")
    print(f"Contracts skipped:    {report.contracts_skipped}")
    print()
    print(f"Overall SSS:          {report.overall_sss:.2f}")
    print(f"Min SSS:              {report.min_sss:.2f}")
    print(f"Max SSS:              {report.max_sss:.2f}")
    print(f"Threshold:            {report.threshold}")
    print()

    print("PATTERN BREAKDOWN:")
    for pb in report.pattern_breakdown:
        status = "PASS" if pb.min_sss >= args.threshold else "WARN"
        print(f"  {pb.pattern:30s}: {pb.contract_count} contracts, "
              f"avg={pb.avg_sss:.2f}, min={pb.min_sss:.2f}, max={pb.max_sss:.2f} [{status}]")
    print()

    if report.failed_patterns:
        print("PATTERNS WITH SSS < THRESHOLD:")
        for pattern in report.failed_patterns:
            print(f"  - {pattern}")
        print()

    gate_status = "PASSED" if report.passes_gate else "FAILED"
    print(f"SSS GATE: {gate_status} (overall={report.overall_sss:.2f} vs threshold={report.threshold})")
    print()

    # Write output
    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(serialize_report(report), f, indent=2)
        print(f"Report written to: {args.output}")
    else:
        print("[DRY RUN] Report not written")

    return 0 if report.passes_gate else 1


if __name__ == "__main__":
    sys.exit(main())
