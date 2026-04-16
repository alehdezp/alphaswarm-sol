"""Supervisor agent for monitoring queues and detecting stuck work.

This module implements the Supervisor agent per PHILOSOPHY.md Infrastructure Roles:
"Supervisor monitors queues, nudges stuck work, enforces SLAs"

Per 05.2-CONTEXT.md:
- Log and continue (don't auto-intervene)
- Let pool complete with what it can
- Visible in logs for post-audit review

Usage:
    from alphaswarm_sol.agents.infrastructure import (
        SupervisorAgent, SupervisorConfig, SupervisorReport
    )
    from alphaswarm_sol.agents.hooks import AgentInbox, AgentRole

    # Create supervisor
    supervisor = SupervisorAgent(
        pool_manager=manager,
        inboxes={
            AgentRole.ATTACKER: attacker_inbox,
            AgentRole.DEFENDER: defender_inbox,
        }
    )

    # Run check
    report = supervisor.check_pool("pool-123")
    print(f"Stuck work: {len(report.stuck_work)}")
    print(f"Escalations: {report.escalations}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .prompts import SUPERVISOR_SYSTEM_PROMPT

if TYPE_CHECKING:
    from alphaswarm_sol.agents.hooks import AgentInbox, WorkClaim
    from alphaswarm_sol.agents.hooks import AgentRole as HookAgentRole
    from alphaswarm_sol.agents.runtime import AgentRuntime
    from alphaswarm_sol.orchestration.pool import PoolManager
    from alphaswarm_sol.orchestration.schemas import PoolStatus


logger = logging.getLogger(__name__)


@dataclass
class SupervisorConfig:
    """Configuration for supervisor agent.

    Attributes:
        stuck_threshold_minutes: Work in progress > this is considered stuck
        check_interval_seconds: How often to run checks (for scheduled mode)
        escalate_after_failures: Escalate to human after this many failures
        log_only: Only log issues, don't auto-intervene (per 05.2-CONTEXT.md)
        timeout_check_enabled: Whether to check for timed out work claims

    Usage:
        config = SupervisorConfig(
            stuck_threshold_minutes=15,
            escalate_after_failures=2
        )
        supervisor = SupervisorAgent(manager, inboxes, config)
    """

    stuck_threshold_minutes: int = 30
    check_interval_seconds: int = 60
    escalate_after_failures: int = 3
    log_only: bool = True  # Per 05.2-CONTEXT.md: log and continue
    timeout_check_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stuck_threshold_minutes": self.stuck_threshold_minutes,
            "check_interval_seconds": self.check_interval_seconds,
            "escalate_after_failures": self.escalate_after_failures,
            "log_only": self.log_only,
            "timeout_check_enabled": self.timeout_check_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SupervisorConfig":
        """Create from dictionary."""
        return cls(
            stuck_threshold_minutes=int(data.get("stuck_threshold_minutes", 30)),
            check_interval_seconds=int(data.get("check_interval_seconds", 60)),
            escalate_after_failures=int(data.get("escalate_after_failures", 3)),
            log_only=bool(data.get("log_only", True)),
            timeout_check_enabled=bool(data.get("timeout_check_enabled", True)),
        )


@dataclass
class StuckWorkReport:
    """Report of a stuck work item.

    Captures details about work that has been in progress longer than
    the configured threshold.

    Attributes:
        pool_id: Pool containing the stuck bead
        bead_id: ID of the stuck bead
        agent_role: Role of agent working on this bead
        in_progress_since: When work was claimed
        stuck_minutes: How long work has been stuck
        failure_count: Number of failures for this bead
        recommended_action: Supervisor's recommendation

    Usage:
        for report in supervisor_report.stuck_work:
            print(f"{report.bead_id}: stuck for {report.stuck_minutes}min")
            print(f"  Recommendation: {report.recommended_action}")
    """

    pool_id: str
    bead_id: str
    agent_role: str
    in_progress_since: datetime
    stuck_minutes: int
    failure_count: int
    recommended_action: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization/logging."""
        return {
            "pool_id": self.pool_id,
            "bead_id": self.bead_id,
            "agent_role": self.agent_role,
            "in_progress_since": self.in_progress_since.isoformat(),
            "stuck_minutes": self.stuck_minutes,
            "failure_count": self.failure_count,
            "recommended_action": self.recommended_action,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StuckWorkReport":
        """Create from dictionary."""
        return cls(
            pool_id=data["pool_id"],
            bead_id=data["bead_id"],
            agent_role=data["agent_role"],
            in_progress_since=datetime.fromisoformat(data["in_progress_since"]),
            stuck_minutes=int(data["stuck_minutes"]),
            failure_count=int(data["failure_count"]),
            recommended_action=data["recommended_action"],
        )


@dataclass
class SupervisorReport:
    """Full supervisor status report for a pool.

    Comprehensive report of pool health including stuck work,
    queue depths, and escalations.

    Attributes:
        timestamp: When the report was generated
        pool_id: Pool being monitored
        pool_status: Current pool lifecycle status
        total_beads: Total beads in the pool
        completed_beads: Number of beads with verdicts
        stuck_work: List of stuck work reports
        queue_depths: Pending count per agent role
        escalations: Bead IDs escalated to human review
        timed_out_claims: Count of work claims that timed out

    Usage:
        report = supervisor.check_pool("pool-123")
        print(f"Pool {report.pool_id}: {report.pool_status}")
        print(f"Progress: {report.completed_beads}/{report.total_beads}")
        if report.stuck_work:
            print(f"WARNING: {len(report.stuck_work)} stuck items")
    """

    timestamp: datetime
    pool_id: str
    pool_status: str  # Using str to avoid import issues
    total_beads: int
    completed_beads: int
    stuck_work: List[StuckWorkReport]
    queue_depths: Dict[str, int]  # role -> pending count
    escalations: List[str]  # bead_ids that need human attention
    timed_out_claims: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "pool_id": self.pool_id,
            "pool_status": self.pool_status,
            "total_beads": self.total_beads,
            "completed_beads": self.completed_beads,
            "stuck_work": [sw.to_dict() for sw in self.stuck_work],
            "queue_depths": self.queue_depths,
            "escalations": self.escalations,
            "timed_out_claims": self.timed_out_claims,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SupervisorReport":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            pool_id=data["pool_id"],
            pool_status=data["pool_status"],
            total_beads=int(data["total_beads"]),
            completed_beads=int(data["completed_beads"]),
            stuck_work=[StuckWorkReport.from_dict(sw) for sw in data.get("stuck_work", [])],
            queue_depths=data.get("queue_depths", {}),
            escalations=data.get("escalations", []),
            timed_out_claims=int(data.get("timed_out_claims", 0)),
        )

    @property
    def has_issues(self) -> bool:
        """Check if report contains any issues."""
        return len(self.stuck_work) > 0 or len(self.escalations) > 0 or self.timed_out_claims > 0

    @property
    def completion_ratio(self) -> float:
        """Get completion ratio (0.0 to 1.0)."""
        if self.total_beads == 0:
            return 1.0
        return self.completed_beads / self.total_beads

    def summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"Supervisor Report: {self.pool_id}",
            f"  Status: {self.pool_status}",
            f"  Progress: {self.completed_beads}/{self.total_beads} ({self.completion_ratio:.0%})",
            f"  Stuck work: {len(self.stuck_work)}",
            f"  Escalations: {len(self.escalations)}",
            f"  Timed out: {self.timed_out_claims}",
        ]
        if self.queue_depths:
            lines.append("  Queue depths:")
            for role, depth in self.queue_depths.items():
                lines.append(f"    {role}: {depth}")
        return "\n".join(lines)


