"""Task 14.5: Calibration Visualization.

Generates reliability diagrams and other visualizations to
assess calibration quality.

Philosophy:
- Visual validation is essential - numbers lie, plots don't
- Near-diagonal reliability curve = well calibrated
- Show before/after to demonstrate improvement
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class CalibrationBin:
    """A single bin in the reliability diagram."""
    bin_lower: float
    bin_upper: float
    bin_center: float
    avg_predicted: float
    avg_actual: float
    count: int
    calibration_error: float  # |predicted - actual|


@dataclass
class ReliabilityData:
    """Data for a reliability diagram."""
    bins: List[CalibrationBin]
    n_samples: int
    expected_calibration_error: float
    max_calibration_error: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "n_samples": self.n_samples,
            "expected_calibration_error": round(self.expected_calibration_error, 4),
            "max_calibration_error": round(self.max_calibration_error, 4),
            "bins": [
                {
                    "range": f"[{b.bin_lower:.2f}, {b.bin_upper:.2f})",
                    "center": b.bin_center,
                    "avg_predicted": round(b.avg_predicted, 4),
                    "avg_actual": round(b.avg_actual, 4),
                    "count": b.count,
                    "error": round(b.calibration_error, 4),
                }
                for b in self.bins
            ],
        }


class CalibrationPlotter:
    """Generate calibration visualizations.

    Example:
        plotter = CalibrationPlotter()

        # Add data points (predicted confidence, actual outcome)
        for finding in findings:
            actual = 1 if finding.is_true_positive else 0
            plotter.add_point(finding.confidence, actual)

        # Generate reliability diagram
        plotter.plot_reliability("calibration_curve.png")

        # Get data without plotting
        data = plotter.compute_reliability()
        print(f"ECE: {data.expected_calibration_error:.4f}")
    """

    def __init__(self, n_bins: int = 10):
        """Initialize plotter.

        Args:
            n_bins: Number of bins for reliability diagram
        """
        self.n_bins = n_bins
        self._predicted: List[float] = []
        self._actual: List[int] = []

    def add_point(self, predicted: float, actual: int) -> None:
        """Add a calibration data point.

        Args:
            predicted: Predicted probability (confidence)
            actual: Actual outcome (1 for TP, 0 for FP)
        """
        self._predicted.append(predicted)
        self._actual.append(actual)

    def add_points(
        self,
        predicted: List[float],
        actual: List[int],
    ) -> None:
        """Add multiple data points."""
        self._predicted.extend(predicted)
        self._actual.extend(actual)

    def clear(self) -> None:
        """Clear all data points."""
        self._predicted = []
        self._actual = []

    def compute_reliability(self) -> ReliabilityData:
        """Compute reliability diagram data without plotting.

        Returns:
            ReliabilityData with bin statistics
        """
        if len(self._predicted) == 0:
            return ReliabilityData(
                bins=[],
                n_samples=0,
                expected_calibration_error=0.0,
                max_calibration_error=0.0,
            )

        predicted = np.array(self._predicted)
        actual = np.array(self._actual)

        # Create bins
        bin_boundaries = np.linspace(0, 1, self.n_bins + 1)
        bins: List[CalibrationBin] = []

        weighted_error_sum = 0.0
        max_error = 0.0
        total_count = 0

        for i in range(self.n_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]
            bin_center = (bin_lower + bin_upper) / 2

            # Find points in this bin
            in_bin = (predicted >= bin_lower) & (predicted < bin_upper)

            if i == self.n_bins - 1:
                # Include upper bound in last bin
                in_bin = (predicted >= bin_lower) & (predicted <= bin_upper)

            count = np.sum(in_bin)

            if count > 0:
                avg_predicted = np.mean(predicted[in_bin])
                avg_actual = np.mean(actual[in_bin])
                calibration_error = abs(avg_predicted - avg_actual)

                weighted_error_sum += calibration_error * count
                max_error = max(max_error, calibration_error)
                total_count += count
            else:
                avg_predicted = bin_center
                avg_actual = 0.0
                calibration_error = 0.0

            bins.append(CalibrationBin(
                bin_lower=bin_lower,
                bin_upper=bin_upper,
                bin_center=bin_center,
                avg_predicted=avg_predicted,
                avg_actual=avg_actual,
                count=int(count),
                calibration_error=calibration_error,
            ))

        ece = weighted_error_sum / total_count if total_count > 0 else 0.0

        return ReliabilityData(
            bins=bins,
            n_samples=len(predicted),
            expected_calibration_error=ece,
            max_calibration_error=max_error,
        )

    def plot_reliability(
        self,
        output_path: Optional[Path | str] = None,
        title: str = "Reliability Diagram",
        show_histogram: bool = True,
    ) -> Optional[Any]:
        """Generate reliability diagram.

        Args:
            output_path: Path to save plot (None to return figure)
            title: Plot title
            show_histogram: Show sample count histogram

        Returns:
            matplotlib Figure if output_path is None
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        data = self.compute_reliability()

        if show_histogram:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10), gridspec_kw={"height_ratios": [3, 1]})
        else:
            fig, ax1 = plt.subplots(1, 1, figsize=(8, 6))
            ax2 = None

        # Main reliability diagram
        bin_centers = [b.bin_center for b in data.bins]
        avg_actual = [b.avg_actual for b in data.bins]
        counts = [b.count for b in data.bins]

        # Perfect calibration line
        ax1.plot([0, 1], [0, 1], "k--", label="Perfect calibration", alpha=0.7)

        # Reliability curve (only bins with data)
        valid_bins = [(c, a) for c, a, n in zip(bin_centers, avg_actual, counts) if n > 0]
        if valid_bins:
            centers, actuals = zip(*valid_bins)
            ax1.plot(centers, actuals, "o-", color="blue", label="Model calibration", markersize=8)

        ax1.set_xlim([0, 1])
        ax1.set_ylim([0, 1])
        ax1.set_xlabel("Predicted Probability (Confidence)")
        ax1.set_ylabel("Fraction of True Positives")
        ax1.set_title(f"{title}\nECE = {data.expected_calibration_error:.4f}")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)

        # Sample histogram
        if ax2 is not None:
            ax2.bar(bin_centers, counts, width=1.0 / self.n_bins, edgecolor="black", alpha=0.7)
            ax2.set_xlim([0, 1])
            ax2.set_xlabel("Predicted Probability")
            ax2.set_ylabel("Count")
            ax2.set_title("Sample Distribution")
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()
            return None

        return fig

    def plot_histogram(
        self,
        output_path: Optional[Path | str] = None,
        title: str = "Confidence Distribution",
    ) -> Optional[Any]:
        """Plot histogram of confidence values.

        Args:
            output_path: Path to save plot
            title: Plot title

        Returns:
            matplotlib Figure if output_path is None
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        fig, ax = plt.subplots(figsize=(8, 5))

        predicted = np.array(self._predicted)
        actual = np.array(self._actual)

        # Separate by outcome
        tp_conf = predicted[actual == 1]
        fp_conf = predicted[actual == 0]

        bins = np.linspace(0, 1, self.n_bins + 1)

        ax.hist(tp_conf, bins=bins, alpha=0.6, label=f"True Positives (n={len(tp_conf)})", color="green")
        ax.hist(fp_conf, bins=bins, alpha=0.6, label=f"False Positives (n={len(fp_conf)})", color="red")

        ax.set_xlabel("Confidence")
        ax.set_ylabel("Count")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()
            return None

        return fig


def plot_reliability_diagram(
    predicted: List[float],
    actual: List[int],
    output_path: Optional[Path | str] = None,
    title: str = "Reliability Diagram",
    n_bins: int = 10,
) -> ReliabilityData:
    """Convenience function to plot reliability diagram.

    Args:
        predicted: List of predicted probabilities
        actual: List of actual outcomes (0 or 1)
        output_path: Path to save plot
        title: Plot title
        n_bins: Number of bins

    Returns:
        ReliabilityData with statistics
    """
    plotter = CalibrationPlotter(n_bins=n_bins)
    plotter.add_points(predicted, actual)

    if output_path:
        plotter.plot_reliability(output_path, title)

    return plotter.compute_reliability()


def plot_confidence_histogram(
    predicted: List[float],
    actual: List[int],
    output_path: Optional[Path | str] = None,
    title: str = "Confidence Distribution",
    n_bins: int = 10,
) -> None:
    """Convenience function to plot confidence histogram.

    Args:
        predicted: List of predicted probabilities
        actual: List of actual outcomes
        output_path: Path to save plot
        title: Plot title
        n_bins: Number of bins
    """
    plotter = CalibrationPlotter(n_bins=n_bins)
    plotter.add_points(predicted, actual)
    plotter.plot_histogram(output_path, title)


def plot_before_after(
    before_predicted: List[float],
    after_predicted: List[float],
    actual: List[int],
    output_path: Optional[Path | str] = None,
    n_bins: int = 10,
) -> Tuple[ReliabilityData, ReliabilityData]:
    """Plot before/after calibration comparison.

    Args:
        before_predicted: Pre-calibration predictions
        after_predicted: Post-calibration predictions
        actual: Actual outcomes
        output_path: Path to save plot
        n_bins: Number of bins

    Returns:
        Tuple of (before_data, after_data)
    """
    before_plotter = CalibrationPlotter(n_bins=n_bins)
    before_plotter.add_points(before_predicted, actual)
    before_data = before_plotter.compute_reliability()

    after_plotter = CalibrationPlotter(n_bins=n_bins)
    after_plotter.add_points(after_predicted, actual)
    after_data = after_plotter.compute_reliability()

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return before_data, after_data

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Before
    ax1.plot([0, 1], [0, 1], "k--", label="Perfect", alpha=0.7)
    valid_before = [(b.bin_center, b.avg_actual) for b in before_data.bins if b.count > 0]
    if valid_before:
        centers, actuals = zip(*valid_before)
        ax1.plot(centers, actuals, "o-", color="red", label="Before calibration", markersize=8)
    ax1.set_xlim([0, 1])
    ax1.set_ylim([0, 1])
    ax1.set_xlabel("Predicted Probability")
    ax1.set_ylabel("Fraction of True Positives")
    ax1.set_title(f"Before Calibration\nECE = {before_data.expected_calibration_error:.4f}")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # After
    ax2.plot([0, 1], [0, 1], "k--", label="Perfect", alpha=0.7)
    valid_after = [(b.bin_center, b.avg_actual) for b in after_data.bins if b.count > 0]
    if valid_after:
        centers, actuals = zip(*valid_after)
        ax2.plot(centers, actuals, "o-", color="green", label="After calibration", markersize=8)
    ax2.set_xlim([0, 1])
    ax2.set_ylim([0, 1])
    ax2.set_xlabel("Predicted Probability")
    ax2.set_ylabel("Fraction of True Positives")
    ax2.set_title(f"After Calibration\nECE = {after_data.expected_calibration_error:.4f}")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.suptitle("Calibration Comparison", fontsize=14, fontweight="bold")
    plt.tight_layout()

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

    return before_data, after_data
