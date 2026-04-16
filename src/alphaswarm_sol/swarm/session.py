"""
Swarm Session

High-level interface for autonomous security audits.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import logging

from .coordinator import SwarmCoordinator, CoordinatorConfig, SwarmStatus, SwarmMetrics
from .shared_memory import SharedMemory, Finding, Hypothesis, Severity
from .task_board import TaskBoard

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status."""
    CREATED = "created"
    CONFIGURED = "configured"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SessionConfig:
    """Configuration for audit session."""
    # Coordinator config
    coordinator_config: Optional[CoordinatorConfig] = None

    # Session settings
    session_name: str = "audit_session"
    max_runtime_seconds: int = 3600
    auto_generate_report: bool = True

    # Quality thresholds
    min_findings_for_success: int = 0
    min_confidence_threshold: float = 0.7


@dataclass
class AuditReport:
    """Final audit report."""
    report_id: str
    session_name: str
    generated_at: datetime
    runtime_seconds: float

    # Summary stats
    total_functions_scanned: int
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int

    # Detailed findings
    findings: List[Dict[str, Any]]

    # Recommendations
    recommendations: List[str]

    # Raw data
    metrics: Dict[str, Any]
    agent_contributions: Dict[str, int]

    def get_risk_score(self) -> float:
        """Calculate overall risk score."""
        if self.total_functions_scanned == 0:
            return 0.0

        weights = {
            "critical": 10.0,
            "high": 5.0,
            "medium": 2.0,
            "low": 0.5,
        }

        score = (
            self.critical_findings * weights["critical"] +
            self.high_findings * weights["high"] +
            self.medium_findings * weights["medium"] +
            self.low_findings * weights["low"]
        )

        # Normalize by function count
        return min(100.0, score / self.total_functions_scanned * 10)

    def get_grade(self) -> str:
        """Get security grade."""
        risk = self.get_risk_score()
        if risk == 0:
            return "A+"
        elif risk < 5:
            return "A"
        elif risk < 15:
            return "B"
        elif risk < 30:
            return "C"
        elif risk < 50:
            return "D"
        else:
            return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "session_name": self.session_name,
            "generated_at": self.generated_at.isoformat(),
            "runtime_seconds": round(self.runtime_seconds, 2),
            "total_functions_scanned": self.total_functions_scanned,
            "total_findings": self.total_findings,
            "findings_by_severity": {
                "critical": self.critical_findings,
                "high": self.high_findings,
                "medium": self.medium_findings,
                "low": self.low_findings,
            },
            "risk_score": round(self.get_risk_score(), 2),
            "grade": self.get_grade(),
            "findings": self.findings,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
        }

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# Security Audit Report: {self.session_name}",
            f"",
            f"**Generated**: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Runtime**: {self.runtime_seconds:.1f} seconds",
            f"**Grade**: {self.get_grade()} (Risk Score: {self.get_risk_score():.1f}/100)",
            "",
            "## Executive Summary",
            "",
            f"- **Functions Scanned**: {self.total_functions_scanned}",
            f"- **Total Findings**: {self.total_findings}",
            f"  - Critical: {self.critical_findings}",
            f"  - High: {self.high_findings}",
            f"  - Medium: {self.medium_findings}",
            f"  - Low: {self.low_findings}",
            "",
        ]

        if self.findings:
            lines.extend([
                "## Findings",
                "",
            ])

            for i, finding in enumerate(self.findings, 1):
                lines.extend([
                    f"### {i}. {finding.get('title', 'Untitled')}",
                    f"",
                    f"**Severity**: {finding.get('severity', 'unknown').upper()}",
                    f"**Type**: {finding.get('vulnerability_type', 'unknown')}",
                    f"**Function**: `{finding.get('target_function', 'unknown')}`",
                    f"**Confidence**: {finding.get('confidence', 0):.0%}",
                    "",
                    finding.get('description', 'No description'),
                    "",
                ])

                if finding.get('fix_recommendation'):
                    lines.extend([
                        "**Recommendation**:",
                        finding['fix_recommendation'],
                        "",
                    ])

        if self.recommendations:
            lines.extend([
                "## Recommendations",
                "",
            ])
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        lines.extend([
            "## Metrics",
            "",
            f"- Iterations: {self.metrics.get('iterations', 0)}",
            f"- Tasks Completed: {self.metrics.get('tasks_completed', 0)}",
            f"- Task Efficiency: {self.metrics.get('efficiency', 0):.1%}",
            "",
            "---",
            "*Report generated by True VKG Agent Swarm*",
        ])

        return "\n".join(lines)


