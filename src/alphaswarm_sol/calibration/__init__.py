"""Phase 14: Confidence Calibration System.

This module provides confidence calibration for VKG findings so that
"80% confidence" means approximately 80% true positive rate.

Key components:
- CalibrationDataset: Load and manage ground truth data
- PatternCalibrator: Per-pattern confidence calibration (extends learning/bounds.py)
- ContextFactors: Adjust confidence based on guards and mitigations
- CalibrationPlotter: Generate reliability diagrams
- ConfidenceExplainer: Generate human-readable explanations
- CalibrationValidator: Measure calibration quality (Brier score, ECE)

Architecture:
- Builds on existing `learning/bounds.py` (Wilson score, Bayesian updating)
- Uses existing `benchmarks/confidence_bounds.json` for per-pattern bounds
- Adds optional isotonic/Platt calibrators for patterns with sufficient data

Usage:
    from alphaswarm_sol.calibration import (
        CalibrationDataset,
        PatternCalibrator,
        ContextFactors,
        CalibrationValidator,
        calibrate_finding,
        explain_confidence,
    )

    # Load existing bounds
    calibrator = PatternCalibrator.from_bounds_file("benchmarks/confidence_bounds.json")

    # Calibrate a finding
    calibrated_confidence = calibrator.calibrate(
        pattern_id="vm-001-classic",
        raw_confidence=0.8,
        context_factors={"has_reentrancy_guard": True}
    )

    # Get explanation
    explanation = explain_confidence(calibrated_confidence, "vm-001-classic")
"""

from alphaswarm_sol.calibration.dataset import (
    CalibrationDataset,
    LabeledFinding,
    Label,
    load_benchmark_data,
)
from alphaswarm_sol.calibration.calibrator import (
    PatternCalibrator,
    CalibratorConfig,
    CalibrationMethod,
    calibrate_finding,
)
from alphaswarm_sol.calibration.context import (
    ContextFactors,
    ContextConfig,
    apply_context_factors,
    GUARD_MULTIPLIERS,
)
from alphaswarm_sol.calibration.visualization import (
    CalibrationPlotter,
    plot_reliability_diagram,
    plot_confidence_histogram,
    plot_before_after,
)
from alphaswarm_sol.calibration.explanation import (
    ConfidenceExplainer,
    ConfidenceExplanation,
    explain_confidence,
    format_explanation,
)
from alphaswarm_sol.calibration.validation import (
    CalibrationValidator,
    CalibrationMetrics,
    brier_score,
    expected_calibration_error,
    validate_calibration,
)

__all__ = [
    # Dataset
    "CalibrationDataset",
    "LabeledFinding",
    "Label",
    "load_benchmark_data",
    # Calibrator
    "PatternCalibrator",
    "CalibratorConfig",
    "CalibrationMethod",
    "calibrate_finding",
    # Context
    "ContextFactors",
    "ContextConfig",
    "apply_context_factors",
    "GUARD_MULTIPLIERS",
    # Visualization
    "CalibrationPlotter",
    "plot_reliability_diagram",
    "plot_confidence_histogram",
    "plot_before_after",
    # Explanation
    "ConfidenceExplainer",
    "ConfidenceExplanation",
    "explain_confidence",
    "format_explanation",
    # Validation
    "CalibrationValidator",
    "CalibrationMetrics",
    "brier_score",
    "expected_calibration_error",
    "validate_calibration",
]
