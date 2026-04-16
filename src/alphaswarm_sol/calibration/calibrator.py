"""Task 14.2 & 14.3: Pattern Calibrator.

Extends the existing learning/bounds.py infrastructure to provide
comprehensive calibration with optional isotonic/Platt methods.

Philosophy:
- Default to Bayesian updating (already proven in bounds.py)
- Add isotonic/Platt as optional enhancements for patterns with n >= 30
- Per-pattern calibration with global fallback
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Import existing infrastructure
from alphaswarm_sol.learning.bounds import (
    BoundsManager,
    bayesian_confidence,
    wilson_score_interval,
    calculate_bounds,
)
from alphaswarm_sol.learning.types import ConfidenceBounds, PatternBaseline
from alphaswarm_sol.calibration.dataset import CalibrationDataset, Label


class CalibrationMethod(str, Enum):
    """Available calibration methods."""
    BAYESIAN = "bayesian"      # Default - Bayesian updating
    ISOTONIC = "isotonic"      # Non-parametric, needs n >= 30
    PLATT = "platt"            # Logistic, needs n >= 20
    HISTOGRAM = "histogram"    # Binning-based


@dataclass
class CalibratorConfig:
    """Configuration for the pattern calibrator."""
    default_method: CalibrationMethod = CalibrationMethod.BAYESIAN
    min_samples_for_isotonic: int = 30
    min_samples_for_platt: int = 20
    min_samples_for_per_pattern: int = 5
    absolute_min: float = 0.05
    absolute_max: float = 0.98
    prior_strength: float = 2.0
    prior_probability: float = 0.5


@dataclass
class CalibrationResult:
    """Result of calibrating a confidence value."""
    pattern_id: str
    raw_confidence: float
    calibrated_confidence: float
    method_used: CalibrationMethod
    bounds_used: Optional[ConfidenceBounds] = None
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "raw_confidence": round(self.raw_confidence, 4),
            "calibrated_confidence": round(self.calibrated_confidence, 4),
            "method_used": self.method_used.value,
            "explanation": self.explanation,
        }


class PatternCalibrator:
    """Per-pattern confidence calibrator.

    Builds on existing BoundsManager from learning/bounds.py
    and adds optional isotonic/Platt calibrators.

    Example:
        calibrator = PatternCalibrator.from_bounds_file(
            "benchmarks/confidence_bounds.json"
        )

        # Calibrate a confidence value
        result = calibrator.calibrate("vm-001-classic", 0.8)
        print(f"Calibrated: {result.calibrated_confidence}")

        # Train advanced calibrators from dataset
        calibrator.train_from_dataset(dataset)
    """

    def __init__(
        self,
        config: Optional[CalibratorConfig] = None,
        bounds_manager: Optional[BoundsManager] = None,
    ):
        """Initialize calibrator.

        Args:
            config: Calibrator configuration
            bounds_manager: Existing bounds manager (optional)
        """
        self.config = config or CalibratorConfig()
        self._bounds_manager = bounds_manager or BoundsManager(
            absolute_min=self.config.absolute_min,
            absolute_max=self.config.absolute_max,
        )

        # Optional advanced calibrators (trained from data)
        self._isotonic_calibrators: Dict[str, Any] = {}
        self._platt_calibrators: Dict[str, Any] = {}

        # Pattern sample counts (for method selection)
        self._pattern_samples: Dict[str, int] = {}

    @classmethod
    def from_bounds_file(
        cls,
        bounds_path: Path | str,
        config: Optional[CalibratorConfig] = None,
    ) -> "PatternCalibrator":
        """Create calibrator from existing bounds file.

        Args:
            bounds_path: Path to confidence_bounds.json
            config: Optional configuration

        Returns:
            Initialized PatternCalibrator
        """
        config = config or CalibratorConfig()
        bounds_path = Path(bounds_path)

        bounds_manager = BoundsManager(
            bounds_path=bounds_path,
            absolute_min=config.absolute_min,
            absolute_max=config.absolute_max,
        )

        calibrator = cls(config=config, bounds_manager=bounds_manager)

        # Extract sample counts from bounds
        if bounds_path.exists():
            with open(bounds_path) as f:
                data = json.load(f)
            for pattern_id, bounds_data in data.items():
                calibrator._pattern_samples[pattern_id] = bounds_data.get("sample_size", 0)

        return calibrator

    def calibrate(
        self,
        pattern_id: str,
        raw_confidence: float,
        method: Optional[CalibrationMethod] = None,
    ) -> CalibrationResult:
        """Calibrate a confidence value for a pattern.

        Args:
            pattern_id: Pattern identifier
            raw_confidence: Raw confidence from pattern matching
            method: Override calibration method (optional)

        Returns:
            CalibrationResult with calibrated confidence
        """
        # Select method based on available data
        if method is None:
            method = self._select_method(pattern_id)

        # Get bounds for the pattern
        bounds = self._bounds_manager.get(pattern_id)

        # Calibrate based on method
        if method == CalibrationMethod.ISOTONIC and pattern_id in self._isotonic_calibrators:
            calibrated = self._apply_isotonic(pattern_id, raw_confidence)
            explanation = f"Isotonic calibration (n={self._pattern_samples.get(pattern_id, 0)})"
        elif method == CalibrationMethod.PLATT and pattern_id in self._platt_calibrators:
            calibrated = self._apply_platt(pattern_id, raw_confidence)
            explanation = f"Platt scaling (n={self._pattern_samples.get(pattern_id, 0)})"
        else:
            # Default: Bayesian with bounds
            calibrated = self._apply_bayesian(pattern_id, raw_confidence, bounds)
            explanation = f"Bayesian calibration with bounds [{bounds.lower_bound:.2f}, {bounds.upper_bound:.2f}]"

        # Ensure within absolute bounds
        calibrated = max(self.config.absolute_min, min(self.config.absolute_max, calibrated))

        return CalibrationResult(
            pattern_id=pattern_id,
            raw_confidence=raw_confidence,
            calibrated_confidence=calibrated,
            method_used=method,
            bounds_used=bounds,
            explanation=explanation,
        )

    def _select_method(self, pattern_id: str) -> CalibrationMethod:
        """Select best calibration method for a pattern."""
        samples = self._pattern_samples.get(pattern_id, 0)

        if samples >= self.config.min_samples_for_isotonic and pattern_id in self._isotonic_calibrators:
            return CalibrationMethod.ISOTONIC
        elif samples >= self.config.min_samples_for_platt and pattern_id in self._platt_calibrators:
            return CalibrationMethod.PLATT
        else:
            return CalibrationMethod.BAYESIAN

    def _apply_bayesian(
        self,
        pattern_id: str,
        raw_confidence: float,
        bounds: ConfidenceBounds,
    ) -> float:
        """Apply Bayesian calibration using bounds.

        Maps raw confidence through observed precision.
        """
        # Use observed precision as the calibration target
        observed = bounds.observed_precision if bounds.observed_precision > 0 else bounds.initial

        # Blend raw confidence with observed precision based on sample size
        samples = self._pattern_samples.get(pattern_id, 0)

        # More samples = trust observed more
        if samples >= 30:
            weight = 0.8  # Strong trust in observed
        elif samples >= 10:
            weight = 0.6  # Moderate trust
        elif samples >= 5:
            weight = 0.4  # Weak trust
        else:
            weight = 0.2  # Mostly use raw

        calibrated = weight * observed + (1 - weight) * raw_confidence

        # Clamp to bounds
        return bounds.clamp(calibrated)

    def _apply_isotonic(self, pattern_id: str, raw_confidence: float) -> float:
        """Apply isotonic regression calibration."""
        if pattern_id not in self._isotonic_calibrators:
            return raw_confidence

        calibrator = self._isotonic_calibrators[pattern_id]
        # IsotonicRegression.transform expects 2D array
        calibrated = calibrator.transform([[raw_confidence]])[0]
        return float(calibrated)

    def _apply_platt(self, pattern_id: str, raw_confidence: float) -> float:
        """Apply Platt scaling calibration."""
        if pattern_id not in self._platt_calibrators:
            return raw_confidence

        calibrator = self._platt_calibrators[pattern_id]
        # LogisticRegression.predict_proba expects 2D array
        proba = calibrator.predict_proba([[raw_confidence]])[0, 1]
        return float(proba)

    def train_from_dataset(
        self,
        dataset: CalibrationDataset,
        patterns: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Train advanced calibrators from labeled dataset.

        Args:
            dataset: CalibrationDataset with labeled findings
            patterns: Optional list of patterns to train (all if None)

        Returns:
            Dict mapping pattern_id to training status message
        """
        try:
            from sklearn.isotonic import IsotonicRegression
            from sklearn.linear_model import LogisticRegression
        except ImportError:
            return {"error": "sklearn not installed - using Bayesian only"}

        patterns = patterns or list(dataset.get_all_patterns())
        results = {}

        for pattern_id in patterns:
            findings = dataset.get_findings_for_pattern(pattern_id)

            # Filter to only TP/FP findings
            labeled = [f for f in findings if f.label in {Label.TRUE_POSITIVE, Label.FALSE_POSITIVE}]

            if len(labeled) < self.config.min_samples_for_per_pattern:
                results[pattern_id] = f"Skipped: only {len(labeled)} samples"
                continue

            # Extract X (confidences) and y (labels)
            X = np.array([[f.raw_confidence] for f in labeled])
            y = np.array([1 if f.label == Label.TRUE_POSITIVE else 0 for f in labeled])

            self._pattern_samples[pattern_id] = len(labeled)

            # Train isotonic if enough samples
            if len(labeled) >= self.config.min_samples_for_isotonic:
                try:
                    isotonic = IsotonicRegression(out_of_bounds="clip")
                    isotonic.fit(X.ravel(), y)
                    self._isotonic_calibrators[pattern_id] = isotonic
                    results[pattern_id] = f"Trained isotonic (n={len(labeled)})"
                except Exception as e:
                    results[pattern_id] = f"Isotonic failed: {e}"
                    continue

            # Train Platt if enough samples but not enough for isotonic
            elif len(labeled) >= self.config.min_samples_for_platt:
                try:
                    platt = LogisticRegression(solver="lbfgs", max_iter=1000)
                    platt.fit(X, y)
                    self._platt_calibrators[pattern_id] = platt
                    results[pattern_id] = f"Trained Platt (n={len(labeled)})"
                except Exception as e:
                    results[pattern_id] = f"Platt failed: {e}"
                    continue
            else:
                results[pattern_id] = f"Using Bayesian (n={len(labeled)})"

        return results

    def update_bounds(self, bounds: ConfidenceBounds) -> None:
        """Update bounds for a pattern."""
        self._bounds_manager.set(bounds)
        if bounds.sample_size:
            self._pattern_samples[bounds.pattern_id] = bounds.sample_size

    def get_bounds(self, pattern_id: str) -> ConfidenceBounds:
        """Get bounds for a pattern."""
        return self._bounds_manager.get(pattern_id)

    def save(self, path: Path | str) -> None:
        """Save calibrator state to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "config": {
                "default_method": self.config.default_method.value,
                "min_samples_for_isotonic": self.config.min_samples_for_isotonic,
                "min_samples_for_platt": self.config.min_samples_for_platt,
                "min_samples_for_per_pattern": self.config.min_samples_for_per_pattern,
                "absolute_min": self.config.absolute_min,
                "absolute_max": self.config.absolute_max,
            },
            "pattern_samples": self._pattern_samples,
            "bounds": {
                pid: b.to_dict()
                for pid, b in self._bounds_manager.all_bounds().items()
            },
        }

        # Save sklearn calibrators separately (pickle)
        if self._isotonic_calibrators or self._platt_calibrators:
            pkl_path = path.with_suffix(".pkl")
            with open(pkl_path, "wb") as f:
                pickle.dump({
                    "isotonic": self._isotonic_calibrators,
                    "platt": self._platt_calibrators,
                }, f)
            state["sklearn_path"] = str(pkl_path)

        with open(path, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> "PatternCalibrator":
        """Load calibrator from file."""
        path = Path(path)

        with open(path) as f:
            state = json.load(f)

        config = CalibratorConfig(
            default_method=CalibrationMethod(state["config"]["default_method"]),
            min_samples_for_isotonic=state["config"]["min_samples_for_isotonic"],
            min_samples_for_platt=state["config"]["min_samples_for_platt"],
            min_samples_for_per_pattern=state["config"]["min_samples_for_per_pattern"],
            absolute_min=state["config"]["absolute_min"],
            absolute_max=state["config"]["absolute_max"],
        )

        calibrator = cls(config=config)
        calibrator._pattern_samples = state["pattern_samples"]

        # Load bounds
        for pattern_id, bounds_data in state.get("bounds", {}).items():
            bounds = ConfidenceBounds.from_dict(bounds_data)
            calibrator._bounds_manager.set(bounds)

        # Load sklearn calibrators if present
        sklearn_path = state.get("sklearn_path")
        if sklearn_path and Path(sklearn_path).exists():
            with open(sklearn_path, "rb") as f:
                sklearn_data = pickle.load(f)
            calibrator._isotonic_calibrators = sklearn_data.get("isotonic", {})
            calibrator._platt_calibrators = sklearn_data.get("platt", {})

        return calibrator

    def summary(self) -> str:
        """Generate summary of calibrator state."""
        lines = [
            "Pattern Calibrator Summary",
            "=" * 50,
            f"Patterns with bounds: {len(self._bounds_manager.all_bounds())}",
            f"Isotonic calibrators: {len(self._isotonic_calibrators)}",
            f"Platt calibrators: {len(self._platt_calibrators)}",
            "",
            "Method distribution:",
        ]

        bayesian_count = 0
        isotonic_count = 0
        platt_count = 0

        for pattern_id in self._pattern_samples:
            method = self._select_method(pattern_id)
            if method == CalibrationMethod.ISOTONIC:
                isotonic_count += 1
            elif method == CalibrationMethod.PLATT:
                platt_count += 1
            else:
                bayesian_count += 1

        lines.extend([
            f"  Bayesian: {bayesian_count}",
            f"  Isotonic: {isotonic_count}",
            f"  Platt: {platt_count}",
        ])

        return "\n".join(lines)


def calibrate_finding(
    pattern_id: str,
    raw_confidence: float,
    calibrator: Optional[PatternCalibrator] = None,
    bounds_path: Optional[Path | str] = None,
) -> CalibrationResult:
    """Convenience function to calibrate a single finding.

    Args:
        pattern_id: Pattern identifier
        raw_confidence: Raw confidence value
        calibrator: Optional pre-loaded calibrator
        bounds_path: Optional path to bounds file

    Returns:
        CalibrationResult
    """
    if calibrator is None:
        if bounds_path is None:
            bounds_path = Path("benchmarks/confidence_bounds.json")
        calibrator = PatternCalibrator.from_bounds_file(bounds_path)

    return calibrator.calibrate(pattern_id, raw_confidence)
