#!/usr/bin/env python3
"""
Import CGT (Consolidated Ground Truth) dataset as external ground truth.

This script imports contracts and vulnerability labels from the CGT repository.
All ground truth comes from academic research papers - NO manual labels.

Per VALIDATION-RULES.md rule B1: External Ground Truth Required

CGT integrates ground truth from:
- CodeSmells, ContractFuzzer, Doublade, eThor, EthRacer
- Ever Evolving Game, JiuZhou, Not So Smart Contracts
- NPChecker, SmartBugs curated, SolidiFI, SWC registry, Zeus
"""

import csv
import shutil
import yaml
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def main():
    """Import CGT dataset."""
    # Paths
    cgt_repo = Path("/tmp/cgt")
    corpus_dir = Path("/Volumes/ex_ssd/home/projects/python/vkg-solidity/true-vkg/.vrs/corpus")
    contracts_dest = corpus_dir / "contracts" / "cgt"
    ground_truth_dest = corpus_dir / "ground-truth" / "cgt"

    # Ensure directories exist
    contracts_dest.mkdir(parents=True, exist_ok=True)
    ground_truth_dest.mkdir(parents=True, exist_ok=True)

    # Commit hash for provenance
    commit_hash = "f8cd72cf7fbbfebc809c454667eee271706a4b2b"

    # Map CGT properties to categories and SWC IDs
    property_mapping = {
        # Reentrancy variants
        "Reentrancy": {"swc": "SWC-107", "category": "reentrancy", "severity": "critical"},
        "reentrancy": {"swc": "SWC-107", "category": "reentrancy", "severity": "critical"},
        # Integer overflow
        "Int_overflow": {"swc": "SWC-101", "category": "arithmetic", "severity": "high"},
        "Overflow-Underflow": {"swc": "SWC-101", "category": "arithmetic", "severity": "high"},
        # Unchecked calls
        "Unchkd_send": {"swc": "SWC-104", "category": "unchecked_calls", "severity": "high"},
        "Failed_send": {"swc": "SWC-104", "category": "unchecked_calls", "severity": "high"},
        "Unchecked External Call": {"swc": "SWC-104", "category": "unchecked_calls", "severity": "high"},
        # Access control
        "Access Control": {"swc": "SWC-105", "category": "access_control", "severity": "high"},
        "access-control": {"swc": "SWC-105", "category": "access_control", "severity": "high"},
        # State dependencies
        "Tx_State_Dep": {"swc": "SWC-115", "category": "tx_origin", "severity": "medium"},
        "Transaction state Dependency": {"swc": "SWC-115", "category": "tx_origin", "severity": "medium"},
        "Blk_State_Dep": {"swc": "SWC-116", "category": "time_manipulation", "severity": "medium"},
        "Block Info Dependency": {"swc": "SWC-116", "category": "time_manipulation", "severity": "medium"},
        "Tx_Order_Dep": {"swc": "SWC-114", "category": "front_running", "severity": "medium"},
        # DoS
        "Dos Under external influence": {"swc": "SWC-113", "category": "denial_of_service", "severity": "medium"},
        # Other
        "Compiler Version not fixed": {"swc": "SWC-103", "category": "code_quality", "severity": "low"},
    }

    # Parse consolidated.csv
    contracts_data = defaultdict(lambda: {"findings": [], "datasets": set()})

    with open(cgt_repo / "consolidated.csv", newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            # Only include entries where property_holds is 't' (true - vulnerability confirmed)
            if row.get('property_holds') != 't':
                continue

            prop = row.get('property', '')
            if prop not in property_mapping:
                continue

            # Get source file hash
            fp_sol = row.get('fp_sol', '')
            if not fp_sol:
                continue

            source_file = cgt_repo / "source" / f"{fp_sol}.sol"
            if not source_file.exists():
                continue

            mapping = property_mapping[prop]
            finding = {
                "property": prop,
                "swc_id": mapping["swc"],
                "category": mapping["category"],
                "severity": mapping["severity"],
                "dataset": row.get('dataset', 'unknown'),
                "chain_address": row.get('addr', ''),
                "contract_name": row.get('contractname', ''),
                "provenance": {
                    "source": "CGT",
                    "external_label": True,
                    "dataset_origin": row.get('dataset', ''),
                    "paper_citation": "Consolidation of Ground Truth Sets for Weakness Detection in Smart Contracts (arXiv:2304.11624)",
                }
            }

            contracts_data[fp_sol]["findings"].append(finding)
            contracts_data[fp_sol]["datasets"].add(row.get('dataset', ''))
            contracts_data[fp_sol]["source_file"] = source_file

    # Sample contracts: take top contracts by number of findings (diverse ground truth)
    # Limit to 50 to keep corpus manageable
    sorted_contracts = sorted(
        contracts_data.items(),
        key=lambda x: len(x[1]["findings"]),
        reverse=True
    )[:50]

    # Copy contracts and build ground truth
    contracts = []
    total_findings = 0
    category_stats = defaultdict(lambda: {"contracts": 0, "findings": 0})

    for fp_sol, data in sorted_contracts:
        source_file = data.get("source_file")
        if not source_file:
            continue

        # Copy contract
        dest_file = contracts_dest / f"{fp_sol}.sol"
        shutil.copy(source_file, dest_file)

        # Deduplicate findings by category
        seen_categories = set()
        unique_findings = []
        for finding in data["findings"]:
            key = (finding["category"], finding["swc_id"])
            if key not in seen_categories:
                seen_categories.add(key)
                unique_findings.append(finding)

        contracts.append({
            "path": f"cgt/{fp_sol}.sol",
            "file_hash": fp_sol,
            "datasets": list(data["datasets"]),
            "findings": unique_findings,
        })

        # Update statistics
        for finding in unique_findings:
            cat = finding["category"]
            category_stats[cat]["findings"] += 1
            total_findings += 1

        for cat in seen_categories:
            category_stats[cat[0]]["contracts"] += 1

    # Create ground truth YAML
    ground_truth = {
        "metadata": {
            "source": "CGT",
            "repository": "https://github.com/gsalzer/cgt",
            "commit": commit_hash,
            "imported_date": datetime.now(timezone.utc).isoformat(),
            "description": "Consolidated Ground Truth for Weaknesses of Ethereum Smart Contracts",
            "paper": "https://arxiv.org/pdf/2304.11624",
            "citation": "Consolidation of Ground Truth Sets for Weakness Detection in Smart Contracts",
            "integrated_datasets": [
                "CodeSmells", "ContractFuzzer", "Doublade", "eThor", "EthRacer",
                "Ever Evolving Game", "JiuZhou", "Not So Smart Contracts",
                "NPChecker", "SmartBugs curated", "SolidiFI", "SWC registry", "Zeus"
            ],
            "external_ground_truth": True,
            "no_manual_labels": True,
        },
        "statistics": {
            "total_contracts": len(contracts),
            "total_findings": total_findings,
            "by_category": dict(category_stats),
        },
        "contracts": contracts,
    }

    # Write ground truth YAML
    output_file = ground_truth_dest / "consolidated.yaml"
    with open(output_file, "w") as f:
        yaml.dump(ground_truth, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"CGT import complete:")
    print(f"  - Contracts imported: {len(contracts)}")
    print(f"  - Total findings: {total_findings}")
    print(f"  - Categories: {list(category_stats.keys())}")
    print(f"  - Ground truth file: {output_file}")
    print(f"  - Commit hash: {commit_hash}")


if __name__ == "__main__":
    main()
