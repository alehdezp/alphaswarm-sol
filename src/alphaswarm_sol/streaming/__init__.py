"""
Real-Time Vulnerability Streaming Module

Provides continuous security monitoring for smart contracts:
- On-chain contract monitoring
- Incremental analysis for contract upgrades
- Health score calculation
- Severity-based alerting
"""

from alphaswarm_sol.streaming.monitor import (
    ContractEvent,
    EventType,
    ContractMonitor,
    MonitorConfig,
)

from alphaswarm_sol.streaming.incremental import (
    DiffResult,
    IncrementalAnalyzer,
    ChangeType,
    FunctionChange,
)

from alphaswarm_sol.streaming.health import (
    HealthScore,
    HealthScoreCalculator,
    HealthFactors,
    HealthTrend,
)

from alphaswarm_sol.streaming.alerts import (
    Alert,
    AlertSeverity,
    AlertChannel,
    AlertManager,
    AlertRule,
)

from alphaswarm_sol.streaming.session import (
    StreamingSession,
    SessionConfig,
    SessionStatus,
)

__all__ = [
    # Monitor
    "ContractEvent",
    "EventType",
    "ContractMonitor",
    "MonitorConfig",
    # Incremental
    "DiffResult",
    "IncrementalAnalyzer",
    "ChangeType",
    "FunctionChange",
    # Health
    "HealthScore",
    "HealthScoreCalculator",
    "HealthFactors",
    "HealthTrend",
    # Alerts
    "Alert",
    "AlertSeverity",
    "AlertChannel",
    "AlertManager",
    "AlertRule",
    # Session
    "StreamingSession",
    "SessionConfig",
    "SessionStatus",
]
