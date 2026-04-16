"""Task 14.1: Ground Truth Dataset Management.

Loads and manages labeled findings for calibration training and validation.
Uses existing benchmark data from DVDeFi, SmartBugs, and pattern tests.

Philosophy:
- Build on existing `benchmarks/confidence_bounds.json`
- Don't require new labeling - use existing benchmark results
- Support incremental updates as more data becomes available
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class Label(str, Enum):
    """Ground truth labels for findings."""
    TRUE_POSITIVE = "tp"       # Confirmed vulnerability
    FALSE_POSITIVE = "fp"      # Not a vulnerability
    UNCERTAIN = "uncertain"    # Needs human review
    OUT_OF_SCOPE = "oos"       # VKG can't detect this type


@dataclass
class LabeledFinding:
    """A finding with ground truth label.

    Used for calibration training and validation.
    """
    finding_id: str
    pattern_id: str
    raw_confidence: float
    label: Label
    file: str = ""
    line: int = 0
    function: Optional[str] = None
    contract: Optional[str] = None
    source: str = "unknown"  # dvdefi, smartbugs, manual, etc.
    labeled_at: Optional[datetime] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "finding_id": self.finding_id,
            "pattern_id": self.pattern_id,
            "raw_confidence": self.raw_confidence,
            "label": self.label.value,
            "file": self.file,
            "line": self.line,
            "function": self.function,
            "contract": self.contract,
            "source": self.source,
            "labeled_at": self.labeled_at.isoformat() if self.labeled_at else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LabeledFinding":
        """Create from dictionary."""
        labeled_at = None
        if data.get("labeled_at"):
            labeled_at = datetime.fromisoformat(data["labeled_at"])

        return cls(
            finding_id=data["finding_id"],
            pattern_id=data["pattern_id"],
            raw_confidence=data.get("raw_confidence", 0.5),
            label=Label(data["label"]),
            file=data.get("file", ""),
            line=data.get("line", 0),
            function=data.get("function"),
            contract=data.get("contract"),
            source=data.get("source", "unknown"),
            labeled_at=labeled_at,
            notes=data.get("notes", ""),
        )


@dataclass
class PatternStats:
    """Statistics for a single pattern."""
    pattern_id: str
    true_positives: int = 0
    false_positives: int = 0
    uncertain: int = 0
    out_of_scope: int = 0

    @property
    def total_labeled(self) -> int:
        """Total findings with labels (excluding uncertain/oos)."""
        return self.true_positives + self.false_positives

    @property
    def precision(self) -> float:
        """Precision (TP / (TP + FP))."""
        if self.total_labeled == 0:
            return 0.0
        return self.true_positives / self.total_labeled


class CalibrationDataset:
    """Dataset of labeled findings for calibration.

    Loads from multiple sources:
    - benchmarks/confidence_bounds.json (pattern-level stats)
    - DVDeFi benchmark results
    - Manual labeling files

    Example:
        dataset = CalibrationDataset()
        dataset.load_from_bounds("benchmarks/confidence_bounds.json")

        # Get stats for a pattern
        stats = dataset.get_pattern_stats("vm-001-classic")
        print(f"Precision: {stats.precision:.2%}")

        # Split for training/validation
        train, val = dataset.split(train_ratio=0.8)
    """

    def __init__(self):
        self._findings: List[LabeledFinding] = []
        self._pattern_stats: Dict[str, PatternStats] = {}

    def __len__(self) -> int:
        return len(self._findings)

    def add(self, finding: LabeledFinding) -> None:
        """Add a labeled finding."""
        self._findings.append(finding)
        self._update_stats(finding)

    def _update_stats(self, finding: LabeledFinding) -> None:
        """Update pattern statistics."""
        pattern_id = finding.pattern_id
        if pattern_id not in self._pattern_stats:
            self._pattern_stats[pattern_id] = PatternStats(pattern_id=pattern_id)

        stats = self._pattern_stats[pattern_id]
        if finding.label == Label.TRUE_POSITIVE:
            stats.true_positives += 1
        elif finding.label == Label.FALSE_POSITIVE:
            stats.false_positives += 1
        elif finding.label == Label.UNCERTAIN:
            stats.uncertain += 1
        elif finding.label == Label.OUT_OF_SCOPE:
            stats.out_of_scope += 1

    def load_from_bounds(self, bounds_path: Path | str) -> int:
        """Load pattern statistics from confidence_bounds.json.

        This file contains aggregated TP/FP counts per pattern.
        We synthesize labeled findings from the counts.

        Args:
            bounds_path: Path to confidence_bounds.json

        Returns:
            Number of patterns loaded
        """
        bounds_path = Path(bounds_path)
        if not bounds_path.exists():
            return 0

        with open(bounds_path) as f:
            data = json.load(f)

        loaded = 0
        for pattern_id, bounds_data in data.items():
            sample_size = bounds_data.get("sample_size", 0)
            observed_precision = bounds_data.get("observed_precision", 0.5)

            if sample_size == 0:
                continue

            # Compute TP/FP counts from precision and sample size
            tp_count = int(round(sample_size * observed_precision))
            fp_count = sample_size - tp_count

            # Create synthetic labeled findings
            for i in range(tp_count):
                self.add(LabeledFinding(
                    finding_id=f"{pattern_id}-tp-{i}",
                    pattern_id=pattern_id,
                    raw_confidence=bounds_data.get("initial", 0.7),
                    label=Label.TRUE_POSITIVE,
                    source="benchmark",
                ))

            for i in range(fp_count):
                self.add(LabeledFinding(
                    finding_id=f"{pattern_id}-fp-{i}",
                    pattern_id=pattern_id,
                    raw_confidence=bounds_data.get("initial", 0.7),
                    label=Label.FALSE_POSITIVE,
                    source="benchmark",
                ))

            loaded += 1

        return loaded

    def load_from_json(self, json_path: Path | str) -> int:
        """Load labeled findings from JSON file.

        Args:
            json_path: Path to JSON file with labeled findings

        Returns:
            Number of findings loaded
        """
        json_path = Path(json_path)
        if not json_path.exists():
            return 0

        with open(json_path) as f:
            data = json.load(f)

        findings = data if isinstance(data, list) else data.get("findings", [])

        loaded = 0
        for item in findings:
            finding = LabeledFinding.from_dict(item)
            self.add(finding)
            loaded += 1

        return loaded

    def save_to_json(self, json_path: Path | str) -> None:
        """Save labeled findings to JSON file."""
        json_path = Path(json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "generated_at": datetime.now().isoformat(),
            "total_findings": len(self._findings),
            "pattern_count": len(self._pattern_stats),
            "findings": [f.to_dict() for f in self._findings],
        }

        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_pattern_stats(self, pattern_id: str) -> PatternStats:
        """Get statistics for a pattern."""
        return self._pattern_stats.get(
            pattern_id,
            PatternStats(pattern_id=pattern_id)
        )

    def get_all_patterns(self) -> Set[str]:
        """Get all pattern IDs in the dataset."""
        return set(self._pattern_stats.keys())

    def get_findings_for_pattern(self, pattern_id: str) -> List[LabeledFinding]:
        """Get all findings for a pattern."""
        return [f for f in self._findings if f.pattern_id == pattern_id]

    def filter_by_source(self, source: str) -> "CalibrationDataset":
        """Create new dataset filtered by source."""
        dataset = CalibrationDataset()
        for f in self._findings:
            if f.source == source:
                dataset.add(f)
        return dataset

    def filter_by_labels(self, labels: Set[Label]) -> "CalibrationDataset":
        """Create new dataset filtered by labels."""
        dataset = CalibrationDataset()
        for f in self._findings:
            if f.label in labels:
                dataset.add(f)
        return dataset

    def split(
        self,
        train_ratio: float = 0.8,
        seed: int = 42,
    ) -> tuple["CalibrationDataset", "CalibrationDataset"]:
        """Split dataset into training and validation sets.

        Stratified by pattern to maintain per-pattern representation.

        Args:
            train_ratio: Ratio for training set
            seed: Random seed for reproducibility

        Returns:
            (train_dataset, val_dataset) tuple
        """
        import random
        random.seed(seed)

        train = CalibrationDataset()
        val = CalibrationDataset()

        # Group by pattern
        by_pattern: Dict[str, List[LabeledFinding]] = {}
        for f in self._findings:
            if f.pattern_id not in by_pattern:
                by_pattern[f.pattern_id] = []
            by_pattern[f.pattern_id].append(f)

        # Split each pattern's findings
        for pattern_id, findings in by_pattern.items():
            random.shuffle(findings)
            split_idx = int(len(findings) * train_ratio)

            for f in findings[:split_idx]:
                train.add(f)
            for f in findings[split_idx:]:
                val.add(f)

        return train, val

    def summary(self) -> str:
        """Generate summary of the dataset."""
        lines = [
            "Calibration Dataset Summary",
            "=" * 50,
            f"Total findings: {len(self._findings)}",
            f"Patterns: {len(self._pattern_stats)}",
            "",
            "Label Distribution:",
        ]

        total_tp = sum(s.true_positives for s in self._pattern_stats.values())
        total_fp = sum(s.false_positives for s in self._pattern_stats.values())
        total_unc = sum(s.uncertain for s in self._pattern_stats.values())

        lines.extend([
            f"  True Positives: {total_tp}",
            f"  False Positives: {total_fp}",
            f"  Uncertain: {total_unc}",
            "",
            "Per-Pattern Stats (top 10 by sample size):",
        ])

        # Sort patterns by sample size
        sorted_patterns = sorted(
            self._pattern_stats.values(),
            key=lambda s: s.total_labeled,
            reverse=True
        )[:10]

        for stats in sorted_patterns:
            lines.append(
                f"  {stats.pattern_id}: n={stats.total_labeled}, "
                f"precision={stats.precision:.2%}"
            )

        return "\n".join(lines)


def load_benchmark_data(
    bounds_path: Path | str = "benchmarks/confidence_bounds.json",
) -> CalibrationDataset:
    """Convenience function to load benchmark data.

    Args:
        bounds_path: Path to confidence bounds file

    Returns:
        Loaded CalibrationDataset
    """
    dataset = CalibrationDataset()
    dataset.load_from_bounds(bounds_path)
    return dataset
