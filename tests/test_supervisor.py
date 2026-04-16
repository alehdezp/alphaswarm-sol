"""Tests for the SupervisorAgent.

Tests the supervisor's ability to:
- Monitor agent inboxes for stuck work
- Detect beads exceeding failure threshold
- Escalate problematic beads for human review
- Report queue depths and pool progress
- Operate in log-only mode (no auto-intervention)
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import tempfile

from alphaswarm_sol.agents.infrastructure import (
    SupervisorAgent,
    SupervisorConfig,
    SupervisorReport,
    StuckWorkReport,
)
from alphaswarm_sol.agents.hooks import AgentInbox, InboxConfig, WorkClaim
from alphaswarm_sol.agents.hooks import AgentRole
from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.beads.types import BeadStatus, Severity


# ============================================================================
# Fixtures
# ============================================================================


def _create_mock_bead(bead_id: str, is_resolved: bool = False):
    """Create a properly configured mock bead.

    The mock needs all attributes required by PrioritizedBeadQueue.
    """
    bead = MagicMock(spec=VulnerabilityBead)
    bead.id = bead_id
    bead.vulnerability_class = "reentrancy"
    bead.severity = Severity.HIGH
    bead.status = BeadStatus.RESOLVED if is_resolved else BeadStatus.PENDING
    bead.is_resolved = is_resolved
    bead.human_flag = False
    bead.add_note = MagicMock()

    # Required by PrioritizedBeadQueue._compute_priority()
    bead.pattern_context = MagicMock()
    bead.pattern_context.why_flagged = "test flagged reason"
    bead.metadata = {}
    bead.notes = []  # Required for tool agreement check
    bead.created_at = datetime.now()

    return bead


@pytest.fixture
def mock_bead():
    """Create a mock VulnerabilityBead for testing."""
    return _create_mock_bead("test-bead-001")


@pytest.fixture
def mock_bead_factory():
    """Factory for creating mock beads."""
    return _create_mock_bead


@pytest.fixture
def mock_pool():
    """Create a mock Pool for testing."""
    pool = MagicMock()
    pool.id = "test-pool"
    pool.bead_ids = ["bead-1", "bead-2", "bead-3"]
    pool.status = MagicMock()
    pool.status.value = "execute"
    return pool


@pytest.fixture
def mock_pool_manager(mock_pool, tmp_path):
    """Create a mock PoolManager."""
    manager = MagicMock()
    manager.get_pool.return_value = mock_pool
    manager.get_active_pools.return_value = [mock_pool]
    manager.storage = MagicMock()
    manager.storage.path = tmp_path / "pools"
    return manager


@pytest.fixture
def empty_inboxes():
    """Create empty inboxes for each role."""
    return {
        AgentRole.ATTACKER: AgentInbox(AgentRole.ATTACKER),
        AgentRole.DEFENDER: AgentInbox(AgentRole.DEFENDER),
        AgentRole.VERIFIER: AgentInbox(AgentRole.VERIFIER),
    }


@pytest.fixture
def inboxes_with_work(mock_bead_factory):
    """Create inboxes with pending work."""
    inboxes = {}
    for role in [AgentRole.ATTACKER, AgentRole.DEFENDER, AgentRole.VERIFIER]:
        inbox = AgentInbox(role)
        # Add some beads
        for i in range(3):
            bead = mock_bead_factory(f"bead-{role.value}-{i}")
            inbox.assign(bead)
        inboxes[role] = inbox
    return inboxes


# ============================================================================
# SupervisorConfig Tests
# ============================================================================


class TestSupervisorConfig:
    """Tests for SupervisorConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SupervisorConfig()
        assert config.stuck_threshold_minutes == 30
        assert config.check_interval_seconds == 60
        assert config.escalate_after_failures == 3
        assert config.log_only is True
        assert config.timeout_check_enabled is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SupervisorConfig(
            stuck_threshold_minutes=15,
            escalate_after_failures=2,
            log_only=False,
        )
        assert config.stuck_threshold_minutes == 15
        assert config.escalate_after_failures == 2
        assert config.log_only is False

    def test_serialization(self):
        """Test config can be serialized and deserialized."""
        config = SupervisorConfig(
            stuck_threshold_minutes=20,
            escalate_after_failures=5,
        )
        data = config.to_dict()
        restored = SupervisorConfig.from_dict(data)

        assert restored.stuck_threshold_minutes == config.stuck_threshold_minutes
        assert restored.escalate_after_failures == config.escalate_after_failures
        assert restored.log_only == config.log_only