@dataclass
class SessionResult:
    """Result of an audit session."""
    session_id: str
    status: SessionStatus
    start_time: datetime
    end_time: Optional[datetime]
    report: Optional[AuditReport]
    metrics: SwarmMetrics
    errors: List[str] = field(default_factory=list)

    def is_successful(self) -> bool:
        """Check if session completed successfully."""
        return self.status == SessionStatus.COMPLETED and not self.errors

    def get_duration_seconds(self) -> float:
        """Get session duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "duration_seconds": round(self.get_duration_seconds(), 2),
            "is_successful": self.is_successful(),
            "findings_count": self.report.total_findings if self.report else 0,
            "errors": self.errors,
        }


class SwarmSession:
    """
    High-level interface for autonomous security audits.

    Usage:
        session = SwarmSession()
        session.configure(functions_to_audit)
        result = session.run()
        print(result.report.to_markdown())
    """

    def __init__(self, config: Optional[SessionConfig] = None):
        self.config = config or SessionConfig()
        self.session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.status = SessionStatus.CREATED

        # Coordinator
        self.coordinator = SwarmCoordinator(self.config.coordinator_config)

        # Timing
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Results
        self.result: Optional[SessionResult] = None
        self.errors: List[str] = []

        # Input tracking
        self.functions_to_audit: List[Dict[str, Any]] = []

    def configure(self, functions: List[Dict[str, Any]]):
        """
        Configure session with functions to audit.

        Args:
            functions: List of function data dicts with keys like:
                - name: Function name
                - visibility: public/external/internal/private
                - has_external_call: bool
                - writes_state: bool
                - etc.
        """
        self.functions_to_audit = functions
        self.coordinator.initialize()
        self.coordinator.add_initial_tasks(functions)
        self.status = SessionStatus.CONFIGURED
        logger.info(f"Session configured with {len(functions)} functions")

    def run(self, max_iterations: Optional[int] = None) -> SessionResult:
        """
        Run the autonomous audit session.

        Returns SessionResult with report and metrics.
        """
        if self.status != SessionStatus.CONFIGURED:
            raise RuntimeError("Session not configured. Call configure() first.")

        self.start_time = datetime.now()
        self.status = SessionStatus.RUNNING
        logger.info(f"Starting audit session: {self.session_id}")

        try:
            # Run the swarm
            metrics = self.coordinator.run(max_iterations)

            # Generate report
            report = self._generate_report(metrics) if self.config.auto_generate_report else None

            self.end_time = datetime.now()
            self.status = SessionStatus.COMPLETED

            self.result = SessionResult(
                session_id=self.session_id,
                status=self.status,
                start_time=self.start_time,
                end_time=self.end_time,
                report=report,
                metrics=metrics,
                errors=self.errors,
            )

            logger.info(f"Session completed: {metrics.findings_discovered} findings")
            return self.result

        except Exception as e:
            self.status = SessionStatus.FAILED
            self.errors.append(str(e))
            self.end_time = datetime.now()
            logger.error(f"Session failed: {e}")

            self.result = SessionResult(
                session_id=self.session_id,
                status=self.status,
                start_time=self.start_time,
                end_time=self.end_time,
                report=None,
                metrics=self.coordinator.metrics,
                errors=self.errors,
            )
            return self.result

    def _generate_report(self, metrics: SwarmMetrics) -> AuditReport:
        """Generate audit report from swarm findings."""
        memory = self.coordinator.shared_memory

        # Collect findings
        findings = []
        severity_counts = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 0,
            Severity.MEDIUM: 0,
            Severity.LOW: 0,
        }

        for finding in memory.findings.values():
            findings.append(finding.to_dict())
            if finding.severity in severity_counts:
                severity_counts[finding.severity] += 1

        # Generate recommendations
        recommendations = self._generate_recommendations(memory)

        # Agent contributions
        agent_contributions = {}
        for agent in self.coordinator.agents.values():
            agent_contributions[agent.agent_id] = agent.tasks_completed

        runtime = (self.end_time or datetime.now()) - self.start_time

        return AuditReport(
            report_id=f"report-{self.session_id}",
            session_name=self.config.session_name,
            generated_at=datetime.now(),
            runtime_seconds=runtime.total_seconds(),
            total_functions_scanned=len(self.functions_to_audit),
            total_findings=len(findings),
            critical_findings=severity_counts[Severity.CRITICAL],
            high_findings=severity_counts[Severity.HIGH],
            medium_findings=severity_counts[Severity.MEDIUM],
            low_findings=severity_counts[Severity.LOW],
            findings=findings,
            recommendations=recommendations,
            metrics=metrics.to_dict(),
            agent_contributions=agent_contributions,
        )

    def _generate_recommendations(self, memory: SharedMemory) -> List[str]:
        """Generate recommendations based on findings."""
        recommendations = []

        # Check for critical issues
        critical = memory.get_findings_by_severity(Severity.CRITICAL)
        if critical:
            recommendations.append(
                f"URGENT: Address {len(critical)} critical vulnerabilities immediately"
            )

        # Check for reentrancy
        reentrancy_findings = [
            f for f in memory.findings.values()
            if f.vulnerability_type == "reentrancy"
        ]
        if reentrancy_findings:
            recommendations.append(
                "Implement ReentrancyGuard pattern on all external-facing functions"
            )

        # Check for access control
        access_findings = [
            f for f in memory.findings.values()
            if f.vulnerability_type == "access_control"
        ]
        if access_findings:
            recommendations.append(
                "Review and strengthen access control on state-modifying functions"
            )

        # Check for oracle issues
        oracle_findings = [
            f for f in memory.findings.values()
            if f.vulnerability_type == "oracle"
        ]
        if oracle_findings:
            recommendations.append(
                "Add staleness checks and fallback mechanisms for oracle data"
            )

        # General recommendations
        if memory.findings:
            recommendations.append("Schedule follow-up audit after implementing fixes")
            recommendations.append("Consider formal verification for critical functions")

        return recommendations

    def stop(self):
        """Stop a running session."""
        self.coordinator.stop()
        self.status = SessionStatus.COMPLETED
        self.end_time = datetime.now()

    def get_progress(self) -> Dict[str, Any]:
        """Get current session progress."""
        stats = self.coordinator.get_statistics()
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "swarm_status": stats["status"],
            "iterations": stats["metrics"]["iterations"],
            "tasks_completed": stats["metrics"]["tasks_completed"],
            "findings_so_far": stats["metrics"]["findings_discovered"],
            "runtime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
        }

    def get_summary(self) -> str:
        """Get session summary."""
        progress = self.get_progress()
        lines = [
            f"=== Session: {self.session_id} ===",
            f"Status: {progress['status']}",
            f"Iterations: {progress['iterations']}",
            f"Tasks: {progress['tasks_completed']}",
            f"Findings: {progress['findings_so_far']}",
            f"Runtime: {progress['runtime_seconds']:.1f}s",
        ]

        if self.result and self.result.report:
            lines.extend([
                "",
                f"Grade: {self.result.report.get_grade()}",
                f"Risk Score: {self.result.report.get_risk_score():.1f}/100",
            ])

        return "\n".join(lines)
