"""
Streaming Session

High-level session management for real-time monitoring.
Combines monitor, analyzer, health scoring, and alerting.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import asyncio
import logging

from alphaswarm_sol.streaming.monitor import (
    ContractMonitor,
    ContractEvent,
    EventType,
    MonitorConfig,
)
from alphaswarm_sol.streaming.incremental import (
    IncrementalAnalyzer,
    DiffResult,
)
from alphaswarm_sol.streaming.health import (
    HealthScoreCalculator,
    HealthScore,
    HealthFactors,
)
from alphaswarm_sol.streaming.alerts import (
    AlertManager,
    Alert,
    AlertSeverity,
    AlertChannel,
    AlertRule,
)

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Status of streaming session."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SessionConfig:
    """Configuration for streaming session."""
    # Monitoring
    monitor_config: MonitorConfig = field(default_factory=MonitorConfig)

    # Analysis
    auto_analyze_upgrades: bool = True
    auto_analyze_deployments: bool = True

    # Health scoring
    calculate_health_on_event: bool = True
    health_score_interval_seconds: int = 3600  # Periodic health check

    # Alerting
    default_alert_channels: List[AlertChannel] = field(
        default_factory=lambda: [AlertChannel.LOG, AlertChannel.CONSOLE]
    )

    # Session
    session_name: str = "default"
    max_events_stored: int = 10000


@dataclass
class SessionMetrics:
    """Metrics for the session."""
    events_processed: int = 0
    analyses_performed: int = 0
    alerts_generated: int = 0
    health_scores_calculated: int = 0

    start_time: Optional[datetime] = None
    last_event_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "events_processed": self.events_processed,
            "analyses_performed": self.analyses_performed,
            "alerts_generated": self.alerts_generated,
            "health_scores_calculated": self.health_scores_calculated,
            "uptime_seconds": uptime,
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None,
        }


class StreamingSession:
    """
    High-level streaming session for continuous monitoring.

    Integrates all streaming components:
    - Contract monitoring
    - Incremental analysis
    - Health scoring
    - Alerting
    """

    def __init__(self, config: Optional[SessionConfig] = None):
        self.config = config or SessionConfig()
        self.status = SessionStatus.IDLE

        # Components
        self.monitor = ContractMonitor(self.config.monitor_config)
        self.analyzer = IncrementalAnalyzer()
        self.health_calculator = HealthScoreCalculator()
        self.alert_manager = AlertManager()

        # State
        self.metrics = SessionMetrics()
        self._contract_code_cache: Dict[str, str] = {}
        self._last_health_scores: Dict[str, HealthScore] = {}

        # Setup default alert rules
        self._setup_default_rules()

        # Register event handlers
        self._register_event_handlers()

    def _setup_default_rules(self):
        """Setup default alerting rules."""
        # Critical events rule
        self.alert_manager.add_rule(AlertRule(
            rule_id="critical-events",
            name="Critical Events",
            description="Alert on all critical severity events",
            min_severity=AlertSeverity.CRITICAL,
            channels=self.config.default_alert_channels,
        ))

        # Upgrade alerts
        self.alert_manager.add_rule(AlertRule(
            rule_id="upgrades",
            name="Contract Upgrades",
            description="Alert on contract upgrades",
            min_severity=AlertSeverity.HIGH,
            event_types=["upgrade"],
            channels=self.config.default_alert_channels,
        ))

        # High value transactions
        self.alert_manager.add_rule(AlertRule(
            rule_id="high-value",
            name="High Value Transactions",
            description="Alert on high value transactions",
            min_severity=AlertSeverity.MEDIUM,
            event_types=["high_value_tx"],
            channels=[AlertChannel.LOG],
            throttle_seconds=300,  # Max once per 5 minutes
        ))

    def _register_event_handlers(self):
        """Register handlers for contract events."""
        self.monitor.add_handler(EventType.DEPLOYMENT, self._on_deployment)
        self.monitor.add_handler(EventType.UPGRADE, self._on_upgrade)
        self.monitor.add_handler(EventType.OWNERSHIP_CHANGE, self._on_ownership_change)
        self.monitor.add_handler(EventType.HIGH_VALUE_TX, self._on_high_value_tx)
        self.monitor.add_handler(EventType.PAUSE, self._on_pause)

    def _on_deployment(self, event: ContractEvent):
        """Handle new contract deployment."""
        self.metrics.events_processed += 1
        self.metrics.last_event_time = event.timestamp

        self.alert_manager.create_alert(
            severity=AlertSeverity.HIGH,
            title="New Contract Deployed",
            message=f"Contract deployed at {event.contract_address}",
            contract_address=event.contract_address,
            event_type="deployment",
            tx_hash=event.tx_hash,
            block_number=event.block_number,
        )
        self.metrics.alerts_generated += 1

        # Auto-analyze if configured
        if self.config.auto_analyze_deployments:
            # Would trigger analysis here
            self.metrics.analyses_performed += 1

    def _on_upgrade(self, event: ContractEvent):
        """Handle contract upgrade."""
        self.metrics.events_processed += 1
        self.metrics.last_event_time = event.timestamp

        new_impl = event.data.get("new_implementation", "unknown")

        self.alert_manager.create_alert(
            severity=AlertSeverity.CRITICAL,
            title="Contract Upgraded",
            message=f"Proxy {event.contract_address} upgraded to {new_impl}",
            contract_address=event.contract_address,
            event_type="upgrade",
            tx_hash=event.tx_hash,
            block_number=event.block_number,
        )
        self.metrics.alerts_generated += 1

        # Incremental analysis
        if self.config.auto_analyze_upgrades:
            old_code = self._contract_code_cache.get(event.contract_address)
            if old_code:
                # Would fetch new code and diff here
                self.metrics.analyses_performed += 1

    def _on_ownership_change(self, event: ContractEvent):
        """Handle ownership change."""
        self.metrics.events_processed += 1
        self.metrics.last_event_time = event.timestamp

        new_owner = event.data.get("new_owner", "unknown")

        self.alert_manager.create_alert(
            severity=AlertSeverity.CRITICAL,
            title="Ownership Changed",
            message=f"Contract {event.contract_address} ownership changed to {new_owner}",
            contract_address=event.contract_address,
            event_type="ownership_change",
            tx_hash=event.tx_hash,
            block_number=event.block_number,
        )
        self.metrics.alerts_generated += 1

    def _on_high_value_tx(self, event: ContractEvent):
        """Handle high value transaction."""
        self.metrics.events_processed += 1
        self.metrics.last_event_time = event.timestamp

        value = event.data.get("value", 0)

        self.alert_manager.create_alert(
            severity=AlertSeverity.MEDIUM,
            title="High Value Transaction",
            message=f"Transaction of {value} ETH to {event.contract_address}",
            contract_address=event.contract_address,
            event_type="high_value_tx",
            tx_hash=event.tx_hash,
            block_number=event.block_number,
        )
        self.metrics.alerts_generated += 1

    def _on_pause(self, event: ContractEvent):
        """Handle contract pause."""
        self.metrics.events_processed += 1
        self.metrics.last_event_time = event.timestamp

        self.alert_manager.create_alert(
            severity=AlertSeverity.HIGH,
            title="Contract Paused",
            message=f"Contract {event.contract_address} has been paused",
            contract_address=event.contract_address,
            event_type="pause",
            tx_hash=event.tx_hash,
            block_number=event.block_number,
        )
        self.metrics.alerts_generated += 1

    async def start(self):
        """Start the streaming session."""
        if self.status == SessionStatus.RUNNING:
            logger.warning("Session already running")
            return

        self.status = SessionStatus.RUNNING
        self.metrics.start_time = datetime.now()

        logger.info(f"Starting streaming session: {self.config.session_name}")

        try:
            await self.monitor.start()
        except Exception as e:
            self.status = SessionStatus.ERROR
            logger.error(f"Session error: {e}")
            raise

    def stop(self):
        """Stop the streaming session."""
        self.monitor.stop()
        self.status = SessionStatus.STOPPED
        logger.info(f"Stopped streaming session: {self.config.session_name}")

    def pause(self):
        """Pause the session."""
        self.monitor.stop()
        self.status = SessionStatus.PAUSED
        logger.info("Session paused")

    def resume(self):
        """Resume the session."""
        if self.status == SessionStatus.PAUSED:
            self.status = SessionStatus.RUNNING
            # Would restart monitoring
            logger.info("Session resumed")

    def watch_contract(self, address: str, initial_code: Optional[str] = None):
        """
        Add a contract to watch list.

        Args:
            address: Contract address
            initial_code: Optional initial source code for diff analysis
        """
        self.monitor.watch_address(address)

        if initial_code:
            self._contract_code_cache[address] = initial_code

        logger.info(f"Now watching contract: {address}")

    def unwatch_contract(self, address: str):
        """Remove a contract from watch list."""
        self.monitor.unwatch_address(address)
        self._contract_code_cache.pop(address, None)
        logger.info(f"Stopped watching contract: {address}")

    def calculate_health(
        self,
        address: str,
        findings: Optional[List[Dict]] = None,
        factors: Optional[HealthFactors] = None
    ) -> HealthScore:
        """
        Calculate health score for a contract.

        Args:
            address: Contract address
            findings: Optional VKG findings
            factors: Optional pre-calculated factors

        Returns:
            HealthScore
        """
        if factors:
            score = self.health_calculator.calculate(address, factors)
        elif findings:
            score = self.health_calculator.calculate_from_findings(address, findings)
        else:
            # Use default factors
            score = self.health_calculator.calculate(address, HealthFactors())

        self._last_health_scores[address] = score
        self.metrics.health_scores_calculated += 1

        # Alert on low health scores
        if score.score < 50:
            self.alert_manager.create_alert(
                severity=AlertSeverity.HIGH,
                title="Low Health Score",
                message=f"Contract {address} has health score {score.score}/100",
                contract_address=address,
            )
            self.metrics.alerts_generated += 1

        return score

    def analyze_upgrade(
        self,
        address: str,
        old_code: str,
        new_code: str
    ) -> DiffResult:
        """
        Analyze a contract upgrade.

        Args:
            address: Contract address
            old_code: Previous version code
            new_code: New version code

        Returns:
            DiffResult with changes
        """
        result = self.analyzer.diff_contracts(old_code, new_code)

        self.metrics.analyses_performed += 1

        # Alert on security-relevant changes
        security_changes = result.get_security_relevant()
        if security_changes:
            self.alert_manager.create_alert(
                severity=AlertSeverity.HIGH,
                title="Security-Relevant Upgrade Changes",
                message=f"Upgrade contains {len(security_changes)} security-relevant changes",
                contract_address=address,
            )
            self.metrics.alerts_generated += 1

        # Update code cache
        self._contract_code_cache[address] = new_code

        return result

    def process_block(self, block_data: Dict[str, Any]) -> List[ContractEvent]:
        """
        Process a block for events.

        Args:
            block_data: Block data with transactions

        Returns:
            List of detected events
        """
        return self.monitor.process_block(block_data)

    def get_status(self) -> Dict[str, Any]:
        """Get session status and metrics."""
        return {
            "status": self.status.value,
            "session_name": self.config.session_name,
            "metrics": self.metrics.to_dict(),
            "monitor": self.monitor.get_statistics(),
            "alerts": self.alert_manager.get_statistics(),
            "watched_contracts": len(self.config.monitor_config.watch_addresses),
        }

    def get_health_scores(self) -> Dict[str, HealthScore]:
        """Get all calculated health scores."""
        return self._last_health_scores.copy()

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get recent alerts."""
        return self.alert_manager.get_recent_alerts(limit=limit, severity=severity)

    def acknowledge_alert(self, alert_id: str, by: Optional[str] = None) -> bool:
        """Acknowledge an alert."""
        return self.alert_manager.acknowledge(alert_id, by)

    def export_session_data(self) -> Dict[str, Any]:
        """Export session data for persistence."""
        return {
            "session_name": self.config.session_name,
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
            "watched_contracts": self.config.monitor_config.watch_addresses,
            "events": [e.to_dict() for e in self.monitor.events[-100:]],
            "alerts": [a.to_dict() for a in self.alert_manager.alerts[-100:]],
            "health_scores": {
                addr: score.to_dict()
                for addr, score in self._last_health_scores.items()
            },
        }
