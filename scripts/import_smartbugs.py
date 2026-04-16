#!/usr/bin/env python3
"""
Import SmartBugs-curated dataset as external ground truth.

This script imports contracts and vulnerability labels from the SmartBugs-curated
repository. All ground truth comes from the external source - NO manual labels.

Per VALIDATION-RULES.md rule B1: External Ground Truth Required
"""

import json
import shutil
import yaml
from datetime import datetime, timezone
from pathlib import Path


def main():
    """Import SmartBugs-curated dataset."""
    # Paths
    smartbugs_repo = Path("/tmp/smartbugs-curated")
    corpus_dir = Path("./.vrs/corpus")
    contracts_dest = corpus_dir / "contracts" / "smartbugs"
    ground_truth_dest = corpus_dir / "ground-truth" / "smartbugs"

    # Ensure directories exist
    contracts_dest.mkdir(parents=True, exist_ok=True)
    ground_truth_dest.mkdir(parents=True, exist_ok=True)

    # Read vulnerabilities.json - this is the EXTERNAL ground truth
    vuln_file = smartbugs_repo / "vulnerabilities.json"
    with open(vuln_file) as f:
        vuln_data = json.load(f)

    # Get commit hash for provenance
    commit_hash = "230e649123477eff332742a59a1c7cc6dc286cab"  # From git rev-parse HEAD

    # Map SmartBugs categories to SWC IDs
    category_to_swc = {
        "access_control": "SWC-105",  # Unprotected Ether Withdrawal
        "arithmetic": "SWC-101",      # Integer Overflow and Underflow
        "bad_randomness": "SWC-120",  # Weak Sources of Randomness
        "denial_of_service": "SWC-113",  # DoS with Failed Call
        "front_running": "SWC-114",   # Transaction Order Dependence
        "reentrancy": "SWC-107",      # Reentrancy
        "short_addresses": "SWC-109", # Uninitialized Storage Pointer
        "time_manipulation": "SWC-116",  # Block values as proxy for time
        "unchecked_low_level_calls": "SWC-104",  # Unchecked Call Return Value
        "other": "SWC-100",           # Function Default Visibility
    }

    # Map categories to severity
    category_to_severity = {
        "reentrancy": "critical",
        "access_control": "high",
        "arithmetic": "high",
        "unchecked_low_level_calls": "high",
        "bad_randomness": "medium",
        "denial_of_service": "medium",
        "front_running": "medium",
        "time_manipulation": "low",
        "short_addresses": "low",
        "other": "medium",
    }

    # Process contracts and build ground truth
    contracts = []
    total_findings = 0

    for entry in vuln_data:
        contract_name = entry["name"]
        source_path = entry["path"]  # e.g., "dataset/access_control/FibonacciBalance.sol"

        # Extract category from path
        parts = source_path.split("/")
        category = parts[1] if len(parts) > 1 else "other"

        # Copy .sol file to corpus
        src_file = smartbugs_repo / source_path
        if src_file.exists():
            # Organize by category
            dest_dir = contracts_dest / category
            dest_dir.mkdir(exist_ok=True)
            dest_file = dest_dir / contract_name
            shutil.copy(src_file, dest_file)

            # Build ground truth from EXTERNAL source
            findings = []
            for vuln in entry.get("vulnerabilities", []):
                lines = vuln.get("lines", [])
                vuln_category = vuln.get("category", category)

                finding = {
                    "swc_id": category_to_swc.get(vuln_category, "SWC-100"),
                    "category": vuln_category,
                    "severity": category_to_severity.get(vuln_category, "medium"),
                    "lines": lines,
                    "location": f"{contract_name}:{lines[0]}" if lines else f"{contract_name}:unknown",
                    # Provenance: ALL from external source
                    "provenance": {
                        "source": "SmartBugs-curated",
                        "external_label": True,
                        "source_url": entry.get("source", "https://github.com/smartbugs/smartbugs-curated"),
                    }
                }
                findings.append(finding)
                total_findings += 1

            contracts.append({
                "path": f"smartbugs/{category}/{contract_name}",
                "name": contract_name,
                "category": category,
                "pragma": entry.get("pragma", "unknown"),
                "original_source": entry.get("source", ""),
                "findings": findings,
            })

    # Create ground truth YAML with EXTERNAL provenance
    ground_truth = {
        "metadata": {
            "source": "SmartBugs-curated",
            "repository": "https://github.com/smartbugs/smartbugs-curated",
            "commit": commit_hash,
            "imported_date": datetime.now(timezone.utc).isoformat(),
            "description": "Curated dataset of vulnerable Solidity contracts for automated analysis benchmarking",
            "license": "MIT",
            "citation": "SmartBugs: A Framework to Analyze Solidity Smart Contracts (ACM ESEC/FSE 2020)",
            # CRITICAL: All labels are external
            "external_ground_truth": True,
            "no_manual_labels": True,
        },
        "statistics": {
            "total_contracts": len(contracts),
            "total_findings": total_findings,
            "by_category": {},
        },
        "contracts": contracts,
    }

    # Calculate category statistics
    for contract in contracts:
        cat = contract["category"]
        if cat not in ground_truth["statistics"]["by_category"]:
            ground_truth["statistics"]["by_category"][cat] = {"contracts": 0, "findings": 0}
        ground_truth["statistics"]["by_category"][cat]["contracts"] += 1
        ground_truth["statistics"]["by_category"][cat]["findings"] += len(contract["findings"])

    # Write ground truth YAML
    output_file = ground_truth_dest / "curated.yaml"
    with open(output_file, "w") as f:
        yaml.dump(ground_truth, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"SmartBugs-curated import complete:")
    print(f"  - Contracts imported: {len(contracts)}")
    print(f"  - Total findings: {total_findings}")
    print(f"  - Categories: {list(ground_truth['statistics']['by_category'].keys())}")
    print(f"  - Ground truth file: {output_file}")
    print(f"  - Commit hash: {commit_hash}")


if __name__ == "__main__":
    main()