# ============================================================================
# StuckWorkReport Tests
# ============================================================================


class TestStuckWorkReport:
    """Tests for StuckWorkReport."""

    def test_creation(self):
        """Test creating a stuck work report."""
        report = StuckWorkReport(
            pool_id="pool-123",
            bead_id="bead-456",
            agent_role="attacker",
            in_progress_since=datetime.now() - timedelta(minutes=45),
            stuck_minutes=45,
            failure_count=2,
            recommended_action="ESCALATE: Multiple failures",
        )

        assert report.pool_id == "pool-123"
        assert report.bead_id == "bead-456"
        assert report.stuck_minutes == 45
        assert report.failure_count == 2

    def test_serialization(self):
        """Test report serialization."""
        now = datetime.now()
        report = StuckWorkReport(
            pool_id="pool-123",
            bead_id="bead-456",
            agent_role="attacker",
            in_progress_since=now,
            stuck_minutes=30,
            failure_count=1,
            recommended_action="WAIT",
        )

        data = report.to_dict()
        assert data["pool_id"] == "pool-123"
        assert data["bead_id"] == "bead-456"
        assert data["stuck_minutes"] == 30

        # Test round-trip
        restored = StuckWorkReport.from_dict(data)
        assert restored.bead_id == report.bead_id
        assert restored.stuck_minutes == report.stuck_minutes


# ============================================================================
# SupervisorReport Tests
# ============================================================================


class TestSupervisorReport:
    """Tests for SupervisorReport."""

    def test_creation(self):
        """Test creating a supervisor report."""
        report = SupervisorReport(
            timestamp=datetime.now(),
            pool_id="test-pool",
            pool_status="execute",
            total_beads=10,
            completed_beads=3,
            stuck_work=[],
            queue_depths={"attacker": 2, "defender": 3},
            escalations=[],
        )

        assert report.pool_id == "test-pool"
        assert report.total_beads == 10
        assert report.completed_beads == 3
        assert report.queue_depths["attacker"] == 2

    def test_has_issues_false_when_healthy(self):
        """Test has_issues is False for healthy pool."""
        report = SupervisorReport(
            timestamp=datetime.now(),
            pool_id="test-pool",
            pool_status="execute",
            total_beads=5,
            completed_beads=2,
            stuck_work=[],
            queue_depths={},
            escalations=[],
            timed_out_claims=0,
        )

        assert report.has_issues is False

    def test_has_issues_true_with_stuck_work(self):
        """Test has_issues is True when stuck work exists."""
        stuck = StuckWorkReport(
            pool_id="p1",
            bead_id="b1",
            agent_role="attacker",
            in_progress_since=datetime.now(),
            stuck_minutes=60,
            failure_count=0,
            recommended_action="WAIT",
        )
        report = SupervisorReport(
            timestamp=datetime.now(),
            pool_id="test-pool",
            pool_status="execute",
            total_beads=5,
            completed_beads=2,
            stuck_work=[stuck],
            queue_depths={},
            escalations=[],
        )

        assert report.has_issues is True

    def test_has_issues_true_with_escalations(self):
        """Test has_issues is True when escalations exist."""
        report = SupervisorReport(
            timestamp=datetime.now(),
            pool_id="test-pool",
            pool_status="execute",
            total_beads=5,
            completed_beads=2,
            stuck_work=[],
            queue_depths={},
            escalations=["bead-1"],
        )

        assert report.has_issues is True

    def test_completion_ratio(self):
        """Test completion ratio calculation."""
        report = SupervisorReport(
            timestamp=datetime.now(),
            pool_id="test-pool",
            pool_status="execute",
            total_beads=10,
            completed_beads=4,
            stuck_work=[],
            queue_depths={},
            escalations=[],
        )

        assert report.completion_ratio == 0.4

    def test_completion_ratio_empty_pool(self):
        """Test completion ratio for empty pool."""
        report = SupervisorReport(
            timestamp=datetime.now(),
            pool_id="test-pool",
            pool_status="execute",
            total_beads=0,
            completed_beads=0,
            stuck_work=[],
            queue_depths={},
            escalations=[],
        )

        assert report.completion_ratio == 1.0

    def test_summary(self):
        """Test human-readable summary generation."""
        report = SupervisorReport(
            timestamp=datetime.now(),
            pool_id="test-pool",
            pool_status="execute",
            total_beads=10,
            completed_beads=5,
            stuck_work=[],
            queue_depths={"attacker": 2, "defender": 1},
            escalations=[],
        )

        summary = report.summary()
        assert "test-pool" in summary
        assert "5/10" in summary
        assert "50%" in summary

    def test_serialization(self):
        """Test report serialization."""
        report = SupervisorReport(
            timestamp=datetime.now(),
            pool_id="test-pool",
            pool_status="execute",
            total_beads=5,
            completed_beads=2,
            stuck_work=[],
            queue_depths={"attacker": 1},
            escalations=["bead-1"],
            timed_out_claims=1,
        )

        data = report.to_dict()
        restored = SupervisorReport.from_dict(data)

        assert restored.pool_id == report.pool_id
        assert restored.total_beads == report.total_beads
        assert restored.escalations == report.escalations
        assert restored.timed_out_claims == report.timed_out_claims


