"""
Alert Manager

Manages severity-based alerting for security events.
Supports multiple channels and configurable rules.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"    # Immediate action required
    HIGH = "high"            # Urgent attention needed
    MEDIUM = "medium"        # Should be addressed
    LOW = "low"              # Informational
    INFO = "info"            # Status update


class AlertChannel(Enum):
    """Alert delivery channels."""
    LOG = "log"              # Local logging
    CONSOLE = "console"      # Console output
    WEBHOOK = "webhook"      # HTTP webhook
    EMAIL = "email"          # Email notification
    DISCORD = "discord"      # Discord webhook
    SLACK = "slack"          # Slack webhook
    PAGERDUTY = "pagerduty"  # PagerDuty incident


@dataclass
class Alert:
    """
    A security alert.
    """
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    contract_address: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    # Context
    event_type: Optional[str] = None
    finding_id: Optional[str] = None
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None

    # Delivery tracking
    channels_sent: List[AlertChannel] = field(default_factory=list)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "contract_address": self.contract_address,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "finding_id": self.finding_id,
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "acknowledged": self.acknowledged,
        }

    def to_slack_message(self) -> Dict[str, Any]:
        """Format for Slack."""
        color = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.HIGH: "warning",
            AlertSeverity.MEDIUM: "#f0ad4e",
            AlertSeverity.LOW: "good",
            AlertSeverity.INFO: "#17a2b8",
        }.get(self.severity, "#6c757d")

        return {
            "attachments": [{
                "color": color,
                "title": self.title,
                "text": self.message,
                "fields": [
                    {"title": "Severity", "value": self.severity.value.upper(), "short": True},
                    {"title": "Contract", "value": self.contract_address or "N/A", "short": True},
                ],
                "ts": int(self.timestamp.timestamp()),
            }]
        }

    def to_discord_message(self) -> Dict[str, Any]:
        """Format for Discord."""
        color = {
            AlertSeverity.CRITICAL: 0xFF0000,  # Red
            AlertSeverity.HIGH: 0xFF8C00,      # Orange
            AlertSeverity.MEDIUM: 0xFFD700,    # Yellow
            AlertSeverity.LOW: 0x00FF00,       # Green
            AlertSeverity.INFO: 0x0000FF,      # Blue
        }.get(self.severity, 0x808080)

        return {
            "embeds": [{
                "title": self.title,
                "description": self.message,
                "color": color,
                "fields": [
                    {"name": "Severity", "value": self.severity.value.upper(), "inline": True},
                    {"name": "Contract", "value": self.contract_address or "N/A", "inline": True},
                ],
                "timestamp": self.timestamp.isoformat(),
            }]
        }


@dataclass
class AlertRule:
    """
    Rule for triggering alerts.
    """
    rule_id: str
    name: str
    description: str

    # Conditions
    min_severity: AlertSeverity = AlertSeverity.MEDIUM
    event_types: List[str] = field(default_factory=list)  # Empty = all
    contract_addresses: List[str] = field(default_factory=list)  # Empty = all

    # Actions
    channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.LOG])
    throttle_seconds: int = 0            # Minimum time between alerts

    # State
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    def matches(self, alert: Alert) -> bool:
        """Check if alert matches this rule."""
        # Check severity
        severity_order = [AlertSeverity.INFO, AlertSeverity.LOW, AlertSeverity.MEDIUM,
                        AlertSeverity.HIGH, AlertSeverity.CRITICAL]
        if severity_order.index(alert.severity) < severity_order.index(self.min_severity):
            return False

        # Check event type
        if self.event_types and alert.event_type not in self.event_types:
            return False

        # Check contract address
        if self.contract_addresses and alert.contract_address not in self.contract_addresses:
            return False

        # Check throttle
        if self.throttle_seconds > 0 and self.last_triggered:
            elapsed = (datetime.now() - self.last_triggered).total_seconds()
            if elapsed < self.throttle_seconds:
                return False

        return True


class AlertManager:
    """
    Manages alert creation, routing, and delivery.
    """

    def __init__(self):
        self.alerts: List[Alert] = []
        self.rules: Dict[str, AlertRule] = {}
        self.channel_handlers: Dict[AlertChannel, Callable[[Alert], None]] = {}
        self._alert_counter = 0

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default channel handlers."""
        self.channel_handlers[AlertChannel.LOG] = self._handle_log
        self.channel_handlers[AlertChannel.CONSOLE] = self._handle_console

    def _handle_log(self, alert: Alert):
        """Handle log channel."""
        log_level = {
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.INFO: logging.DEBUG,
        }.get(alert.severity, logging.INFO)

        logger.log(log_level, f"[ALERT] {alert.title}: {alert.message}")

    def _handle_console(self, alert: Alert):
        """Handle console channel."""
        icon = {
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.HIGH: "⚠️",
            AlertSeverity.MEDIUM: "⚡",
            AlertSeverity.LOW: "ℹ️",
            AlertSeverity.INFO: "📝",
        }.get(alert.severity, "•")

        print(f"{icon} [{alert.severity.value.upper()}] {alert.title}")
        print(f"   {alert.message}")
        if alert.contract_address:
            print(f"   Contract: {alert.contract_address}")

    def register_handler(
        self,
        channel: AlertChannel,
        handler: Callable[[Alert], None]
    ):
        """Register a channel handler."""
        self.channel_handlers[channel] = handler

    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str):
        """Remove an alert rule."""
        self.rules.pop(rule_id, None)

    def create_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        **kwargs
    ) -> Alert:
        """
        Create and dispatch an alert.

        Args:
            severity: Alert severity
            title: Alert title
            message: Alert message
            **kwargs: Additional alert fields

        Returns:
            Created Alert
        """
        self._alert_counter += 1
        alert_id = f"ALERT-{self._alert_counter:06d}"

        alert = Alert(
            alert_id=alert_id,
            severity=severity,
            title=title,
            message=message,
            **kwargs
        )

        self.alerts.append(alert)

        # Dispatch to matching rules
        self._dispatch_alert(alert)

        return alert

    def _dispatch_alert(self, alert: Alert):
        """Dispatch alert to matching rules."""
        for rule in self.rules.values():
            if rule.matches(alert):
                # Update rule state
                rule.last_triggered = datetime.now()
                rule.trigger_count += 1

                # Send to channels
                for channel in rule.channels:
                    self._send_to_channel(alert, channel)

        # If no rules matched but it's critical, always log
        if not any(r.matches(alert) for r in self.rules.values()):
            if alert.severity == AlertSeverity.CRITICAL:
                self._send_to_channel(alert, AlertChannel.LOG)

    def _send_to_channel(self, alert: Alert, channel: AlertChannel):
        """Send alert to a specific channel."""
        handler = self.channel_handlers.get(channel)

        if handler:
            try:
                handler(alert)
                alert.channels_sent.append(channel)
            except Exception as e:
                logger.error(f"Failed to send alert to {channel.value}: {e}")
        else:
            logger.warning(f"No handler registered for channel: {channel.value}")

    def acknowledge(
        self,
        alert_id: str,
        acknowledged_by: Optional[str] = None
    ) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert to acknowledge
            acknowledged_by: Who acknowledged

        Returns:
            True if alert was found and acknowledged
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = acknowledged_by
                return True

        return False

    def get_unacknowledged(
        self,
        min_severity: AlertSeverity = AlertSeverity.LOW
    ) -> List[Alert]:
        """Get unacknowledged alerts."""
        severity_order = [AlertSeverity.INFO, AlertSeverity.LOW, AlertSeverity.MEDIUM,
                        AlertSeverity.HIGH, AlertSeverity.CRITICAL]

        return [
            a for a in self.alerts
            if not a.acknowledged and
            severity_order.index(a.severity) >= severity_order.index(min_severity)
        ]

    def get_alerts_for_contract(self, contract_address: str) -> List[Alert]:
        """Get all alerts for a contract."""
        return [a for a in self.alerts if a.contract_address == contract_address]

    def get_recent_alerts(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get recent alerts."""
        alerts = sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        by_severity = {}
        for sev in AlertSeverity:
            by_severity[sev.value] = len([a for a in self.alerts if a.severity == sev])

        unacked = len(self.get_unacknowledged())

        return {
            "total_alerts": len(self.alerts),
            "by_severity": by_severity,
            "unacknowledged": unacked,
            "rules_count": len(self.rules),
        }

    def clear_alerts(self, acknowledged_only: bool = False):
        """Clear alert history."""
        if acknowledged_only:
            self.alerts = [a for a in self.alerts if not a.acknowledged]
        else:
            self.alerts.clear()

    def export_alerts(self, format: str = "json") -> str:
        """Export alerts to string format."""
        if format == "json":
            return json.dumps([a.to_dict() for a in self.alerts], indent=2)
        else:
            lines = []
            for alert in self.alerts:
                lines.append(f"[{alert.severity.value}] {alert.title}")
                lines.append(f"  {alert.message}")
                lines.append("")
            return "\n".join(lines)
