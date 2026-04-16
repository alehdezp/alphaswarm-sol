#!/usr/bin/env python3
"""
Capture regression baseline from current GA metrics.

Usage:
    uv run python scripts/capture_baseline.py --metrics .vrs/ga-metrics/aggregated-metrics.json
    uv run python scripts/capture_baseline.py --metrics .vrs/ga-metrics/aggregated-metrics.json --output .vrs/baselines/ga-baseline.json
"""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def get_git_info() -> Dict[str, str]:
    """Get current git commit and branch info."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        # Get commit date
        commit_date = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci"],
            stderr=subprocess.DEVNULL
        ).decode().strip()

        # Check for dirty state
        dirty = subprocess.call(
            ["git", "diff", "--quiet"],
            stderr=subprocess.DEVNULL
        ) != 0

        return {
            "commit": commit,
            "branch": branch,
            "commit_date": commit_date,
            "dirty": dirty,
        }
    except subprocess.CalledProcessError:
        return {
            "commit": "unknown",
            "branch": "unknown",
            "commit_date": "unknown",
            "dirty": True,
        }


def get_version_info() -> Dict[str, str]:
    """Get AlphaSwarm version info."""
    try:
        # Try to get version from pyproject.toml
        pyproject = Path("pyproject.toml")
        if pyproject.exists():
            content = pyproject.read_text()
            for line in content.split("\n"):
                if line.strip().startswith("version"):
                    # Extract version = "x.x.x"
                    version = line.split("=")[1].strip().strip('"')
                    return {"alphaswarm_version": version}
    except Exception:
        pass

    return {"alphaswarm_version": "unknown"}


def create_baseline(metrics_file: Path) -> Dict[str, Any]:
    """Create baseline from aggregated metrics."""
    if not metrics_file.exists():
        raise FileNotFoundError(f"Metrics file not found: {metrics_file}")

    metrics = json.loads(metrics_file.read_text())

    # Validate metrics meet GA targets
    if metrics.get("overall_precision", 0) < 0.70:
        print(f"WARNING: Precision {metrics['overall_precision']:.2%} below target 70%")

    if metrics.get("overall_recall", 0) < 0.60:
        print(f"WARNING: Recall {metrics['overall_recall']:.2%} below target 60%")

    baseline = {
        "baseline_type": "ga-release",
        "created_at": datetime.now().isoformat(),
        "git": get_git_info(),
        "version": get_version_info(),
        "metrics": {
            "precision": metrics["overall_precision"],
            "recall": metrics["overall_recall"],
            "f1_score": metrics["overall_f1"],
            "true_positives": metrics["total_true_positives"],
            "false_positives": metrics["total_false_positives"],
            "false_negatives": metrics["total_false_negatives"],
            "tests_count": metrics["total_tests"],
            "total_duration_ms": metrics["total_duration_ms"],
        },
        "by_vulnerability_type": metrics.get("by_vulnerability_type", {}),
        "by_ground_truth_source": metrics.get("by_ground_truth_source", {}),
        "regression_thresholds": {
            "precision_max_drop": 0.05,  # Max 5% precision drop allowed
            "recall_max_drop": 0.05,     # Max 5% recall drop allowed
            "f1_max_drop": 0.05,         # Max 5% F1 drop allowed
        },
        "tests": [
            {
                "test_id": t["test_id"],
                "fixture": t["fixture"],
                "precision": t["precision"],
                "recall": t["recall"],
                "f1_score": t["f1_score"],
            }
            for t in metrics.get("tests", [])
        ],
    }

    return baseline


def validate_baseline(baseline: Dict[str, Any]) -> bool:
    """Validate baseline has required data."""
    required_metrics = ["precision", "recall", "f1_score"]
    for metric in required_metrics:
        if metric not in baseline.get("metrics", {}):
            print(f"ERROR: Missing metric: {metric}")
            return False

    if baseline["metrics"]["precision"] < 0.5:
        print(f"WARNING: Low precision baseline: {baseline['metrics']['precision']:.2%}")

    if baseline["metrics"]["recall"] < 0.4:
        print(f"WARNING: Low recall baseline: {baseline['metrics']['recall']:.2%}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Capture regression baseline")
    parser.add_argument("--metrics", required=True, help="Path to aggregated metrics JSON")
    parser.add_argument("--output", default=".vrs/baselines/ga-baseline.json",
                        help="Output baseline file")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing baseline")
    args = parser.parse_args()

    metrics_file = Path(args.metrics)
    output_file = Path(args.output)

    # Check if baseline already exists
    if output_file.exists() and not args.force:
        print(f"ERROR: Baseline already exists: {output_file}")
        print("Use --force to overwrite")
        exit(1)

    # Create baseline
    print(f"Creating baseline from: {metrics_file}")
    baseline = create_baseline(metrics_file)

    # Validate
    if not validate_baseline(baseline):
        print("ERROR: Baseline validation failed")
        exit(1)

    # Write baseline
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(baseline, indent=2))

    print(f"Baseline saved to: {output_file}")
    print()
    print("BASELINE SUMMARY")
    print("----------------")
    print(f"Commit:      {baseline['git']['commit'][:8]}...")
    print(f"Branch:      {baseline['git']['branch']}")
    print(f"Version:     {baseline['version']['alphaswarm_version']}")
    print(f"Precision:   {baseline['metrics']['precision']:.2%}")
    print(f"Recall:      {baseline['metrics']['recall']:.2%}")
    print(f"F1 Score:    {baseline['metrics']['f1_score']:.2%}")
    print(f"Tests:       {baseline['metrics']['tests_count']}")


if __name__ == "__main__":
    main()