# ============================================================================
# SupervisorAgent Tests
# ============================================================================


class TestSupervisorAgent:
    """Tests for SupervisorAgent."""

    def test_init(self, mock_pool_manager, empty_inboxes):
        """Test supervisor initialization."""
        supervisor = SupervisorAgent(mock_pool_manager, empty_inboxes)

        assert supervisor.pool_manager == mock_pool_manager
        assert supervisor.inboxes == empty_inboxes
        assert supervisor.config.log_only is True

    def test_init_with_custom_config(self, mock_pool_manager, empty_inboxes):
        """Test supervisor with custom configuration."""
        config = SupervisorConfig(stuck_threshold_minutes=10)
        supervisor = SupervisorAgent(mock_pool_manager, empty_inboxes, config)

        assert supervisor.config.stuck_threshold_minutes == 10

    def test_check_pool_no_issues(self, mock_pool_manager, empty_inboxes):
        """Healthy pool should report no stuck work."""
        supervisor = SupervisorAgent(mock_pool_manager, empty_inboxes)

        with patch.object(supervisor, '_is_bead_complete', return_value=False):
            report = supervisor.check_pool("test-pool")

        assert report.pool_id == "test-pool"
        assert len(report.stuck_work) == 0
        assert len(report.escalations) == 0

    def test_check_pool_not_found(self, mock_pool_manager, empty_inboxes):
        """Should raise error for non-existent pool."""
        mock_pool_manager.get_pool.return_value = None
        supervisor = SupervisorAgent(mock_pool_manager, empty_inboxes)

        with pytest.raises(ValueError, match="Pool not found"):
            supervisor.check_pool("nonexistent-pool")

    def test_check_pool_reports_queue_depths(self, mock_pool_manager, inboxes_with_work):
        """Should report queue depths for all roles."""
        supervisor = SupervisorAgent(mock_pool_manager, inboxes_with_work)

        with patch.object(supervisor, '_is_bead_complete', return_value=False):
            report = supervisor.check_pool("test-pool")

        assert "attacker" in report.queue_depths
        assert "defender" in report.queue_depths
        assert "verifier" in report.queue_depths
        # Each inbox has 3 beads assigned
        assert report.queue_depths["attacker"] == 3
        assert report.queue_depths["defender"] == 3

    def test_detect_stuck_work(self, mock_pool_manager, mock_bead):
        """Should detect work exceeding stuck threshold."""
        # Create inbox with work in progress
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(mock_bead)
        claim = inbox.claim_work()

        # Backdate the claim to simulate stuck work
        claim.claimed_at = datetime.now() - timedelta(minutes=60)
        inbox._in_progress[mock_bead.id] = claim

        inboxes = {AgentRole.ATTACKER: inbox}
        config = SupervisorConfig(stuck_threshold_minutes=30)
        supervisor = SupervisorAgent(mock_pool_manager, inboxes, config)

        with patch.object(supervisor, '_is_bead_complete', return_value=False):
            report = supervisor.check_pool("test-pool")

        assert len(report.stuck_work) == 1
        assert report.stuck_work[0].bead_id == mock_bead.id
        assert report.stuck_work[0].stuck_minutes >= 60

    def test_not_stuck_under_threshold(self, mock_pool_manager, mock_bead):
        """Work under threshold should not be flagged as stuck."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(mock_bead)
        claim = inbox.claim_work()

        # Work started only 10 minutes ago
        claim.claimed_at = datetime.now() - timedelta(minutes=10)
        inbox._in_progress[mock_bead.id] = claim

        inboxes = {AgentRole.ATTACKER: inbox}
        config = SupervisorConfig(stuck_threshold_minutes=30)
        supervisor = SupervisorAgent(mock_pool_manager, inboxes, config)

        with patch.object(supervisor, '_is_bead_complete', return_value=False):
            report = supervisor.check_pool("test-pool")

        assert len(report.stuck_work) == 0

    def test_escalation_after_failures(self, mock_pool_manager):
        """Should escalate beads that exceed failure threshold."""
        config = SupervisorConfig(escalate_after_failures=2)
        inbox = AgentInbox(AgentRole.ATTACKER)

        # Simulate multiple failures
        inbox._failure_counts["bead-1"] = 2
        inbox._failure_counts["bead-2"] = 1  # Not at threshold

        inboxes = {AgentRole.ATTACKER: inbox}
        supervisor = SupervisorAgent(mock_pool_manager, inboxes, config)

        with patch.object(supervisor, '_flag_for_human') as mock_flag:
            with patch.object(supervisor, '_is_bead_complete', return_value=False):
                report = supervisor.check_pool("test-pool")

            # Should flag bead-1 but not bead-2
            mock_flag.assert_called_once_with("test-pool", "bead-1")

        assert "bead-1" in report.escalations
        assert "bead-2" not in report.escalations

    def test_no_duplicate_escalation(self, mock_pool_manager):
        """Should not escalate same bead twice."""
        config = SupervisorConfig(escalate_after_failures=2)
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox._failure_counts["bead-1"] = 2

        inboxes = {AgentRole.ATTACKER: inbox}
        supervisor = SupervisorAgent(mock_pool_manager, inboxes, config)

        with patch.object(supervisor, '_flag_for_human') as mock_flag:
            with patch.object(supervisor, '_is_bead_complete', return_value=False):
                # First check should escalate
                report1 = supervisor.check_pool("test-pool")
                # Second check should not escalate again
                report2 = supervisor.check_pool("test-pool")

        # Should only be called once
        mock_flag.assert_called_once()
        assert "bead-1" in report1.escalations
        assert "bead-1" not in report2.escalations

    def test_log_only_no_intervention(self, mock_pool_manager, inboxes_with_work):
        """Supervisor should only log, not auto-intervene."""
        config = SupervisorConfig(log_only=True)
        supervisor = SupervisorAgent(mock_pool_manager, inboxes_with_work, config)

        # Record initial queue counts
        initial_counts = {
            role: inbox.pending_count
            for role, inbox in inboxes_with_work.items()
        }

        with patch.object(supervisor, '_is_bead_complete', return_value=False):
            supervisor.check_pool("test-pool")

        # Queue counts should be unchanged
        for role, inbox in inboxes_with_work.items():
            assert inbox.pending_count == initial_counts[role]

    def test_recommend_action_escalate(self, mock_pool_manager, mock_bead):
        """Should recommend escalation for beads with many failures."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(mock_bead)
        claim = inbox.claim_work()
        inbox._failure_counts[mock_bead.id] = 3

        config = SupervisorConfig(escalate_after_failures=3)
        inboxes = {AgentRole.ATTACKER: inbox}
        supervisor = SupervisorAgent(mock_pool_manager, inboxes, config)

        action = supervisor._recommend_action(claim, inbox)
        assert "ESCALATE" in action

    def test_recommend_action_monitor_retry(self, mock_pool_manager, mock_bead):
        """Should recommend monitoring for retrying beads."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(mock_bead)
        claim = inbox.claim_work()
        claim.attempt = 2  # Second attempt
        inbox._failure_counts[mock_bead.id] = 1

        config = SupervisorConfig(escalate_after_failures=3)
        inboxes = {AgentRole.ATTACKER: inbox}
        supervisor = SupervisorAgent(mock_pool_manager, inboxes, config)

        action = supervisor._recommend_action(claim, inbox)
        assert "MONITOR" in action

    def test_recommend_action_wait(self, mock_pool_manager, mock_bead):
        """Should recommend waiting for first attempt."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(mock_bead)
        claim = inbox.claim_work()
        claim.attempt = 1

        config = SupervisorConfig(escalate_after_failures=3)
        inboxes = {AgentRole.ATTACKER: inbox}
        supervisor = SupervisorAgent(mock_pool_manager, inboxes, config)

        action = supervisor._recommend_action(claim, inbox)
        assert "WAIT" in action

    def test_completed_beads_counted(self, mock_pool_manager, empty_inboxes):
        """Should correctly count completed beads."""
        # Mock _is_bead_complete to return True for some beads
        def is_complete(pool_id, bead_id):
            return bead_id in ["bead-1", "bead-3"]

        supervisor = SupervisorAgent(mock_pool_manager, empty_inboxes)

        with patch.object(supervisor, '_is_bead_complete', side_effect=is_complete):
            report = supervisor.check_pool("test-pool")

        # Pool has 3 beads, 2 are complete
        assert report.completed_beads == 2
        assert report.total_beads == 3

    def test_check_all_active_pools(self, mock_pool_manager, empty_inboxes):
        """Should check all active pools."""
        pool1 = MagicMock()
        pool1.id = "pool-1"
        pool1.bead_ids = []
        pool1.status = MagicMock()
        pool1.status.value = "execute"

        pool2 = MagicMock()
        pool2.id = "pool-2"
        pool2.bead_ids = []
        pool2.status = MagicMock()
        pool2.status.value = "verify"

        mock_pool_manager.get_active_pools.return_value = [pool1, pool2]
        mock_pool_manager.get_pool.side_effect = lambda pid: pool1 if pid == "pool-1" else pool2

        supervisor = SupervisorAgent(mock_pool_manager, empty_inboxes)

        with patch.object(supervisor, '_is_bead_complete', return_value=False):
            reports = supervisor.check_all_active_pools()

        assert len(reports) == 2
        assert any(r.pool_id == "pool-1" for r in reports)
        assert any(r.pool_id == "pool-2" for r in reports)

    def test_get_escalated_beads(self, mock_pool_manager):
        """Should track all escalated beads."""
        config = SupervisorConfig(escalate_after_failures=1)
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox._failure_counts["bead-1"] = 1
        inbox._failure_counts["bead-2"] = 1

        inboxes = {AgentRole.ATTACKER: inbox}
        supervisor = SupervisorAgent(mock_pool_manager, inboxes, config)

        with patch.object(supervisor, '_flag_for_human'):
            with patch.object(supervisor, '_is_bead_complete', return_value=False):
                supervisor.check_pool("test-pool")

        escalated = supervisor.get_escalated_beads()
        assert "bead-1" in escalated
        assert "bead-2" in escalated

    def test_clear_escalation_tracking(self, mock_pool_manager):
        """Should clear escalation tracking."""
        config = SupervisorConfig(escalate_after_failures=1)
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox._failure_counts["bead-1"] = 1

        inboxes = {AgentRole.ATTACKER: inbox}
        supervisor = SupervisorAgent(mock_pool_manager, inboxes, config)

        with patch.object(supervisor, '_flag_for_human'):
            with patch.object(supervisor, '_is_bead_complete', return_value=False):
                supervisor.check_pool("test-pool")

        assert len(supervisor.get_escalated_beads()) == 1

        supervisor.clear_escalation_tracking()

        assert len(supervisor.get_escalated_beads()) == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestSupervisorIntegration:
    """Integration tests with real components."""

    def test_full_workflow_with_mock_pool(self, tmp_path, mock_bead_factory):
        """Test full supervisor workflow."""
        from alphaswarm_sol.orchestration.pool import PoolManager
        from alphaswarm_sol.orchestration.schemas import Scope

        # Create real pool manager
        pool_dir = tmp_path / "pools"
        manager = PoolManager(pool_dir)

        # Create a pool
        scope = Scope(files=["contracts/Vault.sol"])
        pool = manager.create_pool(scope, pool_id="test-pool")
        manager.add_bead(pool.id, "bead-1")
        manager.add_bead(pool.id, "bead-2")

        # Create inboxes with work
        attacker_inbox = AgentInbox(AgentRole.ATTACKER)
        bead = mock_bead_factory("bead-1")
        attacker_inbox.assign(bead)

        # Claim work and backdate to simulate stuck
        claim = attacker_inbox.claim_work()
        claim.claimed_at = datetime.now() - timedelta(minutes=60)
        attacker_inbox._in_progress[bead.id] = claim

        inboxes = {AgentRole.ATTACKER: attacker_inbox}
        config = SupervisorConfig(stuck_threshold_minutes=30)
        supervisor = SupervisorAgent(manager, inboxes, config)

        # Run check
        with patch.object(supervisor, '_is_bead_complete', return_value=False):
            with patch.object(supervisor, '_flag_for_human'):
                report = supervisor.check_pool("test-pool")

        assert report.pool_id == "test-pool"
        assert report.total_beads == 2
        assert len(report.stuck_work) == 1
        assert report.stuck_work[0].bead_id == "bead-1"


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
