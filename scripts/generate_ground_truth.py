#!/usr/bin/env python3
"""Generate ground truth graph stats and persist graphs for calibration contracts.

Runs `uv run alphaswarm build-kg` on each calibration contract, captures the actual
node/edge counts from build output, copies the graph.toon to a persistent location,
and writes stats.json with semantic metadata.

Usage:
    uv run python scripts/generate_ground_truth.py

Output:
    .vrs/ground-truth/cal-XX/stats.json        — full stats with semantic metadata
    .vrs/ground-truth/cal-XX/graph.toon         — persistent graph copy
    .vrs/ground-truth/cal-XX-graph-stats.json   — validator-compatible flat format
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Project root — script expects to be run from the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ground truth output directory
GROUND_TRUTH_DIR = PROJECT_ROOT / ".vrs" / "ground-truth"

# Calibration contract definitions with semantic metadata.
# Function names are verified against actual .sol source files.
CALIBRATION_CONTRACTS = {
    "cal-01": {
        "path": "tests/contracts/ReentrancyClassic.sol",
        "name": "ReentrancyClassic",
        "expected_vulnerability_class": "reentrancy",
        "semantic_fingerprint": "CEI_violation_withdraw",
        "function_names": ["deposit", "withdraw"],
        "has_external_calls": True,
        "has_state_modification_after_call": True,
    },
    "cal-02": {
        "path": "tests/contracts/NoAccessGate.sol",
        "name": "NoAccessGate",
        "expected_vulnerability_class": "access-control",
        "semantic_fingerprint": "missing_access_gate_setOwner",
        "function_names": ["setOwner"],
        "has_external_calls": False,
        "has_state_modification_after_call": False,
    },
    "cal-03": {
        "path": "tests/contracts/OracleNoStaleness.sol",
        "name": "OracleNoStaleness",
        "expected_vulnerability_class": "oracle-manipulation",
        "semantic_fingerprint": "oracle_no_staleness_check",
        "function_names": ["getPrice"],
        "has_external_calls": True,
        "has_state_modification_after_call": False,
    },
    "cal-04": {
        "path": "tests/contracts/TxOriginAuth.sol",
        "name": "TxOriginAuth",
        "expected_vulnerability_class": "access-control",
        "semantic_fingerprint": "tx_origin_auth_privileged",
        "function_names": ["privileged"],
        "has_external_calls": False,
        "has_state_modification_after_call": False,
    },
}


def build_graph(contract_path: Path, out_dir: Path) -> subprocess.CompletedProcess:
    """Run build-kg for a single contract."""
    cmd = [
        "uv",
        "run",
        "alphaswarm",
        "build-kg",
        str(contract_path),
        "--out",
        str(out_dir),
        "--force",
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=120,
    )


def parse_build_output(stdout: str, stderr: str) -> dict:
    """Parse build-kg stdout/stderr for nodes, edges, identity, and graph path.

    The build-kg command outputs structured log lines. We need:
    - nodes=N and edges=N from the vkg_build_complete line
    - identity: HASH from the summary line
    - VKG saved to: PATH from the output line
    """
    combined = stdout + "\n" + stderr

    # Parse nodes and edges from log line: "edges=17 nodes=12"
    nodes_match = re.search(r"nodes=(\d+)", combined)
    edges_match = re.search(r"edges=(\d+)", combined)

    # Parse identity hash
    identity_match = re.search(r"identity:\s*(\w+)", combined)

    # Parse graph path
    graph_path_match = re.search(r"VKG saved to:\s*(.+\.toon)", combined)

    nodes = int(nodes_match.group(1)) if nodes_match else 0
    edges = int(edges_match.group(1)) if edges_match else 0
    identity = identity_match.group(1) if identity_match else "unknown"
    graph_path = graph_path_match.group(1).strip() if graph_path_match else ""

    return {
        "nodes": nodes,
        "edges": edges,
        "identity": identity,
        "graph_path": graph_path,
    }


def generate_ground_truth() -> bool:
    """Generate ground truth for all calibration contracts.

    Returns True if all contracts built successfully, False otherwise.
    """
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    failures: list[str] = []

    for cal_id, meta in CALIBRATION_CONTRACTS.items():
        contract_path = PROJECT_ROOT / meta["path"]

        # Validate contract exists
        if not contract_path.exists():
            print(f"WARNING: {cal_id} contract not found at {contract_path} — skipping")
            failures.append(cal_id)
            continue

        print(f"\n{'='*60}")
        print(f"Building {cal_id}: {meta['name']} ({meta['path']})")
        print(f"{'='*60}")

        # Build graph in a temp directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = build_graph(contract_path, Path(tmp_dir))

            if result.returncode != 0:
                print(f"ERROR: build-kg failed for {cal_id}")
                print(f"  stdout: {result.stdout}")
                print(f"  stderr: {result.stderr}")
                failures.append(cal_id)
                continue

            # Parse build output
            parsed = parse_build_output(result.stdout, result.stderr)

            if parsed["nodes"] == 0:
                print(f"ERROR: No nodes parsed from build output for {cal_id}")
                print(f"  stdout: {result.stdout}")
                print(f"  stderr: {result.stderr}")
                failures.append(cal_id)
                continue

            # Locate graph.toon in the build output
            source_graph = Path(parsed["graph_path"]) if parsed["graph_path"] else None
            if not source_graph or not source_graph.exists():
                # Fallback: search in temp directory for graph.toon
                toon_files = list(Path(tmp_dir).rglob("graph.toon"))
                if toon_files:
                    source_graph = toon_files[0]
                else:
                    print(f"ERROR: No graph.toon found for {cal_id}")
                    failures.append(cal_id)
                    continue

            # Create output directory for this contract
            cal_dir = GROUND_TRUTH_DIR / cal_id
            cal_dir.mkdir(parents=True, exist_ok=True)

            # Copy graph.toon to persistent location
            persistent_graph = cal_dir / "graph.toon"
            shutil.copy2(str(source_graph), str(persistent_graph))

            # Build stats.json with semantic metadata
            built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            stats = {
                "contract": meta["name"],
                "contract_id": cal_id,
                "contract_path": meta["path"],
                "built_at": built_at,
                "identity": parsed["identity"],
                "nodes": parsed["nodes"],
                "edges": parsed["edges"],
                "graph_path": str(persistent_graph.resolve()),
                "expected_vulnerability_class": meta["expected_vulnerability_class"],
                "semantic_fingerprint": meta["semantic_fingerprint"],
                "function_names": meta["function_names"],
                "has_external_calls": meta["has_external_calls"],
                "has_state_modification_after_call": meta["has_state_modification_after_call"],
            }

            # Write stats.json (subdirectory format for human/module consumption)
            stats_path = cal_dir / "stats.json"
            stats_path.write_text(json.dumps(stats, indent=2) + "\n")

            # Write validator-compatible flat format:
            # ground_truth_dir / "{contract_id}-graph-stats.json"
            flat_stats_path = GROUND_TRUTH_DIR / f"{cal_id}-graph-stats.json"
            flat_stats_path.write_text(json.dumps(stats, indent=2) + "\n")

            print(f"  nodes={parsed['nodes']}, edges={parsed['edges']}")
            print(f"  identity={parsed['identity']}")
            print(f"  graph_path={persistent_graph.resolve()}")
            print(f"  vuln_class={meta['expected_vulnerability_class']}")
            print(f"  stats.json -> {stats_path}")
            print(f"  graph-stats.json -> {flat_stats_path}")

            results.append(stats)

    # Print summary
    print(f"\n{'='*60}")
    print("GROUND TRUTH GENERATION SUMMARY")
    print(f"{'='*60}")
    print(f"{'Contract ID':<12} {'Nodes':<8} {'Edges':<8} {'Vuln Class':<22} {'Graph Path'}")
    print("-" * 90)
    for s in results:
        print(
            f"{s['contract_id']:<12} {s['nodes']:<8} {s['edges']:<8} "
            f"{s['expected_vulnerability_class']:<22} {s['graph_path']}"
        )

    if failures:
        print(f"\nFAILED contracts: {', '.join(failures)}")
        return False

    print(f"\nAll {len(results)} contracts built successfully.")
    return True


if __name__ == "__main__":
    success = generate_ground_truth()
    sys.exit(0 if success else 1)
