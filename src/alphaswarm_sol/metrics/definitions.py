"""Metric definitions with thresholds and data sources.

Task 8.1: Define 8 key metrics with explicit data sources.

Each metric has:
- Formula for calculation
- Target and alert thresholds
- Data sources (where the input data comes from)
- Phase dependencies (what must be complete to calculate this metric)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .types import MetricName, MetricValue


@dataclass
class MetricDefinition:
    """Definition of a VKG metric."""

    name: MetricName
    formula: str
    description: str
    target: float
    threshold_warning: float
    threshold_critical: float
    unit: str
    higher_is_better: bool
    data_sources: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # Phase dependencies

    def create_value(self, value: float) -> MetricValue:
        """Create a MetricValue from this definition."""
        return MetricValue(
            name=self.name,
            value=value,
            target=self.target,
            threshold_warning=self.threshold_warning,
            threshold_critical=self.threshold_critical,
            unit=self.unit,
        )


# The 8 metric definitions
METRIC_DEFINITIONS: dict[MetricName, MetricDefinition] = {
    MetricName.DETECTION_RATE: MetricDefinition(
        name=MetricName.DETECTION_RATE,
        formula="detected_vulns / expected_vulns",
        description="Percentage of known vulnerabilities successfully detected",
        target=0.80,
        threshold_warning=0.75,
        threshold_critical=0.70,
        unit="percentage",
        higher_is_better=True,
        data_sources=[
            "tests/projects/*/MANIFEST.yaml (expected vulnerabilities)",
            "VKG scan output (detected findings)",
        ],
        dependencies=[],
    ),
    MetricName.FALSE_POSITIVE_RATE: MetricDefinition(
        name=MetricName.FALSE_POSITIVE_RATE,
        formula="FP / (FP + TP)",
        description="Percentage of findings that are false alarms",
        target=0.15,
        threshold_warning=0.18,
        threshold_critical=0.20,
        unit="percentage",
        higher_is_better=False,
        data_sources=[
            "tests/projects/*/MANIFEST.yaml (ground truth)",
            "VKG scan output (findings to compare)",
        ],
        dependencies=[],
    ),
    MetricName.PATTERN_PRECISION: MetricDefinition(
        name=MetricName.PATTERN_PRECISION,
        formula="avg(TP / (TP + FP) per pattern)",
        description="Average precision across all patterns",
        target=0.85,
        threshold_warning=0.80,
        threshold_critical=0.75,
        unit="percentage",
        higher_is_better=True,
        data_sources=[
            "tests/projects/*/MANIFEST.yaml (ground truth per pattern)",
            "VKG scan output (findings grouped by pattern)",
        ],
        dependencies=[],
    ),
    MetricName.SCAFFOLD_COMPILE_RATE: MetricDefinition(
        name=MetricName.SCAFFOLD_COMPILE_RATE,
        formula="compiled_scaffolds / total_scaffolds",
        description="Percentage of generated test scaffolds that compile",
        target=0.60,
        threshold_warning=0.50,
        threshold_critical=0.40,
        unit="percentage",
        higher_is_better=True,
        data_sources=[
            "Scaffold generation logs",
            "Foundry compilation results",
        ],
        dependencies=["Phase 6 (Beads)"],
    ),
    MetricName.LLM_AUTONOMY: MetricDefinition(
        name=MetricName.LLM_AUTONOMY,
        formula="auto_resolved / total_tier_b_findings",
        description="Percentage of Tier B findings resolved without human escalation",
        target=0.70,
        threshold_warning=0.60,
        threshold_critical=0.50,
        unit="percentage",
        higher_is_better=True,
        data_sources=[
            "Bead verdict logs",
            "LLM verification results",
        ],
        dependencies=["Phase 6 (Beads)", "Phase 11 (LLM)"],
    ),
    MetricName.TIME_TO_DETECTION: MetricDefinition(
        name=MetricName.TIME_TO_DETECTION,
        formula="avg(scan_duration_per_contract)",
        description="Average time to complete vulnerability scan per contract",
        target=30.0,
        threshold_warning=45.0,
        threshold_critical=60.0,
        unit="seconds",
        higher_is_better=False,
        data_sources=[
            "CLI timing logs",
            "Scan duration measurements",
        ],
        dependencies=[],
    ),
    MetricName.TOKEN_EFFICIENCY: MetricDefinition(
        name=MetricName.TOKEN_EFFICIENCY,
        formula="avg(tokens_per_finding_resolution)",
        description="Average LLM tokens used per finding resolution",
        target=10000,
        threshold_warning=15000,
        threshold_critical=20000,
        unit="tokens",
        higher_is_better=False,
        data_sources=[
            "LLM telemetry (src/alphaswarm_sol/llm/telemetry.py)",
            "Token usage logs",
        ],
        dependencies=["Phase 11 (LLM)"],
    ),
    MetricName.ESCALATION_RATE: MetricDefinition(
        name=MetricName.ESCALATION_RATE,
        formula="human_escalations / total_tier_b_findings",
        description="Percentage of findings requiring human review",
        target=0.20,
        threshold_warning=0.25,
        threshold_critical=0.30,
        unit="percentage",
        higher_is_better=False,
        data_sources=[
            "Bead escalation logs",
            "Human review requests",
        ],
        dependencies=["Phase 6 (Beads)"],
    ),
}


def get_definition(name: MetricName) -> MetricDefinition:
    """Get the definition for a metric by name."""
    return METRIC_DEFINITIONS[name]


def get_all_definitions() -> dict[MetricName, MetricDefinition]:
    """Get all metric definitions."""
    return METRIC_DEFINITIONS.copy()


def get_available_metrics(completed_phases: set[str] | None = None) -> list[MetricName]:
    """Return metrics that can be calculated based on available dependencies.

    Args:
        completed_phases: Set of completed phase names. If None, assumes only
            base phases (no Beads, no LLM) are complete.

    Returns:
        List of MetricName values that can be calculated.
    """
    if completed_phases is None:
        # Default: only core metrics that don't require Beads/LLM
        completed_phases = set()

    available = []
    for name, defn in METRIC_DEFINITIONS.items():
        # Check if all dependencies are satisfied
        if not defn.dependencies:
            available.append(name)
        elif all(dep in completed_phases for dep in defn.dependencies):
            available.append(name)

    return available


def get_core_metrics() -> list[MetricName]:
    """Return metrics that don't depend on Beads or LLM phases.

    These metrics can always be calculated:
    - Detection Rate
    - False Positive Rate
    - Pattern Precision
    - Time to Detection
    """
    return [
        MetricName.DETECTION_RATE,
        MetricName.FALSE_POSITIVE_RATE,
        MetricName.PATTERN_PRECISION,
        MetricName.TIME_TO_DETECTION,
    ]


def get_bead_dependent_metrics() -> list[MetricName]:
    """Return metrics that require Beads phase."""
    return [
        MetricName.SCAFFOLD_COMPILE_RATE,
        MetricName.ESCALATION_RATE,
    ]


def get_llm_dependent_metrics() -> list[MetricName]:
    """Return metrics that require LLM phase."""
    return [
        MetricName.LLM_AUTONOMY,
        MetricName.TOKEN_EFFICIENCY,
    ]
