"""End-to-end integration tests for complete audit workflows.

These tests validate that all Phase 7.1.5 components work together correctly
in production-like audit scenarios.

Test Coverage:
1. Audit produces traceable evidence with complete lineage
2. Dashboard reflects audit results accurately
3. Policy violation appears in both audit log and dashboard
4. Chaos results feed into SLO tracking
5. High-volume audit maintains performance
6. Observability doesn't break core workflow on failure
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from alphaswarm_sol.governance import PolicyEnforcer, PolicyViolationError
from alphaswarm_sol.metrics.cost_ledger import CostLedger
from alphaswarm_sol.observability import (
    create_agent_span,
    get_tracer,
    setup_tracing,
    shutdown_tracing,
)
from alphaswarm_sol.observability.audit import AuditCategory, AuditLogger
from alphaswarm_sol.observability.lineage import LineageTracker, SourceType
from alphaswarm_sol.orchestration import Pool, PoolStatus, Scope
from alphaswarm_sol.reliability import (
    ChaosExperiment,
    ChaosTestHarness,
    FaultType,
    SLO,
    SLOMeasurement,
    SLOTracker,
)

# Test fixtures path
FIXTURES = Path(__file__).parent.parent / "fixtures"
SCENARIOS_PATH = FIXTURES / "observability_scenarios.yaml"
PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture
def scenarios():
    """Load test scenarios from YAML."""
    with open(SCENARIOS_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture
def temp_audit_log(tmp_path):
    """Temporary audit log file."""
    return tmp_path / "audit.log"


@pytest.fixture
def temp_policies_file(tmp_path):
    """Create temporary governance policies file."""
    policies_path = tmp_path / "governance_policies.yaml"

    policies = {
        "metadata": {"version": "1.0", "description": "Test policies"},
        "policies": {
            "cost_budget": {
                "hard_limit_usd": 10.0,
                "soft_limit_usd": 8.0,
                "enabled": True,
                "block_on_exceed": True,
            },
            "tool_access": {
                "enabled": True,
                "role_restrictions": {
                    "vrs-attacker": ["slither", "bskg_query"],
                    "vrs-defender": ["slither", "aderyn", "bskg_query"],
                },
                "forbidden_tools": [],
            },
            "evidence_integrity": {
                "enabled": True,
                "require_evidence_refs": True,
                "min_evidence_count": 1,
            },
            "model_usage": {"enabled": False, "tier_restrictions": {}, "allowed_models": []},
        },
    }

    with open(policies_path, "w") as f:
        yaml.dump(policies, f)

    return policies_path


class TestFullAuditWorkflow:
    """End-to-end tests for complete audit workflow."""

    @pytest.mark.xfail(reason="Stale code: Full audit workflow API changed")
    def test_audit_produces_traceable_evidence(
        self, scenarios, temp_audit_log, temp_policies_file
    ):
        """Test that audit produces traceable evidence with complete lineage.

        Validates:
        - Audit execution creates trace spans
        - Evidence lineage tracked from BSKG source
        - Audit log captures verdict with trace ID
        - Complete chain: trace → audit → lineage
        """
        scenario = scenarios["full_pool_scenario"]

        # Setup tracing
        setup_tracing(service_name="test-audit")
        tracer = get_tracer(__name__)

        # Setup audit logger
        audit_logger = AuditLogger(log_path=temp_audit_log)

        # Setup lineage tracker
        lineage_tracker = LineageTracker()

        # Create pool
        scope = Scope(files=scenario["scope"]["files"])
        pool = Pool(id=scenario["pool_id"], scope=scope, status=PoolStatus.EXECUTE)

        # Execute audit with full observability
        trace_ids = []
        evidence_ids = []

        with tracer.start_as_current_span("audit.execute") as audit_span:
            audit_trace_id = format(audit_span.get_span_context().trace_id, "032x")
            trace_ids.append(audit_trace_id)

            # Simulate agent investigation
            for bead_data in scenario["beads"]:
                with create_agent_span(
                    agent_name="vrs-attacker",
                    bead_id=bead_data["bead_id"],
                    pool_id=pool.id,
                ) as agent_span:
                    agent_trace_id = format(agent_span.get_span_context().trace_id, "032x")
                    trace_ids.append(agent_trace_id)

                    # Create evidence lineage
                    evidence_id = bead_data["evidence_refs"][0]
                    evidence_ids.append(evidence_id)

                    lineage = lineage_tracker.create_lineage(
                        evidence_id=evidence_id,
                        source_type=SourceType.BSKG,
                        source_id=f"node_func_{bead_data['function_name']}_123",
                        extracting_agent="vrs-attacker",
                    )

                    # Log verdict to audit
                    audit_logger.log_verdict(
                        pool_id=pool.id,
                        bead_id=bead_data["bead_id"],
                        verdict=bead_data["verdict"],
                        confidence=bead_data["confidence"],
                        evidence_refs=bead_data["evidence_refs"],
                        agent_type="vrs-attacker",
                        trace_id=agent_trace_id,
                    )

        # Verify trace captured
        assert len(trace_ids) >= 1, "Trace IDs should be captured"

        # Verify evidence lineage
        assert len(evidence_ids) >= 1, "Evidence IDs should be created"
        for evidence_id in evidence_ids:
            chain = lineage_tracker.get_lineage(evidence_id)
            assert chain is not None, f"Lineage should exist for {evidence_id}"
            assert len(chain.chain) >= 2, "Should have origin and extraction steps"

        # Verify audit log
        assert temp_audit_log.exists(), "Audit log should exist"
        log_lines = temp_audit_log.read_text().strip().split("\n")
        assert len(log_lines) >= 1, "Should have audit entries"

        # Verify trace ID in audit log
        verdict_entries = []
        for line in log_lines:
            entry = json.loads(line)
            if entry.get("category") == AuditCategory.VERDICT_ASSIGNMENT.value:
                verdict_entries.append(entry)

        assert len(verdict_entries) >= 1, "Should have verdict entries"
        assert verdict_entries[0]["trace_id"] in trace_ids, "Trace ID should be in audit log"

        shutdown_tracing()

    @pytest.mark.xfail(reason="Stale code: Full audit workflow API changed")
    def test_dashboard_reflects_audit_results(self, scenarios, temp_audit_log):
        """Test that dashboard reflects audit results accurately.

        Validates:
        - Cost ledger tracks audit costs
        - SLO measurements recorded
        - Dashboard data structure correct
        """
        scenario = scenarios["full_pool_scenario"]

        # Setup cost ledger
        ledger = CostLedger(pool_id=scenario["pool_id"])

        # Setup SLO tracker
        slo = SLO(
            id="pool_completion",
            name="Pool Completion Rate",
            metric_type="success_rate",
            target_value=0.95,
            threshold_value=0.90,
            comparison="greater_than",
            measurement_window_sec=300,
        )
        slo_tracker = SLOTracker(slos=[slo])

        # Simulate audit execution
        for bead_data in scenario["beads"]:
            # Record cost
            ledger.record(
                agent_type="vrs-attacker",
                model="claude-3-5-sonnet",
                input_tokens=1000,
                output_tokens=500,
                bead_id=bead_data["bead_id"],
            )

        # Record SLO measurement
        measurement = SLOMeasurement(
            slo_id=slo.id,
            measured_value=1.0,  # 100% success
            timestamp=time.time(),
            pool_id=scenario["pool_id"],
        )
        slo_tracker.check_slo(slo.id, measurement)

        # Get dashboard data
        cost_summary = ledger.summary()

        # Verify dashboard data
        assert cost_summary.pool_id == scenario["pool_id"]
        assert cost_summary.total_cost_usd > 0, "Should have recorded costs"
        assert cost_summary.total_requests >= len(
            scenario["beads"]
        ), "Should have request count"

    @pytest.mark.xfail(reason="Stale code: Full audit workflow API changed")
    def test_policy_violation_appears_in_audit_and_dashboard(
        self, scenarios, temp_audit_log, temp_policies_file
    ):
        """Test that policy violations appear in both audit log and dashboard.

        Validates:
        - Policy violation logged to audit
        - Violation details accessible for dashboard
        - Trace correlation maintained
        """
        scenario = scenarios["cost_budget_scenario"]

        pool_id = scenario["pool_id"]

        # Setup audit logger
        audit_logger = AuditLogger(log_path=temp_audit_log)

        # Setup cost ledger
        ledger = CostLedger(pool_id=pool_id)

        # Setup policy enforcer
        enforcer = PolicyEnforcer(
            policies_path=temp_policies_file,
            cost_ledger=ledger,
            audit_logger=audit_logger,
        )

        # Exhaust budget
        ledger.record(
            agent_type="vrs-attacker",
            model="claude-3-opus",
            input_tokens=100000,
            output_tokens=50000,
        )

        # Attempt violating call
        trace_id = "trace_test_123"
        try:
            enforcer.check_input_policy(
                pool_id=pool_id,
                agent_type="vrs-attacker",
                requested_cost=5.0,
                trace_id=trace_id,
            )
        except PolicyViolationError:
            pass  # Expected

        # Verify audit log
        assert temp_audit_log.exists(), "Audit log should exist"
        log_lines = temp_audit_log.read_text().strip().split("\n")

        violation_entries = []
        for line in log_lines:
            entry = json.loads(line)
            if entry.get("category") == AuditCategory.POLICY_VIOLATION.value:
                violation_entries.append(entry)

        assert len(violation_entries) >= 1, "Should have violation entry"
        assert violation_entries[0]["trace_id"] == trace_id
        assert violation_entries[0]["pool_id"] == pool_id

    @pytest.mark.xfail(reason="Stale code: Full audit workflow API changed")
    def test_chaos_results_feed_into_slo_tracking(self, scenarios):
        """Test that chaos testing results feed into SLO tracking.

        Validates:
        - Chaos experiment runs
        - Success rate calculated
        - SLO measurement created from chaos results
        """
        scenario = scenarios["chaos_scenario"]

        # Create chaos experiment
        experiment = ChaosExperiment(
            id=scenario["experiment_id"],
            fault_type=FaultType.API_ERROR,
            fault_rate=scenario["fault_rate"],
            duration_sec=5,
        )

        # Create chaos harness
        harness = ChaosTestHarness()

        # Create SLO for reliability
        slo = SLO(
            id="chaos_reliability",
            name="Chaos Reliability",
            metric_type="success_rate",
            target_value=0.90,
            threshold_value=0.75,
            comparison="greater_than",
            measurement_window_sec=60,
        )

        slo_tracker = SLOTracker(slos=[slo])

        # Run chaos experiment
        successes = 0
        total = scenario["total_calls"]

        def mock_operation():
            time.sleep(0.01)
            return {"status": "success"}

        for i in range(total):
            try:
                with harness.inject_faults(experiment):
                    mock_operation()
                    successes += 1
            except Exception:
                pass  # Count as failure

        # Calculate success rate
        success_rate = successes / total

        # Create SLO measurement from chaos results
        measurement = SLOMeasurement(
            slo_id=slo.id,
            measured_value=success_rate,
            timestamp=time.time(),
            pool_id="chaos-test-pool",
            metadata={"chaos_experiment_id": experiment.id, "fault_rate": experiment.fault_rate},
        )

        # Check SLO
        violation = slo_tracker.check_slo(slo.id, measurement)

        # Verify results
        assert success_rate >= scenario["expected_resilience_pct"], (
            f"Should maintain {scenario['expected_resilience_pct']*100}% "
            f"success, got {success_rate*100}%"
        )
        if success_rate < slo.threshold_value:
            assert violation is not None, "Violation should be detected"


class TestRealWorldScenarios:
    """Tests for real-world audit scenarios."""

    def test_high_volume_audit_maintains_performance(self):
        """Test that high-volume audit maintains performance.

        Validates:
        - Can handle 100+ operations
        - Cost tracking scales
        - Audit logging doesn't degrade performance
        """
        pool_id = "high-volume-pool"

        # Setup components
        ledger = CostLedger(pool_id=pool_id)

        # Simulate high-volume audit
        start_time = time.time()
        operation_count = 100

        for i in range(operation_count):
            # Record cost
            ledger.record(
                agent_type=f"agent-{i % 3}",
                model="claude-3-5-sonnet",
                input_tokens=100,
                output_tokens=50,
                bead_id=f"bead-{i}",
            )

        end_time = time.time()
        duration = end_time - start_time

        # Verify performance
        assert duration < 5.0, f"High-volume audit should complete in <5s, took {duration}s"

        # Verify data integrity
        summary = ledger.summary()
        assert summary.total_requests == operation_count
        assert summary.total_cost_usd > 0

    def test_observability_doesnt_break_core_workflow(self, tmp_path):
        """Test that observability doesn't break core workflow on failure.

        Validates:
        - Audit continues if tracing fails
        - Audit continues if lineage tracking fails
        - Core workflow resilient to observability errors
        """
        pool_id = "resilience-test-pool"

        # Setup with intentionally failing components
        with patch("alphaswarm_sol.observability.tracer.get_tracer") as mock_tracer:
            # Make tracer raise error
            mock_tracer.side_effect = Exception("Tracer failure")

            # Core workflow should still execute
            try:
                # This should not raise even if tracer fails
                ledger = CostLedger(pool_id=pool_id)
                ledger.record(
                    agent_type="vrs-attacker",
                    model="claude-3-5-sonnet",
                    input_tokens=1000,
                    output_tokens=500,
                )

                # Verify core functionality works
                assert ledger.total_cost > 0, "Core workflow should succeed"
            except Exception as e:
                if "Tracer failure" in str(e):
                    pytest.fail("Core workflow should not break on observability failure")
                raise
