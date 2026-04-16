"""VKG Metrics & Observability Module.

This module provides:
- 8 key metrics tracking for VKG effectiveness
- Historical storage for trend analysis
- Alerting on metric degradation
- CLI integration for visibility
- CI integration for regression prevention

Usage:
    from alphaswarm_sol.metrics import MetricName, MetricValue, MetricSnapshot

    # Create a metric value
    detection_rate = MetricValue(
        name=MetricName.DETECTION_RATE,
        value=0.85,
        target=0.80,
        threshold_warning=0.75,
        threshold_critical=0.70,
    )

    # Check status
    status = detection_rate.evaluate_status()  # MetricStatus.OK

Phase 8: Metrics & Observability
"""

from .types import (
    MetricName,
    MetricStatus,
    MetricValue,
    MetricSnapshot,
    LOWER_IS_BETTER_METRICS,
)
from .definitions import (
    MetricDefinition,
    METRIC_DEFINITIONS,
    get_definition,
    get_all_definitions,
    get_available_metrics,
    get_core_metrics,
    get_bead_dependent_metrics,
    get_llm_dependent_metrics,
)
from .events import (
    EventType,
    DetectionEvent,
    TimingEvent,
    ScaffoldEvent,
    VerdictEvent,
    MetricEvent,
    event_from_dict,
)
from .event_store import EventStore
from .recorder import MetricsRecorder, get_recorder
from .calculator import MetricCalculator, create_calculator
from .tracker import MetricsTracker
from .storage import HistoryStore, create_history_store
from .alerting import Alert, AlertLevel, AlertType, AlertChecker, check_alerts
from .ci import (
    ExitCode,
    CIResult,
    check_metrics_gate,
    save_baseline,
    compare_snapshots,
    format_ci_summary,
)
from .cost_ledger import (
    CostLedger,
    CostEntry,
    PoolBudget,
    PoolCostSummary,
    PoolBudgetExceededError,
    get_pool_ledger,
    clear_pool_ledgers,
    get_all_pool_summaries,
)

__all__ = [
    # Types
    "MetricName",
    "MetricStatus",
    "MetricValue",
    "MetricSnapshot",
    "LOWER_IS_BETTER_METRICS",
    # Definitions
    "MetricDefinition",
    "METRIC_DEFINITIONS",
    "get_definition",
    "get_all_definitions",
    "get_available_metrics",
    "get_core_metrics",
    "get_bead_dependent_metrics",
    "get_llm_dependent_metrics",
    # Events
    "EventType",
    "DetectionEvent",
    "TimingEvent",
    "ScaffoldEvent",
    "VerdictEvent",
    "MetricEvent",
    "event_from_dict",
    # Recording
    "EventStore",
    "MetricsRecorder",
    "get_recorder",
    # Calculation
    "MetricCalculator",
    "create_calculator",
    "MetricsTracker",
    # Storage
    "HistoryStore",
    "create_history_store",
    # Alerting
    "Alert",
    "AlertLevel",
    "AlertType",
    "AlertChecker",
    "check_alerts",
    # CI Integration
    "ExitCode",
    "CIResult",
    "check_metrics_gate",
    "save_baseline",
    "compare_snapshots",
    "format_ci_summary",
    # Cost Ledger
    "CostLedger",
    "CostEntry",
    "PoolBudget",
    "PoolCostSummary",
    "PoolBudgetExceededError",
    "get_pool_ledger",
    "clear_pool_ledgers",
    "get_all_pool_summaries",
]
