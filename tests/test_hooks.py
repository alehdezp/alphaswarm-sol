"""Tests for the hook system: prioritized queues, inboxes, and storage.

This module tests the hook system components per plan 05.2-02:
- PrioritizedBeadQueue: Priority ordering, deduplication
- AgentInbox: Work assignment, claiming, completion, failure
- HookStorage: State persistence

Usage:
    uv run pytest tests/test_hooks.py -v
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from alphaswarm_sol.agents.hooks import (
    AgentInbox,
    AgentRole,
    BeadPriority,
    HookStorage,
    InboxConfig,
    PrioritizedBead,
    PrioritizedBeadQueue,
    WorkClaim,
)
from alphaswarm_sol.beads.schema import (
    VulnerabilityBead,
    PatternContext,
    InvestigationGuide,
    TestContext,
)
from alphaswarm_sol.beads.types import CodeSnippet, InvestigationStep, Severity


# ============================================================================
# Fixtures
# ============================================================================


def make_bead(
    bead_id: str,
    severity: Severity = Severity.MEDIUM,
    why_flagged: str = "Test pattern matched",
    notes: list[str] | None = None,
    metadata: dict | None = None,
) -> VulnerabilityBead:
    """Create a test bead with specified properties."""
    return VulnerabilityBead(
        id=bead_id,
        vulnerability_class="test-vuln",
        pattern_id="test-001",
        severity=severity,
        confidence=0.8,
        vulnerable_code=CodeSnippet(
            source="function test() {}",
            file_path="Test.sol",
            start_line=1,
            end_line=1,
            function_name="test",
            contract_name="Test",
        ),
        related_code=[],
        full_contract=None,
        inheritance_chain=[],
        pattern_context=PatternContext(
            pattern_name="Test Pattern",
            pattern_description="Test description",
            why_flagged=why_flagged,
            matched_properties=["test_prop"],
            evidence_lines=[1],
        ),
        investigation_guide=InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Check",
                    look_for="Issue",
                    evidence_needed="Evidence",
                )
            ],
            questions_to_answer=["Is it vulnerable?"],
            common_false_positives=[],
            key_indicators=[],
            safe_patterns=[],
        ),
        test_context=TestContext(
            scaffold_code="// test",
            attack_scenario="Attack",
            setup_requirements=[],
            expected_outcome="Outcome",
        ),
        similar_exploits=[],
        fix_recommendations=[],
        notes=notes or [],
        metadata=metadata or {},
    )


@pytest.fixture
def critical_bead() -> VulnerabilityBead:
    """Create critical severity bead."""
    return make_bead("VKG-001", Severity.CRITICAL)


@pytest.fixture
def critical_exploitable_bead() -> VulnerabilityBead:
    """Create critical exploitable bead."""
    return make_bead(
        "VKG-002",
        Severity.CRITICAL,
        why_flagged="Exploitable reentrancy pattern found",
    )


@pytest.fixture
def high_bead() -> VulnerabilityBead:
    """Create high severity bead."""
    return make_bead("VKG-003", Severity.HIGH)


@pytest.fixture
def high_exploitable_bead() -> VulnerabilityBead:
    """Create high exploitable bead."""
    return make_bead(
        "VKG-004",
        Severity.HIGH,
        why_flagged="Exploitable access control bypass",
    )


@pytest.fixture
def medium_bead() -> VulnerabilityBead:
    """Create medium severity bead."""
    return make_bead("VKG-005", Severity.MEDIUM)


@pytest.fixture
def medium_tool_agreement_bead() -> VulnerabilityBead:
    """Create medium severity bead with tool agreement."""
    return make_bead(
        "VKG-006",
        Severity.MEDIUM,
        notes=["[tool_agreement] Slither and Mythril both flagged this"],
    )


@pytest.fixture
def low_bead() -> VulnerabilityBead:
    """Create low severity bead."""
    return make_bead("VKG-007", Severity.LOW)


# ============================================================================
# PrioritizedBeadQueue Tests
# ============================================================================


class TestPrioritizedBeadQueue:
    """Tests for PrioritizedBeadQueue."""

    def test_empty_queue(self):
        """Empty queue has len 0 and pop returns None."""
        q = PrioritizedBeadQueue()
        assert len(q) == 0
        assert q.pop() is None
        assert q.peek() is None
        assert not bool(q)

    def test_push_single_bead(self, critical_bead):
        """Single bead can be pushed and popped."""
        q = PrioritizedBeadQueue()
        q.push(critical_bead)
        assert len(q) == 1
        assert critical_bead.id in q
        assert bool(q)

        result = q.pop()
        assert result is not None
        assert result.id == critical_bead.id
        assert len(q) == 0

    def test_push_pop_priority_order(
        self,
        critical_bead,
        high_bead,
        medium_bead,
        low_bead,
    ):
        """Beads are popped in priority order: critical > high > medium > low."""
        q = PrioritizedBeadQueue()
        # Add in random order
        q.push(medium_bead)
        q.push(critical_bead)
        q.push(low_bead)
        q.push(high_bead)

        assert len(q) == 4

        # Should pop in priority order
        assert q.pop().severity == Severity.CRITICAL
        assert q.pop().severity == Severity.HIGH
        assert q.pop().severity == Severity.MEDIUM
        assert q.pop().severity == Severity.LOW
        assert len(q) == 0

    def test_duplicate_prevention(self, critical_bead):
        """Same bead ID should not be added twice."""
        q = PrioritizedBeadQueue()
        q.push(critical_bead)
        q.push(critical_bead)  # Duplicate
        assert len(q) == 1

    def test_contains_check(self, critical_bead, high_bead):
        """Contains check works correctly."""
        q = PrioritizedBeadQueue()
        q.push(critical_bead)

        assert critical_bead.id in q
        assert high_bead.id not in q

    def test_peek_without_remove(self, critical_bead, high_bead):
        """Peek returns top bead without removing."""
        q = PrioritizedBeadQueue()
        q.push(high_bead)
        q.push(critical_bead)

        # Peek should return critical
        top = q.peek()
        assert top is not None
        assert top.severity == Severity.CRITICAL
        assert len(q) == 2  # Still has both

        # Pop should also return critical
        popped = q.pop()
        assert popped is not None
        assert popped.severity == Severity.CRITICAL
        assert len(q) == 1

    def test_remove_bead(self, critical_bead, high_bead):
        """Remove bead by ID."""
        q = PrioritizedBeadQueue()
        q.push(critical_bead)
        q.push(high_bead)

        assert q.remove(critical_bead.id)
        assert critical_bead.id not in q
        assert len(q) == 1

        # Pop should return high now
        assert q.pop().severity == Severity.HIGH

    def test_remove_nonexistent(self, critical_bead):
        """Remove returns False for nonexistent bead."""
        q = PrioritizedBeadQueue()
        q.push(critical_bead)

        assert not q.remove("nonexistent")
        assert len(q) == 1

    def test_clear(self, critical_bead, high_bead):
        """Clear removes all beads."""
        q = PrioritizedBeadQueue()
        q.push(critical_bead)
        q.push(high_bead)
        assert len(q) == 2

        q.clear()
        assert len(q) == 0
        assert q.pop() is None

    def test_exploitability_priority(
        self,
        critical_bead,
        critical_exploitable_bead,
    ):
        """Exploitable beads within same severity prioritized."""
        q = PrioritizedBeadQueue()
        q.push(critical_bead)  # Not exploitable
        q.push(critical_exploitable_bead)  # Exploitable

        # Exploitable should come first
        first = q.pop()
        assert first is not None
        assert "exploitable" in first.pattern_context.why_flagged.lower()

    def test_tool_agreement_priority(
        self,
        medium_bead,
        medium_tool_agreement_bead,
    ):
        """Tool agreement beads prioritized within medium severity."""
        q = PrioritizedBeadQueue()
        q.push(medium_bead)  # No tool agreement
        q.push(medium_tool_agreement_bead)  # Has tool agreement

        # Tool agreement should come first (MEDIUM_TOOL_AGREEMENT < MEDIUM)
        first = q.pop()
        assert first is not None
        assert any("tool_agreement" in note for note in first.notes)

    def test_recency_tiebreaker(self):
        """Older beads should be processed first at same priority."""
        q = PrioritizedBeadQueue()

        # Add two medium beads
        bead1 = make_bead("VKG-A1", Severity.MEDIUM)
        bead2 = make_bead("VKG-A2", Severity.MEDIUM)

        q.push(bead1)
        q.push(bead2)

        # First added should come first (FIFO within priority)
        first = q.pop()
        assert first.id == "VKG-A1"

    def test_get_priority(self, critical_bead, low_bead):
        """Get priority without adding to queue."""
        q = PrioritizedBeadQueue()

        assert q.get_priority(critical_bead) == BeadPriority.CRITICAL
        assert q.get_priority(low_bead) == BeadPriority.LOW

    def test_repr(self, critical_bead):
        """String representation shows size."""
        q = PrioritizedBeadQueue()
        assert "size=0" in repr(q)

        q.push(critical_bead)
        assert "size=1" in repr(q)

    def test_metadata_exploitability(self):
        """Exploitability from metadata is detected."""
        bead = make_bead(
            "VKG-META",
            Severity.HIGH,
            metadata={"exploitable": True},
        )
        q = PrioritizedBeadQueue()
        assert q.get_priority(bead) == BeadPriority.HIGH_EXPLOITABLE

    def test_metadata_tool_count(self):
        """Tool count >= 2 from metadata triggers tool agreement."""
        bead = make_bead(
            "VKG-TOOLS",
            Severity.MEDIUM,
            metadata={"tool_count": 3},
        )
        q = PrioritizedBeadQueue()
        assert q.get_priority(bead) == BeadPriority.MEDIUM_TOOL_AGREEMENT


# ============================================================================
# AgentInbox Tests
# ============================================================================


class TestAgentInbox:
    """Tests for AgentInbox."""

    def test_create_inbox(self):
        """Create inbox with default config."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        assert inbox.agent_role == "attacker"
        assert inbox.pending_count == 0
        assert inbox.in_progress_count == 0
        assert inbox.is_empty

    def test_create_inbox_with_config(self):
        """Create inbox with custom config."""
        config = InboxConfig(max_queue_size=50, max_retries=5)
        inbox = AgentInbox(AgentRole.DEFENDER, config)
        assert inbox.config.max_queue_size == 50
        assert inbox.config.max_retries == 5

    def test_assign_and_claim(self, critical_bead):
        """Assigned bead can be claimed."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        assert inbox.assign(critical_bead)
        assert inbox.pending_count == 1

        claim = inbox.claim_work()
        assert claim is not None
        assert claim.bead.id == critical_bead.id
        assert claim.agent_role == "attacker"
        assert claim.attempt == 1
        assert inbox.pending_count == 0
        assert inbox.in_progress_count == 1

    def test_assign_duplicate(self, critical_bead):
        """Cannot assign same bead twice."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        assert inbox.assign(critical_bead)
        assert not inbox.assign(critical_bead)  # Duplicate
        assert inbox.pending_count == 1

    def test_assign_queue_full(self, critical_bead, high_bead):
        """Cannot assign when queue is full."""
        config = InboxConfig(max_queue_size=1)
        inbox = AgentInbox(AgentRole.ATTACKER, config)

        assert inbox.assign(critical_bead)
        assert not inbox.assign(high_bead)  # Queue full
        assert inbox.pending_count == 1

    def test_assign_many(self, critical_bead, high_bead, medium_bead):
        """Assign multiple beads at once."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        count = inbox.assign_many([critical_bead, high_bead, medium_bead])
        assert count == 3
        assert inbox.pending_count == 3

    def test_complete_work(self, critical_bead):
        """Mark work as completed."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        claim = inbox.claim_work()

        assert inbox.complete_work(claim.bead.id)
        assert inbox.in_progress_count == 0
        assert inbox.completed_count == 1

    def test_complete_work_not_in_progress(self, critical_bead):
        """Complete returns False if not in progress."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        assert not inbox.complete_work(critical_bead.id)

    def test_failure_requeue(self, critical_bead):
        """Failed work should be requeued."""
        config = InboxConfig(requeue_on_failure=True, max_retries=3)
        inbox = AgentInbox(AgentRole.ATTACKER, config)
        inbox.assign(critical_bead)

        claim = inbox.claim_work()
        escalate = inbox.fail_work(claim.bead.id)

        assert not escalate  # First failure, no escalation
        assert inbox.pending_count == 1  # Requeued
        assert inbox.in_progress_count == 0

    def test_failure_no_requeue(self, critical_bead):
        """With requeue disabled, failed work is not requeued."""
        config = InboxConfig(requeue_on_failure=False)
        inbox = AgentInbox(AgentRole.ATTACKER, config)
        inbox.assign(critical_bead)

        claim = inbox.claim_work()
        inbox.fail_work(claim.bead.id)

        assert inbox.pending_count == 0  # Not requeued
        assert inbox.in_progress_count == 0

    def test_failure_escalation(self, critical_bead):
        """Work should escalate after threshold failures."""
        config = InboxConfig(escalate_threshold=2, requeue_on_failure=True)
        inbox = AgentInbox(AgentRole.ATTACKER, config)
        inbox.assign(critical_bead)

        # First failure
        claim = inbox.claim_work()
        escalate = inbox.fail_work(claim.bead.id)
        assert not escalate

        # Second failure - should escalate
        claim = inbox.claim_work()
        escalate = inbox.fail_work(claim.bead.id)
        assert escalate

    def test_failure_attempt_tracking(self, critical_bead):
        """Attempt number is tracked across failures."""
        config = InboxConfig(requeue_on_failure=True, max_retries=5)
        inbox = AgentInbox(AgentRole.ATTACKER, config)
        inbox.assign(critical_bead)

        # First attempt
        claim1 = inbox.claim_work()
        assert claim1.attempt == 1
        inbox.fail_work(claim1.bead.id)

        # Second attempt
        claim2 = inbox.claim_work()
        assert claim2.attempt == 2

    def test_release_work(self, critical_bead):
        """Release work back to queue."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        claim = inbox.claim_work()

        assert inbox.release_work(claim.bead.id)
        assert inbox.pending_count == 1
        assert inbox.in_progress_count == 0

    def test_release_all(self, critical_bead, high_bead):
        """Release all in-progress work."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        inbox.assign(high_bead)
        inbox.claim_work()
        inbox.claim_work()

        assert inbox.in_progress_count == 2
        count = inbox.release_all()
        assert count == 2
        assert inbox.pending_count == 2
        assert inbox.in_progress_count == 0

    def test_get_claim(self, critical_bead):
        """Get claim for in-progress work."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        claim = inbox.claim_work()

        retrieved = inbox.get_claim(critical_bead.id)
        assert retrieved is not None
        assert retrieved.bead.id == claim.bead.id

    def test_get_failure_count(self, critical_bead):
        """Get failure count for a bead."""
        config = InboxConfig(requeue_on_failure=True)
        inbox = AgentInbox(AgentRole.ATTACKER, config)
        inbox.assign(critical_bead)

        assert inbox.get_failure_count(critical_bead.id) == 0

        claim = inbox.claim_work()
        inbox.fail_work(claim.bead.id)
        assert inbox.get_failure_count(critical_bead.id) == 1

    def test_timed_out_claims(self, critical_bead):
        """Get claims that exceeded timeout."""
        config = InboxConfig(timeout_seconds=1)
        inbox = AgentInbox(AgentRole.ATTACKER, config)
        inbox.assign(critical_bead)
        claim = inbox.claim_work()

        # Artificially set claimed_at to past
        claim.claimed_at = datetime.now() - timedelta(seconds=10)
        inbox._in_progress[critical_bead.id] = claim

        timed_out = inbox.get_timed_out_claims()
        assert len(timed_out) == 1
        assert timed_out[0].bead.id == critical_bead.id

    def test_has_work(self, critical_bead):
        """Check if inbox has pending work."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        assert not inbox.has_work

        inbox.assign(critical_bead)
        assert inbox.has_work

        inbox.claim_work()
        assert not inbox.has_work  # No longer pending

    def test_total_count(self, critical_bead, high_bead):
        """Total count includes pending and in-progress."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        inbox.assign(high_bead)
        assert inbox.total_count == 2

        inbox.claim_work()
        assert inbox.total_count == 2  # Still 2 total

    def test_to_dict(self, critical_bead):
        """Serialize inbox state."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        inbox.claim_work()

        state = inbox.to_dict()
        assert state["agent_role"] == "attacker"
        assert len(state["in_progress"]) == 1
        assert state["config"]["max_queue_size"] == 100


# ============================================================================
# HookStorage Tests
# ============================================================================


class TestHookStorage:
    """Tests for HookStorage."""

    def test_save_and_load_inbox(self, tmp_path, critical_bead, high_bead):
        """Save and load inbox state."""
        storage = HookStorage(tmp_path)
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        inbox.assign(high_bead)

        # Save
        path = storage.save_inbox(inbox, "pool-test")
        assert path.exists()

        # Create loader
        beads = {critical_bead.id: critical_bead, high_bead.id: high_bead}

        def loader(bead_id: str):
            return beads.get(bead_id)

        # Load
        loaded = storage.load_inbox("pool-test", AgentRole.ATTACKER, loader)
        assert loaded is not None
        assert loaded.pending_count == 2
        assert loaded.agent_role == "attacker"

    def test_load_nonexistent(self, tmp_path):
        """Load returns None for nonexistent inbox."""
        storage = HookStorage(tmp_path)
        loaded = storage.load_inbox("nonexistent", AgentRole.ATTACKER, lambda x: None)
        assert loaded is None

    def test_delete_inbox(self, tmp_path, critical_bead):
        """Delete saved inbox state."""
        storage = HookStorage(tmp_path)
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        storage.save_inbox(inbox, "pool-test")

        assert storage.delete_inbox("pool-test", AgentRole.ATTACKER)
        assert not storage.inbox_exists("pool-test", AgentRole.ATTACKER)

    def test_delete_nonexistent(self, tmp_path):
        """Delete returns False for nonexistent inbox."""
        storage = HookStorage(tmp_path)
        assert not storage.delete_inbox("nonexistent", AgentRole.ATTACKER)

    def test_delete_pool_hooks(self, tmp_path, critical_bead):
        """Delete all hooks for a pool."""
        storage = HookStorage(tmp_path)

        # Create inboxes for multiple roles
        for role in [AgentRole.ATTACKER, AgentRole.DEFENDER]:
            inbox = AgentInbox(role)
            inbox.assign(critical_bead)
            storage.save_inbox(inbox, "pool-test")

        count = storage.delete_pool_hooks("pool-test")
        assert count == 2

    def test_list_inboxes(self, tmp_path, critical_bead):
        """List saved inbox roles for a pool."""
        storage = HookStorage(tmp_path)

        for role in [AgentRole.ATTACKER, AgentRole.DEFENDER]:
            inbox = AgentInbox(role)
            inbox.assign(critical_bead)
            storage.save_inbox(inbox, "pool-test")

        roles = storage.list_inboxes("pool-test")
        assert len(roles) == 2
        assert "attacker" in roles
        assert "defender" in roles

    def test_list_pools(self, tmp_path, critical_bead):
        """List all pools with hook state."""
        storage = HookStorage(tmp_path)

        for pool_id in ["pool-a", "pool-b"]:
            inbox = AgentInbox(AgentRole.ATTACKER)
            inbox.assign(critical_bead)
            storage.save_inbox(inbox, pool_id)

        pools = storage.list_pools()
        assert len(pools) == 2
        assert "pool-a" in pools
        assert "pool-b" in pools

    def test_inbox_exists(self, tmp_path, critical_bead):
        """Check if inbox state exists."""
        storage = HookStorage(tmp_path)

        assert not storage.inbox_exists("pool-test", AgentRole.ATTACKER)

        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        storage.save_inbox(inbox, "pool-test")

        assert storage.inbox_exists("pool-test", AgentRole.ATTACKER)
        assert not storage.inbox_exists("pool-test", AgentRole.DEFENDER)

    def test_get_inbox_metadata(self, tmp_path, critical_bead, high_bead):
        """Get metadata without full load."""
        storage = HookStorage(tmp_path)
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        inbox.assign(high_bead)
        storage.save_inbox(inbox, "pool-test")

        meta = storage.get_inbox_metadata("pool-test", AgentRole.ATTACKER)
        assert meta is not None
        assert meta["agent_role"] == "attacker"
        assert meta["pending_count"] == 2
        assert meta["pool_id"] == "pool-test"

    def test_persistence_with_in_progress(self, tmp_path, critical_bead, high_bead):
        """In-progress work is persisted and restored."""
        storage = HookStorage(tmp_path)
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(critical_bead)
        inbox.assign(high_bead)
        inbox.claim_work()  # Move one to in-progress

        storage.save_inbox(inbox, "pool-test")

        beads = {critical_bead.id: critical_bead, high_bead.id: high_bead}
        loaded = storage.load_inbox(
            "pool-test",
            AgentRole.ATTACKER,
            lambda x: beads.get(x),
        )
        assert loaded is not None
        assert loaded.pending_count == 1
        assert loaded.in_progress_count == 1

    def test_persistence_with_failures(self, tmp_path, critical_bead):
        """Failure counts are persisted and restored."""
        config = InboxConfig(requeue_on_failure=True)
        storage = HookStorage(tmp_path)
        inbox = AgentInbox(AgentRole.ATTACKER, config)
        inbox.assign(critical_bead)

        # Fail twice
        claim = inbox.claim_work()
        inbox.fail_work(claim.bead.id)
        claim = inbox.claim_work()
        inbox.fail_work(claim.bead.id)

        storage.save_inbox(inbox, "pool-test")

        beads = {critical_bead.id: critical_bead}
        loaded = storage.load_inbox(
            "pool-test",
            AgentRole.ATTACKER,
            lambda x: beads.get(x),
        )
        assert loaded is not None
        assert loaded.get_failure_count(critical_bead.id) == 2


# ============================================================================
# WorkClaim Tests
# ============================================================================


class TestWorkClaim:
    """Tests for WorkClaim dataclass."""

    def test_is_first_attempt(self, critical_bead):
        """Check if first attempt."""
        claim = WorkClaim(
            bead=critical_bead,
            agent_role="attacker",
            claimed_at=datetime.now(),
            attempt=1,
        )
        assert claim.is_first_attempt

        claim2 = WorkClaim(
            bead=critical_bead,
            agent_role="attacker",
            claimed_at=datetime.now(),
            attempt=2,
        )
        assert not claim2.is_first_attempt

    def test_duration_seconds(self, critical_bead):
        """Get duration since claim."""
        claim = WorkClaim(
            bead=critical_bead,
            agent_role="attacker",
            claimed_at=datetime.now() - timedelta(seconds=10),
            attempt=1,
        )
        assert claim.duration_seconds >= 10

    def test_to_dict(self, critical_bead):
        """Serialize claim to dict."""
        claim = WorkClaim(
            bead=critical_bead,
            agent_role="attacker",
            claimed_at=datetime.now(),
            attempt=1,
        )
        data = claim.to_dict()
        assert data["bead_id"] == critical_bead.id
        assert data["agent_role"] == "attacker"
        assert data["attempt"] == 1


# ============================================================================
# InboxConfig Tests
# ============================================================================


class TestInboxConfig:
    """Tests for InboxConfig dataclass."""

    def test_default_values(self):
        """Default config values."""
        config = InboxConfig()
        assert config.max_queue_size == 100
        assert config.max_retries == 3
        assert config.requeue_on_failure is True
        assert config.escalate_threshold == 3
        assert config.timeout_seconds == 3600

    def test_custom_values(self):
        """Custom config values."""
        config = InboxConfig(
            max_queue_size=50,
            max_retries=5,
            requeue_on_failure=False,
            escalate_threshold=2,
            timeout_seconds=1800,
        )
        assert config.max_queue_size == 50
        assert config.max_retries == 5
        assert config.requeue_on_failure is False
        assert config.escalate_threshold == 2
        assert config.timeout_seconds == 1800

    def test_to_dict(self):
        """Serialize config to dict."""
        config = InboxConfig(max_queue_size=50)
        data = config.to_dict()
        assert data["max_queue_size"] == 50

    def test_from_dict(self):
        """Deserialize config from dict."""
        data = {"max_queue_size": 50, "max_retries": 5}
        config = InboxConfig.from_dict(data)
        assert config.max_queue_size == 50
        assert config.max_retries == 5


# ============================================================================
# BeadPriority Tests
# ============================================================================


class TestBeadPriority:
    """Tests for BeadPriority enum."""

    def test_priority_ordering(self):
        """Priorities are ordered correctly."""
        assert BeadPriority.CRITICAL_EXPLOITABLE < BeadPriority.CRITICAL
        assert BeadPriority.CRITICAL < BeadPriority.HIGH_EXPLOITABLE
        assert BeadPriority.HIGH_EXPLOITABLE < BeadPriority.HIGH
        assert BeadPriority.HIGH < BeadPriority.MEDIUM_TOOL_AGREEMENT
        assert BeadPriority.MEDIUM_TOOL_AGREEMENT < BeadPriority.MEDIUM
        assert BeadPriority.MEDIUM < BeadPriority.LOW

    def test_priority_values(self):
        """Priority values are integers 1-7."""
        assert BeadPriority.CRITICAL_EXPLOITABLE.value == 1
        assert BeadPriority.LOW.value == 7


# ============================================================================
# AgentRole Tests
# ============================================================================


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_role_values(self):
        """Role values are correct."""
        assert AgentRole.ATTACKER.value == "attacker"
        assert AgentRole.DEFENDER.value == "defender"
        assert AgentRole.VERIFIER.value == "verifier"
        assert AgentRole.COORDINATOR.value == "coordinator"
        assert AgentRole.SUPERVISOR.value == "supervisor"
