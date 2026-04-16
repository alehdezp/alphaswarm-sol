"""Bootstrap data generation from existing benchmarks.

Task 7.0: Generate initial confidence bounds and baseline metrics
from existing test projects and their MANIFEST.yaml ground truth files.

This provides the foundation for learning:
- Per-pattern precision/recall/F1
- Per-pattern confidence bounds
- Baseline for measuring learning improvement
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from alphaswarm_sol.learning.types import PatternBaseline, ConfidenceBounds
from alphaswarm_sol.learning.bounds import calculate_bounds


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a MANIFEST.yaml file.

    Args:
        path: Path to MANIFEST.yaml

    Returns:
        Parsed manifest dict
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)


class BootstrapGenerator:
    """Generate bootstrap data from test projects.

    Reads MANIFEST.yaml files from test projects to extract
    ground truth data and compute baseline metrics.
    """

    # Minimum sample size for reliable bounds
    MIN_SAMPLES = 5

    # Default bounds when insufficient data
    DEFAULT_LOWER = 0.30
    DEFAULT_UPPER = 0.95
    DEFAULT_INITIAL = 0.70

    def __init__(
        self,
        test_projects_path: Path,
        patterns_path: Path | None = None,
    ):
        """Initialize bootstrap generator.

        Args:
            test_projects_path: Path to tests/projects directory
            patterns_path: Path to patterns directory (optional)
        """
        self.test_projects = test_projects_path
        self.patterns_path = patterns_path

    def generate_baselines(self) -> dict[str, PatternBaseline]:
        """Generate baseline metrics for all patterns from manifests.

        Returns:
            Dict mapping pattern_id to PatternBaseline
        """
        baselines: dict[str, PatternBaseline] = {}
        pattern_data: dict[str, dict[str, int]] = {}

        # Find all MANIFEST.yaml files
        for manifest_path in self.test_projects.glob("**/MANIFEST.yaml"):
            try:
                manifest = load_manifest(manifest_path)
                self._extract_pattern_data(manifest, pattern_data)
            except Exception as e:
                print(f"Warning: Failed to load {manifest_path}: {e}")
                continue

        # Convert to PatternBaseline objects
        for pattern_id, data in pattern_data.items():
            tp = data.get("true_positives", 0)
            fp = data.get("false_positives", 0)
            fn = data.get("false_negatives", 0)

            total_tp_fp = tp + fp
            total_tp_fn = tp + fn

            precision = tp / total_tp_fp if total_tp_fp > 0 else 0.5
            recall = tp / total_tp_fn if total_tp_fn > 0 else 0.5
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            baselines[pattern_id] = PatternBaseline(
                pattern_id=pattern_id,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                precision=round(precision, 4),
                recall=round(recall, 4),
                f1_score=round(f1, 4),
                sample_size=tp + fp + fn,
                source="manifest",
            )

        return baselines

    def _extract_pattern_data(
        self,
        manifest: dict[str, Any],
        pattern_data: dict[str, dict[str, int]],
    ) -> None:
        """Extract pattern metrics from a manifest.

        The manifest has a 'patterns' section with structure:
        patterns:
          pattern-id:
            functions:
              vulnerable: [list of vulnerable functions]
              safe: [list of safe functions]
              false_positives: [list of FPs]
              false_negatives: [list of FNs]
            metrics:
              precision: 0.xx
              recall: 0.xx
        """
        patterns_section = manifest.get("patterns", {})

        # Handle both single 'patterns:' key and multiple 'patterns:' keys
        # (YAML allows this, resulting in dict with last value)
        if isinstance(patterns_section, dict):
            for pattern_id, pattern_info in patterns_section.items():
                if not isinstance(pattern_info, dict):
                    continue

                if pattern_id not in pattern_data:
                    pattern_data[pattern_id] = {
                        "true_positives": 0,
                        "false_positives": 0,
                        "false_negatives": 0,
                    }

                functions = pattern_info.get("functions", {})

                # Count vulnerable functions as expected TPs
                vulnerable = functions.get("vulnerable", [])
                if vulnerable:
                    pattern_data[pattern_id]["true_positives"] += len(vulnerable)

                # Count explicit false positives
                fps = functions.get("false_positives", [])
                if fps:
                    pattern_data[pattern_id]["false_positives"] += len(fps)

                # Count explicit false negatives
                fns = functions.get("false_negatives", [])
                if fns:
                    pattern_data[pattern_id]["false_negatives"] += len(fns)

                # If metrics are provided directly, use them to adjust counts
                metrics = pattern_info.get("metrics", {})
                if metrics:
                    # Metrics can provide more accurate data if available
                    pass  # For now, use function counts

    def generate_confidence_bounds(
        self,
        baselines: dict[str, PatternBaseline],
    ) -> dict[str, ConfidenceBounds]:
        """Generate confidence bounds from baselines.

        Args:
            baselines: Dict of pattern baselines

        Returns:
            Dict mapping pattern_id to ConfidenceBounds
        """
        bounds: dict[str, ConfidenceBounds] = {}

        for pattern_id, baseline in baselines.items():
            bounds[pattern_id] = calculate_bounds(baseline)

        return bounds

    def save_baselines(
        self,
        baselines: dict[str, PatternBaseline],
        output_path: Path,
    ) -> None:
        """Save baselines to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            pattern_id: baseline.to_dict()
            for pattern_id, baseline in baselines.items()
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_confidence_bounds(
        self,
        bounds: dict[str, ConfidenceBounds],
        output_path: Path,
    ) -> None:
        """Save confidence bounds to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            pattern_id: b.to_dict()
            for pattern_id, b in bounds.items()
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_baselines(self, path: Path) -> dict[str, PatternBaseline]:
        """Load baselines from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)

        return {
            pattern_id: PatternBaseline.from_dict(baseline_data)
            for pattern_id, baseline_data in data.items()
        }

    def load_confidence_bounds(self, path: Path) -> dict[str, ConfidenceBounds]:
        """Load confidence bounds from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)

        return {
            pattern_id: ConfidenceBounds.from_dict(bounds_data)
            for pattern_id, bounds_data in data.items()
        }


def generate_bootstrap_data(
    test_projects: Path,
    patterns: Path | None,
    output_dir: Path,
) -> tuple[dict[str, PatternBaseline], dict[str, ConfidenceBounds]]:
    """Generate all bootstrap data.

    Main entry point for Task 7.0.

    Args:
        test_projects: Path to tests/projects directory
        patterns: Path to patterns directory (optional)
        output_dir: Directory to save output files

    Returns:
        Tuple of (baselines dict, bounds dict)

    Usage:
        from alphaswarm_sol.vulndocs.resolution import vulndocs_read_path_as_path
        baselines, bounds = generate_bootstrap_data(
            Path("tests/projects"),
            vulndocs_read_path_as_path(),
            Path("benchmarks")
        )
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = BootstrapGenerator(test_projects, patterns)

    print("Generating baselines from MANIFEST.yaml files...")
    baselines = generator.generate_baselines()
    baseline_path = output_dir / "pattern_baseline.json"
    generator.save_baselines(baselines, baseline_path)
    print(f"  Saved {len(baselines)} pattern baselines to {baseline_path}")

    print("Generating confidence bounds...")
    bounds = generator.generate_confidence_bounds(baselines)
    bounds_path = output_dir / "confidence_bounds.json"
    generator.save_confidence_bounds(bounds, bounds_path)
    print(f"  Saved {len(bounds)} confidence bounds to {bounds_path}")

    # Print summary
    print("\nBootstrap Summary:")
    print("-" * 50)
    for pattern_id in sorted(baselines.keys()):
        baseline = baselines[pattern_id]
        bound = bounds[pattern_id]
        print(
            f"  {pattern_id}: precision={baseline.precision:.2f}, "
            f"recall={baseline.recall:.2f}, "
            f"bounds=[{bound.lower_bound:.2f}, {bound.upper_bound:.2f}]"
        )

    print("\nBootstrap complete!")
    return baselines, bounds


# CLI entry point
if __name__ == "__main__":
    import sys

    from alphaswarm_sol.vulndocs.resolution import vulndocs_read_path_as_path

    test_projects = Path("tests/projects")
    patterns = vulndocs_read_path_as_path()
    output_dir = Path("benchmarks")

    if len(sys.argv) > 1:
        test_projects = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    generate_bootstrap_data(test_projects, patterns, output_dir)
