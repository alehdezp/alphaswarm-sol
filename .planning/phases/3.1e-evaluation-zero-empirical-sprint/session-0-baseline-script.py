#!/usr/bin/env python3
"""Session 0 Baseline Script -- Phase 3.1e Measurement Prerequisites.

Builds knowledge graphs for all 7 CORPUS contracts, runs pattern detection
with per-function-firing granularity, computes graph fingerprints, and
produces baseline-before.json and graph-fingerprints.json.

Usage:
    python session-0-baseline-script.py                  # Full run
    python session-0-baseline-script.py --dry-run        # Smoke test (no graph builds)
    python session-0-baseline-script.py --limit 49       # Fails: limit assertion

Output:
    .vrs/experiments/plan-01/baseline-before.json
    .vrs/experiments/session-0/graph-fingerprints.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Imports from production modules
# ---------------------------------------------------------------------------
from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.kg.fingerprint import graph_fingerprint
from alphaswarm_sol.queries.patterns import PatternEngine, get_patterns
from alphaswarm_sol.queries.report import _function_contract_map

# Import CORPUS and GroundTruth from detection baseline test
from tests.evaluation.test_detection_baseline import (
    CORPUS,
    DEFAULT_LENSES,
    GroundTruth,
)

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parents[3]
BASELINE_OUT = ROOT / ".vrs" / "experiments" / "plan-01" / "baseline-before.json"
FINGERPRINT_OUT = ROOT / ".vrs" / "experiments" / "session-0" / "graph-fingerprints.json"


# ---------------------------------------------------------------------------
# CORPUS Validation (FIRST step, before any graph build or query)
# ---------------------------------------------------------------------------

def validate_corpus() -> None:
    """Validate CORPUS structure and content.

    Exits with code 1 on any validation failure, printing diagnostic info.
    """
    if not isinstance(CORPUS, list) or len(CORPUS) == 0:
        print(f"BLOCKING: CORPUS is not a non-empty list. type={type(CORPUS)}, len={len(CORPUS) if isinstance(CORPUS, list) else 'N/A'}")
        raise SystemExit(1)

    for i, element in enumerate(CORPUS):
        if not isinstance(element, GroundTruth):
            print(f"BLOCKING: CORPUS[{i}] is not a GroundTruth instance. type={type(element)}")
            raise SystemExit(1)

        for field_name in ("contract_path", "target_contract_label", "expected_patterns"):
            value = getattr(element, field_name, None)
            if value is None:
                print(f"BLOCKING: CORPUS[{i}].{field_name} is None")
                raise SystemExit(1)

    print(f"CORPUS validation passed: {len(CORPUS)} GroundTruth elements")


# ---------------------------------------------------------------------------
# Query wrapper with runtime limit invariant
# ---------------------------------------------------------------------------

def run_query(
    engine: PatternEngine,
    graph: Any,
    patterns: list,
    *,
    lens: list[str],
    limit: int = 200,
    explain: bool = True,
) -> list[dict[str, Any]]:
    """Run pattern query with runtime limit assertion."""
    assert limit >= 200, f"BLOCKING: limit={limit} will truncate results"
    return engine.run(
        graph,
        patterns,
        lens=lens,
        limit=limit,
        explain=explain,
    )


# ---------------------------------------------------------------------------
# Ground truth join
# ---------------------------------------------------------------------------

def build_corpus_map() -> dict[str, set[str]]:
    """Build corpus_by_contract mapping from CORPUS."""
    return {
        gt.target_contract_label: set(gt.expected_patterns)
        for gt in CORPUS
    }


def is_tp(pattern_id: str, contract_label: str, corpus_map: dict[str, set[str]]) -> bool:
    """Determine if a finding is a true positive based on ground truth."""
    expected = corpus_map.get(contract_label, set())
    return pattern_id in expected


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Session 0 baseline capture")
    parser.add_argument("--dry-run", action="store_true", help="Smoke test only")
    parser.add_argument("--limit", type=int, default=200, help="Query limit")
    args = parser.parse_args()

    # Step 0: Always validate CORPUS first
    validate_corpus()

    # Step 0b: Runtime limit check (fires on --limit 49 etc.)
    if args.limit < 200:
        print(f"BLOCKING: limit={args.limit} will truncate results")
        raise SystemExit(1)

    if args.dry_run:
        print("Dry-run mode: CORPUS validated, limit assertion checked. Exiting.")
        return

    # Step 1: Load patterns once
    patterns = get_patterns()
    engine = PatternEngine()
    corpus_map = build_corpus_map()
    builder = VKGBuilder(ROOT)
    timestamp = datetime.now(timezone.utc).isoformat()

    # Step 2: Compute corpus file hash for drift detection
    corpus_file = ROOT / "tests" / "evaluation" / "test_detection_baseline.py"
    corpus_sha256 = hashlib.sha256(corpus_file.read_bytes()).hexdigest()

    # Step 3: Process each contract
    per_contract: dict[str, dict[str, Any]] = {}
    fingerprints: list[dict[str, Any]] = []
    all_findings_flat: list[dict[str, Any]] = []

    for gt in CORPUS:
        contract_name = gt.target_contract_label
        print(f"Processing {contract_name}...")

        if not gt.contract_path.exists():
            print(f"  WARNING: Contract not found: {gt.contract_path}. Skipping.")
            continue

        # Build graph
        graph = builder.build(gt.contract_path)

        # Compute fingerprint (returns 64-char hex string)
        fp = graph_fingerprint(graph)
        fingerprints.append({
            "contract": contract_name,
            "fingerprint": fp,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        })

        # Run pattern query with explain=True
        findings = run_query(
            engine, graph, patterns,
            lens=DEFAULT_LENSES, limit=args.limit, explain=True,
        )

        # Build function -> contract label map
        fn_contract_map = _function_contract_map(graph)
        # Resolve contract labels from node IDs
        contract_label_map: dict[str, str] = {}
        for node_id, contract_node_id in fn_contract_map.items():
            contract_node = graph.nodes.get(contract_node_id)
            if contract_node:
                contract_label_map[node_id] = contract_node.label

        # Verify at least one resolved label matches the target
        resolved_labels = set(contract_label_map.values())
        assert contract_name in resolved_labels or len(findings) == 0, (
            f"No resolved label matches target {contract_name}. "
            f"Resolved: {resolved_labels}"
        )

        # Extract per-function firings for the target contract
        contract_findings: list[dict[str, Any]] = []
        tp_count = 0
        fp_count = 0

        for finding in findings:
            node_id = finding.get("node_id", "")
            resolved_contract = contract_label_map.get(node_id, "unknown")

            # Only include findings for the target contract
            if resolved_contract != contract_name:
                continue

            pattern_id = finding.get("pattern_id", "")
            node_label = finding.get("node_label", "")
            finding_is_tp = is_tp(pattern_id, contract_name, corpus_map)

            # Extract fired_conditions from explain output
            explain_data = finding.get("explain", {})
            fired_conditions = {
                "all": explain_data.get("all", []),
                "any": explain_data.get("any", []),
                "none": explain_data.get("none", []),
                "edges": explain_data.get("edges", []),
            }

            record = {
                "contract": contract_name,
                "pattern_id": pattern_id,
                "function_name": node_label,
                "node_id": node_id,
                "is_tp": finding_is_tp,
                "fired_conditions": fired_conditions,
            }
            contract_findings.append(record)
            all_findings_flat.append(record)

            if finding_is_tp:
                tp_count += 1
            else:
                fp_count += 1

        per_contract[contract_name] = {
            "findings": contract_findings,
            "tp_count": tp_count,
            "fp_count": fp_count,
            "total": len(contract_findings),
        }
        print(f"  {contract_name}: {tp_count} TP, {fp_count} FP, {len(contract_findings)} total")

    # Step 4: Compute totals
    total_tp = sum(c["tp_count"] for c in per_contract.values())
    total_fp = sum(c["fp_count"] for c in per_contract.values())
    total_findings = sum(c["total"] for c in per_contract.values())

    # Step 5: Write baseline-before.json
    baseline = {
        "meta": {
            "timestamp": timestamp,
            "query_params": {
                "limit": args.limit,
            },
            "graph_fingerprint": "see graph-fingerprints.json",
            "corpus_size": len(CORPUS),
        },
        "_run_params": {
            "limit": args.limit,
            "lens": DEFAULT_LENSES,
        },
        "per_contract": per_contract,
        "totals": {
            "tp": total_tp,
            "fp": total_fp,
            "total": total_findings,
            "contracts_tested": len(per_contract),
        },
    }

    BASELINE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_OUT.write_text(json.dumps(baseline, indent=2))
    print(f"\nBaseline written to {BASELINE_OUT}")
    print(f"  Total: {total_tp} TP, {total_fp} FP, {total_findings} findings")

    # Step 6: Write graph-fingerprints.json
    fingerprint_data = {
        "contracts": fingerprints,
        "_corpus_version": {
            "sha256": corpus_sha256,
            "file": "tests/evaluation/test_detection_baseline.py",
        },
    }
    FINGERPRINT_OUT.parent.mkdir(parents=True, exist_ok=True)
    FINGERPRINT_OUT.write_text(json.dumps(fingerprint_data, indent=2))
    print(f"Fingerprints written to {FINGERPRINT_OUT}")
    print(f"  {len(fingerprints)} contracts fingerprinted")


if __name__ == "__main__":
    main()