class SupervisorAgent:
    """Monitors agent queues and detects stuck work.

    Per 05.2-CONTEXT.md:
    - Log and continue (don't auto-intervene)
    - Let pool complete with what it can
    - Visible in logs for post-audit review

    The supervisor:
    - Checks all agent inboxes for stuck work
    - Detects beads that exceed failure threshold
    - Flags problematic beads for human review
    - Reports queue depths and pool progress

    Usage:
        from alphaswarm_sol.agents.infrastructure import SupervisorAgent, SupervisorConfig
        from alphaswarm_sol.agents.hooks import AgentInbox, AgentRole
        from alphaswarm_sol.orchestration.pool import PoolManager

        # Setup
        manager = PoolManager(Path(".vrs/pools"))
        inboxes = {
            AgentRole.ATTACKER: AgentInbox(AgentRole.ATTACKER),
            AgentRole.DEFENDER: AgentInbox(AgentRole.DEFENDER),
            AgentRole.VERIFIER: AgentInbox(AgentRole.VERIFIER),
        }

        # Create supervisor
        config = SupervisorConfig(stuck_threshold_minutes=15)
        supervisor = SupervisorAgent(manager, inboxes, config)

        # Run check
        report = supervisor.check_pool("pool-123")
        if report.has_issues:
            logger.warning(report.summary())
    """

    def __init__(
        self,
        pool_manager: "PoolManager",
        inboxes: Dict["HookAgentRole", "AgentInbox"],
        config: Optional[SupervisorConfig] = None,
        runtime: Optional["AgentRuntime"] = None,
    ):
        """Initialize supervisor agent.

        Args:
            pool_manager: PoolManager for pool operations
            inboxes: Dictionary mapping AgentRole to AgentInbox
            config: Optional SupervisorConfig (uses defaults if not provided)
            runtime: Optional AgentRuntime for LLM-assisted decisions (future use)
        """
        self.pool_manager = pool_manager
        self.inboxes = inboxes
        self.config = config or SupervisorConfig()
        self.runtime = runtime
        self._escalated_beads: set = set()  # Track already-escalated beads
        self._system_prompt = SUPERVISOR_SYSTEM_PROMPT

    @property
    def base_path(self):
        """Get base path from pool manager."""
        return self.pool_manager.storage.path

    def check_pool(self, pool_id: str) -> SupervisorReport:
        """Run supervisor check on a pool.

        Checks all agent inboxes for:
        - Work stuck longer than threshold
        - Beads exceeding failure threshold
        - Queue depths per role
        - Timed out work claims

        Args:
            pool_id: Pool to check

        Returns:
            SupervisorReport with current pool status

        Raises:
            ValueError: If pool not found

        Usage:
            report = supervisor.check_pool("pool-123")
            if report.has_issues:
                logger.warning(f"Pool issues: {report.summary()}")
        """
        pool = self.pool_manager.get_pool(pool_id)
        if pool is None:
            raise ValueError(f"Pool not found: {pool_id}")

        stuck_work: List[StuckWorkReport] = []
        escalations: List[str] = []
        queue_depths: Dict[str, int] = {}
        timed_out_count = 0
        now = datetime.now()

        for role, inbox in self.inboxes.items():
            role_value = role.value if hasattr(role, "value") else str(role)
            queue_depths[role_value] = inbox.pending_count

            # Check in-progress work for stuck items
            for bead_id, claim in inbox._in_progress.items():
                minutes_stuck = (now - claim.claimed_at).total_seconds() / 60

                if minutes_stuck >= self.config.stuck_threshold_minutes:
                    report = StuckWorkReport(
                        pool_id=pool_id,
                        bead_id=bead_id,
                        agent_role=role_value,
                        in_progress_since=claim.claimed_at,
                        stuck_minutes=int(minutes_stuck),
                        failure_count=inbox._failure_counts.get(bead_id, 0),
                        recommended_action=self._recommend_action(claim, inbox),
                    )
                    stuck_work.append(report)
                    logger.warning(f"Stuck work detected: {report.to_dict()}")

            # Check for beads that exceeded failure threshold
            for bead_id, count in inbox._failure_counts.items():
                if count >= self.config.escalate_after_failures:
                    if bead_id not in self._escalated_beads:
                        escalations.append(bead_id)
                        self._escalated_beads.add(bead_id)
                        self._flag_for_human(pool_id, bead_id)
                        logger.info(
                            f"Escalating bead {bead_id} after {count} failures"
                        )

            # Check for timed out claims
            if self.config.timeout_check_enabled:
                timed_out = inbox.get_timed_out_claims()
                timed_out_count += len(timed_out)
                for claim in timed_out:
                    logger.warning(
                        f"Timed out work: {claim.bead.id} "
                        f"(claimed {claim.duration_seconds:.0f}s ago)"
                    )

        # Count completed beads
        completed = sum(1 for bid in pool.bead_ids if self._is_bead_complete(pool_id, bid))

        report = SupervisorReport(
            timestamp=now,
            pool_id=pool_id,
            pool_status=pool.status.value if hasattr(pool.status, "value") else str(pool.status),
            total_beads=len(pool.bead_ids),
            completed_beads=completed,
            stuck_work=stuck_work,
            queue_depths=queue_depths,
            escalations=escalations,
            timed_out_claims=timed_out_count,
        )

        logger.info(f"Supervisor check complete: {report.summary()}")
        return report

    def _recommend_action(self, claim: "WorkClaim", inbox: "AgentInbox") -> str:
        """Generate recommended action for stuck work.

        Args:
            claim: The work claim being evaluated
            inbox: The inbox containing the claim

        Returns:
            Recommendation string for human review
        """
        failures = inbox._failure_counts.get(claim.bead.id, 0)

        if failures >= self.config.escalate_after_failures:
            return "ESCALATE: Multiple failures, needs human review"
        elif claim.attempt > 2:
            return "ESCALATE: Too many attempts, consider manual investigation"
        elif claim.attempt > 1:
            return "MONITOR: Retry in progress"
        elif claim.duration_seconds > 3600:  # > 1 hour
            return "INVESTIGATE: Long running, may be stuck"
        else:
            return "WAIT: First attempt, may complete"

    def _flag_for_human(self, pool_id: str, bead_id: str) -> None:
        """Flag bead for human review.

        Sets human_flag=True on the bead and adds a note explaining
        the escalation reason.

        Args:
            pool_id: Pool containing the bead
            bead_id: Bead to flag
        """
        logger.info(f"Flagging bead {bead_id} for human review in pool {pool_id}")

        # Import here to avoid circular imports
        from alphaswarm_sol.beads.storage import BeadStorage

        # Try pool storage first
        beads_path = self.base_path.parent / "beads"
        storage = BeadStorage(beads_path)

        # Try to load from pool
        bead = storage.load_from_pool(bead_id, pool_id)
        if bead is None:
            # Fall back to main storage
            bead = storage.load(bead_id)

        if bead:
            bead.human_flag = True
            bead.add_note(
                f"[supervisor] Escalation: exceeded failure threshold "
                f"({self.config.escalate_after_failures} failures)"
            )
            # Save back to pool if pool_id set, otherwise main storage
            if bead.pool_id:
                storage.save_to_pool(bead, bead.pool_id)
            else:
                storage.save_bead(bead)
        else:
            logger.warning(f"Could not load bead {bead_id} for flagging")

    def _is_bead_complete(self, pool_id: str, bead_id: str) -> bool:
        """Check if bead has been completed (has verdict).

        Args:
            pool_id: Pool containing the bead
            bead_id: Bead to check

        Returns:
            True if bead is resolved, False otherwise
        """
        from alphaswarm_sol.beads.storage import BeadStorage

        beads_path = self.base_path.parent / "beads"
        storage = BeadStorage(beads_path)

        # Try pool storage first
        bead = storage.load_from_pool(bead_id, pool_id)
        if bead is None:
            bead = storage.load(bead_id)

        return bead is not None and bead.is_resolved

    def check_all_active_pools(self) -> List[SupervisorReport]:
        """Check all active pools.

        Convenience method to run supervisor check on all pools
        with active status.

        Returns:
            List of SupervisorReports for all active pools
        """
        reports = []
        for pool in self.pool_manager.get_active_pools():
            try:
                report = self.check_pool(pool.id)
                reports.append(report)
            except Exception as e:
                logger.error(f"Error checking pool {pool.id}: {e}")
        return reports

    def get_escalated_beads(self) -> List[str]:
        """Get list of all beads that have been escalated.

        Returns:
            List of bead IDs that were escalated during this session
        """
        return list(self._escalated_beads)

    def clear_escalation_tracking(self) -> None:
        """Clear the set of tracked escalated beads.

        Useful when starting a new supervision session.
        """
        self._escalated_beads.clear()


__all__ = [
    "SupervisorConfig",
    "StuckWorkReport",
    "SupervisorReport",
    "SupervisorAgent",
]
