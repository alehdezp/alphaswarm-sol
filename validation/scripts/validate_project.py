#!/usr/bin/env python3
"""Validate VKG detection against project ground truth.

Usage:
    python validate_project.py <project_name>
    python validate_project.py --all
    python validate_project.py --list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from alphaswarm_sol.validation.ground_truth import (
    ProjectGroundTruth,
    VKGFinding,
    FindingMatcher,
    format_validation_report,
)


VALIDATION_DIR = Path(__file__).parent.parent
GROUND_TRUTH_DIR = VALIDATION_DIR / "ground-truth"
RESULTS_DIR = VALIDATION_DIR / "results"


def list_projects() -> List[str]:
    """List available ground truth projects."""
    projects = []
    for path in GROUND_TRUTH_DIR.glob("*.yaml"):
        projects.append(path.stem)
    return sorted(projects)


def load_ground_truth(project_name: str) -> Optional[ProjectGroundTruth]:
    """Load ground truth for a project."""
    path = GROUND_TRUTH_DIR / f"{project_name}.yaml"
    if not path.exists():
        print(f"Error: Ground truth not found: {path}")
        return None
    return ProjectGroundTruth.load(path)


def load_vkg_findings(project_name: str) -> List[VKGFinding]:
    """Load VKG findings for a project.

    In production, this would run VKG on the project.
    For now, it loads from a pre-generated JSON file.
    """
    findings_path = RESULTS_DIR / project_name / "vkg-findings.json"

    if not findings_path.exists():
        print(f"Warning: No VKG findings file found at {findings_path}")
        print("Run VKG on the project first to generate findings.")
        return []

    try:
        with open(findings_path) as f:
            data = json.load(f)

        findings = []
        for item in data.get("findings", data if isinstance(data, list) else []):
            findings.append(VKGFinding.from_pattern_match(item))

        return findings

    except Exception as e:
        print(f"Error loading VKG findings: {e}")
        return []


def validate_project(project_name: str, verbose: bool = True) -> dict:
    """Validate VKG against a project's ground truth.

    Args:
        project_name: Project to validate
        verbose: Print detailed output

    Returns:
        Validation metrics dict
    """
    # Load ground truth
    ground_truth = load_ground_truth(project_name)
    if not ground_truth:
        return {"error": "Ground truth not found"}

    if verbose:
        print(f"\nValidating: {ground_truth.project_name}")
        print(f"  Type: {ground_truth.project_type}")
        print(f"  Audit: {ground_truth.audit_source} ({ground_truth.audit_date})")
        print(f"  Total findings: {ground_truth.total_findings}")
        print(f"  VKG-detectable: {len(ground_truth.vkg_detectable_findings)}")

    # Load VKG findings
    vkg_findings = load_vkg_findings(project_name)

    if verbose:
        print(f"  VKG findings: {len(vkg_findings)}")

    if not vkg_findings:
        # Return metrics for no findings
        return {
            "project": project_name,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": len(ground_truth.vkg_detectable_findings),
            "note": "No VKG findings - run VKG on project first",
        }

    # Run matching
    matcher = FindingMatcher(line_tolerance=10)
    result = matcher.validate_project(ground_truth, vkg_findings)

    # Save results
    results_dir = RESULTS_DIR / project_name
    results_dir.mkdir(parents=True, exist_ok=True)
    result.save(results_dir / "validation-result.json")

    if verbose:
        print("\n" + format_validation_report(result))

    return result.to_dict()["metrics"]


def validate_all(verbose: bool = True) -> dict:
    """Validate all projects with ground truth."""
    projects = list_projects()
    results = {}

    print(f"Found {len(projects)} projects with ground truth")

    for project in projects:
        metrics = validate_project(project, verbose=verbose)
        results[project] = metrics

    # Aggregate metrics
    total_tp = sum(r.get("true_positives", 0) for r in results.values())
    total_fp = sum(r.get("false_positives", 0) for r in results.values())
    total_fn = sum(r.get("false_negatives", 0) for r in results.values())

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    aggregate = {
        "projects": len(projects),
        "total_precision": round(precision, 4),
        "total_recall": round(recall, 4),
        "total_f1": round(f1, 4),
        "total_true_positives": total_tp,
        "total_false_positives": total_fp,
        "total_false_negatives": total_fn,
        "per_project": results,
    }

    # Save aggregate
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "aggregate-metrics.json", "w") as f:
        json.dump(aggregate, f, indent=2)

    print("\n" + "=" * 60)
    print("AGGREGATE METRICS")
    print("=" * 60)
    print(f"  Projects validated: {len(projects)}")
    print(f"  Total Precision: {precision:.1%}")
    print(f"  Total Recall: {recall:.1%}")
    print(f"  Total F1 Score: {f1:.1%}")
    print(f"  Total TP: {total_tp}")
    print(f"  Total FP: {total_fp}")
    print(f"  Total FN: {total_fn}")

    return aggregate


def main():
    parser = argparse.ArgumentParser(description="Validate VKG against ground truth")
    parser.add_argument("project", nargs="?", help="Project name to validate")
    parser.add_argument("--all", action="store_true", help="Validate all projects")
    parser.add_argument("--list", action="store_true", help="List available projects")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")

    args = parser.parse_args()

    if args.list:
        projects = list_projects()
        print("Available projects with ground truth:")
        for p in projects:
            print(f"  - {p}")
        return

    if args.all:
        validate_all(verbose=not args.quiet)
        return

    if args.project:
        validate_project(args.project, verbose=not args.quiet)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
