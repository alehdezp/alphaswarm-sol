"""Tests for cost dashboards and budget enforcement.

Phase 7.1.3-06: Cost Dashboards & Budget Enforcement

Tests:
- CostLedger recording and aggregation
- Budget enforcement (hard/soft limits)
- Dashboard rendering (markdown, compact, TOON)
- Pool manager budget integration
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from alphaswarm_sol.metrics.cost_ledger import (
    CostLedger,
    CostEntry,
    PoolBudget,
    PoolCostSummary,
    PoolBudgetExceededError,
    get_pool_ledger,
    clear_pool_ledgers,
    get_all_pool_summaries,
)
from alphaswarm_sol.report.cost_dashboard import (
    render_cost_dashboard,
    render_summary_dashboard,
    render_multi_pool_dashboard,
    render_compact_summary,
    render_toon_summary,
)
from alphaswarm_sol.orchestration.pool import PoolManager
from alphaswarm_sol.orchestration.schemas import Scope


class TestCostLedger:
    """Tests for CostLedger class."""

    def test_basic_recording(self):
        """Test basic cost recording."""
        ledger = CostLedger(pool_id="test-pool")

        entry = ledger.record(
            agent_type="vrs-attacker",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
        )

        assert entry.pool_id == "test-pool"
        assert entry.agent_type == "vrs-attacker"
        assert entry.input_tokens == 1000
        assert entry.output_tokens == 500
        assert entry.cost_usd > 0

    def test_multiple_entries(self):
        """Test recording multiple entries."""
        ledger = CostLedger(pool_id="test-pool")

        ledger.record(agent_type="vrs-attacker", model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500)
        ledger.record(agent_type="vrs-defender", model="claude-3-5-sonnet", input_tokens=800, output_tokens=400)
        ledger.record(agent_type="vrs-verifier", model="claude-3-opus", input_tokens=500, output_tokens=200)

        assert len(ledger.get_entries()) == 3
        assert ledger.total_tokens == 3400  # 1500 + 1200 + 700
        assert ledger.total_cost > 0

    def test_bead_attribution(self):
        """Test cost attribution to beads."""
        ledger = CostLedger(pool_id="test-pool")

        ledger.record(agent_type="vrs-attacker", model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500, bead_id="VKG-001")
        ledger.record(agent_type="vrs-defender", model="claude-3-5-sonnet", input_tokens=800, output_tokens=400, bead_id="VKG-001")
        ledger.record(agent_type="vrs-attacker", model="claude-3-5-sonnet", input_tokens=500, output_tokens=200, bead_id="VKG-002")

        entries_001 = ledger.get_entries_for_bead("VKG-001")
        entries_002 = ledger.get_entries_for_bead("VKG-002")

        assert len(entries_001) == 2
        assert len(entries_002) == 1

    def test_summary_generation(self):
        """Test summary generation."""
        ledger = CostLedger(pool_id="test-pool")

        ledger.record(agent_type="vrs-attacker", model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500, bead_id="VKG-001")
        ledger.record(agent_type="vrs-defender", model="claude-3-haiku", input_tokens=800, output_tokens=400, bead_id="VKG-001")

        summary = ledger.summary()

        assert summary.pool_id == "test-pool"
        assert summary.total_requests == 2
        assert summary.total_input_tokens == 1800
        assert summary.total_output_tokens == 900
        assert "vrs-attacker" in summary.cost_by_agent
        assert "vrs-defender" in summary.cost_by_agent
        assert "claude-3-5-sonnet" in summary.cost_by_model
        assert "claude-3-haiku" in summary.cost_by_model
        assert "VKG-001" in summary.cost_by_bead

    def test_empty_ledger_summary(self):
        """Test summary for empty ledger."""
        ledger = CostLedger(pool_id="test-pool")
        summary = ledger.summary()

        assert summary.pool_id == "test-pool"
        assert summary.total_requests == 0
        assert summary.total_cost_usd == 0.0

    def test_serialization(self):
        """Test ledger serialization."""
        ledger = CostLedger(
            pool_id="test-pool",
            budget=PoolBudget(max_cost_usd=10.0)
        )
        ledger.record(agent_type="vrs-attacker", model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500)

        data = ledger.to_dict()
        restored = CostLedger.from_dict(data)

        assert restored.pool_id == ledger.pool_id
        assert restored.budget.max_cost_usd == 10.0
        assert len(restored.get_entries()) == 1


class TestBudgetEnforcement:
    """Tests for budget enforcement."""

    def test_budget_tracking(self):
        """Test budget tracking without enforcement."""
        budget = PoolBudget(max_cost_usd=1.0, hard_limit=False)
        ledger = CostLedger(pool_id="test-pool", budget=budget)

        ledger.record(agent_type="test", model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500)

        assert ledger.remaining_budget is not None
        assert ledger.remaining_budget < 1.0
        assert ledger.budget_utilization_pct is not None
        assert ledger.budget_utilization_pct > 0

    def test_hard_limit_enforcement(self):
        """Test hard limit budget enforcement."""
        # Create budget that will be exceeded with ~0.01 cost
        budget = PoolBudget(max_cost_usd=0.001, hard_limit=True)
        ledger = CostLedger(pool_id="test-pool", budget=budget)

        with pytest.raises(PoolBudgetExceededError) as exc_info:
            ledger.record(agent_type="test", model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500)

        assert exc_info.value.pool_id == "test-pool"
        assert exc_info.value.budget_usd == 0.001

    def test_soft_limit_warning(self):
        """Test soft limit warning (no exception)."""
        budget = PoolBudget(max_cost_usd=0.001, hard_limit=False)
        ledger = CostLedger(pool_id="test-pool", budget=budget)

        # Should not raise, just warn
        entry = ledger.record(agent_type="test", model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500)

        assert entry is not None
        summary = ledger.summary()
        assert len(summary.warnings) > 0
        assert "exceeded" in summary.warnings[0].lower()

    def test_warning_threshold(self):
        """Test budget warning threshold."""
        # Set budget so 80% threshold is triggered
        budget = PoolBudget(max_cost_usd=0.013, warn_threshold_pct=80.0, hard_limit=False)
        ledger = CostLedger(pool_id="test-pool", budget=budget)

        # This should trigger warning threshold
        ledger.record(agent_type="test", model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500)

        summary = ledger.summary()
        # Should have warning about approaching budget
        assert any("approaching" in w.lower() or "exceeded" in w.lower() for w in summary.warnings)

    def test_can_afford_check(self):
        """Test can_afford budget check."""
        budget = PoolBudget(max_cost_usd=0.05)
        ledger = CostLedger(pool_id="test-pool", budget=budget)

        # Should afford small cost
        assert ledger.can_afford(0.01)

        # Should not afford huge cost
        assert not ledger.can_afford(100.0)

    def test_check_budget(self):
        """Test check_budget returns tuple."""
        budget = PoolBudget(max_cost_usd=0.05)
        ledger = CostLedger(pool_id="test-pool", budget=budget)

        allowed, message = ledger.check_budget(0.01)
        assert allowed
        assert message == ""

        allowed, message = ledger.check_budget(100.0)
        assert not allowed
        assert "exceeded" in message.lower()


class TestPoolBudget:
    """Tests for PoolBudget configuration."""

    def test_default_values(self):
        """Test default budget values."""
        budget = PoolBudget()

        assert budget.max_cost_usd == 5.00
        assert budget.warn_threshold_pct == 80.0
        assert budget.hard_limit is True
        assert budget.warn_cost_usd == 4.00  # 80% of 5.00

    def test_custom_values(self):
        """Test custom budget values."""
        budget = PoolBudget(
            max_cost_usd=10.0,
            warn_threshold_pct=90.0,
            hard_limit=False
        )

        assert budget.max_cost_usd == 10.0
        assert budget.warn_threshold_pct == 90.0
        assert budget.hard_limit is False
        assert budget.warn_cost_usd == 9.0  # 90% of 10.00

    def test_serialization(self):
        """Test budget serialization."""
        budget = PoolBudget(max_cost_usd=15.0, hard_limit=False)
        data = budget.to_dict()
        restored = PoolBudget.from_dict(data)

        assert restored.max_cost_usd == 15.0
        assert restored.hard_limit is False


class TestDashboardRendering:
    """Tests for dashboard rendering functions."""

    @pytest.fixture
    def sample_ledger(self):
        """Create a sample ledger with data."""
        ledger = CostLedger(
            pool_id="test-pool",
            budget=PoolBudget(max_cost_usd=1.0)
        )
        ledger.record(agent_type="vrs-attacker", model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500, bead_id="VKG-001")
        ledger.record(agent_type="vrs-defender", model="claude-3-5-sonnet", input_tokens=800, output_tokens=400, bead_id="VKG-001")
        ledger.record(agent_type="vrs-verifier", model="claude-3-opus", input_tokens=500, output_tokens=200, bead_id="VKG-002")
        return ledger

    def test_render_cost_dashboard(self, sample_ledger):
        """Test full dashboard rendering."""
        dashboard = render_cost_dashboard(sample_ledger)

        assert "## Cost Dashboard: test-pool" in dashboard
        assert "Total Cost" in dashboard
        assert "Total Tokens" in dashboard
        assert "Budget" in dashboard
        assert "Cost by Agent" in dashboard
        assert "vrs-attacker" in dashboard
        assert "vrs-defender" in dashboard

    def test_render_with_entries(self, sample_ledger):
        """Test dashboard with entry list."""
        dashboard = render_cost_dashboard(sample_ledger, include_entries=True)

        assert "Recent Entries" in dashboard

    def test_render_summary_dashboard(self, sample_ledger):
        """Test summary-only dashboard."""
        summary = sample_ledger.summary()
        dashboard = render_summary_dashboard(summary)

        assert "## Cost Dashboard: test-pool" in dashboard
        assert "Total Cost" in dashboard

    def test_render_compact_summary(self, sample_ledger):
        """Test compact single-line summary."""
        summary = sample_ledger.summary()
        compact = render_compact_summary(summary)

        assert "test-pool:" in compact
        assert "$" in compact
        assert "tokens" in compact
        assert "requests" in compact

    def test_render_toon_summary(self, sample_ledger):
        """Test TOON format summary."""
        summary = sample_ledger.summary()
        toon = render_toon_summary(summary)

        assert "pool: test-pool" in toon
        assert "cost_usd:" in toon
        assert "tokens:" in toon

    def test_render_multi_pool_dashboard(self, sample_ledger):
        """Test multi-pool dashboard."""
        ledger2 = CostLedger(pool_id="other-pool")
        ledger2.record(agent_type="vrs-attacker", model="claude-3-haiku", input_tokens=500, output_tokens=200)

        dashboard = render_multi_pool_dashboard([sample_ledger, ledger2])

        assert "All Pools" in dashboard
        assert "test-pool" in dashboard
        assert "other-pool" in dashboard
        assert "Aggregate Summary" in dashboard

    def test_render_empty_multi_pool(self):
        """Test multi-pool with no pools."""
        dashboard = render_multi_pool_dashboard([])
        assert "No pools tracked" in dashboard


class TestPoolManagerBudget:
    """Tests for PoolManager budget integration."""

    @pytest.fixture
    def pool_manager(self):
        """Create a pool manager with temp storage."""
        with TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            yield manager

    def test_create_pool_with_budget(self, pool_manager):
        """Test creating pool with budget."""
        pool = pool_manager.create_pool_with_budget(
            scope=Scope(files=["test.sol"]),
            budget_usd=10.0,
            hard_limit=True
        )

        assert pool is not None
        assert "budget" in pool.metadata
        assert pool.metadata["budget"]["max_cost_usd"] == 10.0

    def test_record_cost_to_pool(self, pool_manager):
        """Test recording cost to pool."""
        pool = pool_manager.create_pool_with_budget(
            scope=Scope(files=["test.sol"]),
            budget_usd=10.0
        )

        result = pool_manager.record_cost(
            pool.id,
            agent_type="vrs-attacker",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500
        )

        assert result is True

        summary = pool_manager.get_cost_summary(pool.id)
        assert summary is not None
        assert summary.total_requests == 1

    def test_budget_exceeded_in_pool(self, pool_manager):
        """Test budget enforcement in pool."""
        pool = pool_manager.create_pool_with_budget(
            scope=Scope(files=["test.sol"]),
            budget_usd=0.001,  # Very small budget
            hard_limit=True
        )

        with pytest.raises(PoolBudgetExceededError):
            pool_manager.record_cost(
                pool.id,
                agent_type="vrs-attacker",
                model="claude-3-5-sonnet",
                input_tokens=10000,
                output_tokens=5000
            )

    def test_can_afford_check_in_pool(self, pool_manager):
        """Test can_afford via pool manager."""
        pool = pool_manager.create_pool_with_budget(
            scope=Scope(files=["test.sol"]),
            budget_usd=0.10
        )

        assert pool_manager.can_afford(pool.id, 0.01)
        assert not pool_manager.can_afford(pool.id, 100.0)

    def test_set_pool_budget(self, pool_manager):
        """Test setting budget on existing pool."""
        pool = pool_manager.create_pool(
            scope=Scope(files=["test.sol"])
        )

        result = pool_manager.set_pool_budget(
            pool.id,
            budget_usd=5.0,
            hard_limit=False
        )

        assert result is True

        # Verify budget was set
        summary = pool_manager.get_cost_summary(pool.id)
        assert summary is not None
        assert summary.budget_max_usd == 5.0

    def test_fail_pool_on_budget(self, pool_manager):
        """Test failing pool due to budget."""
        pool = pool_manager.create_pool_with_budget(
            scope=Scope(files=["test.sol"]),
            budget_usd=0.001,
            hard_limit=False  # Soft limit so we can record over budget
        )

        # Record over budget
        pool_manager.record_cost(
            pool.id,
            agent_type="test",
            model="claude-3-5-sonnet",
            input_tokens=10000,
            output_tokens=5000
        )

        # Fail the pool
        result = pool_manager.fail_pool_on_budget(pool.id)
        assert result is True

        # Verify pool is failed
        failed_pool = pool_manager.get_pool(pool.id)
        assert failed_pool is not None
        assert failed_pool.is_failed
        assert "budget" in failed_pool.metadata.get("failure_reason", "").lower()


class TestGlobalLedgerRegistry:
    """Tests for global ledger registry functions."""

    def setup_method(self):
        """Clear ledgers before each test."""
        clear_pool_ledgers()

    def test_get_pool_ledger(self):
        """Test getting/creating pool ledger."""
        ledger = get_pool_ledger("test-pool")
        assert ledger is not None
        assert ledger.pool_id == "test-pool"

        # Same ID returns same instance
        ledger2 = get_pool_ledger("test-pool")
        assert ledger is ledger2

    def test_get_pool_ledger_with_budget(self):
        """Test creating pool ledger with budget."""
        budget = PoolBudget(max_cost_usd=20.0)
        ledger = get_pool_ledger("test-pool", budget=budget)

        assert ledger.budget is not None
        assert ledger.budget.max_cost_usd == 20.0

    def test_get_all_pool_summaries(self):
        """Test getting summaries for all pools."""
        ledger1 = get_pool_ledger("pool-1")
        ledger2 = get_pool_ledger("pool-2")

        ledger1.record(agent_type="test", model="default", input_tokens=100, output_tokens=50)
        ledger2.record(agent_type="test", model="default", input_tokens=200, output_tokens=100)

        summaries = get_all_pool_summaries()

        assert len(summaries) == 2
        pool_ids = [s.pool_id for s in summaries]
        assert "pool-1" in pool_ids
        assert "pool-2" in pool_ids

    def test_clear_pool_ledgers(self):
        """Test clearing all pool ledgers."""
        get_pool_ledger("pool-1")
        get_pool_ledger("pool-2")

        clear_pool_ledgers()

        summaries = get_all_pool_summaries()
        assert len(summaries) == 0
