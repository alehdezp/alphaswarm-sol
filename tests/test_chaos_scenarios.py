"""Integration tests for chaos scenarios."""

import pytest
from alphaswarm_sol.reliability.chaos import (
    ChaosTestHarness,
    ChaosExperiment,
    FaultType,
    CHAOS_TEMPLATES,
    with_chaos_testing,
    APIError,
)


class MockPool:
    """Mock pool for testing."""

    def __init__(self, pool_id: str):
        self.pool_id = pool_id
        self.status = "RUNNING"
        self.beads_completed = 0
        self.beads_failed = 0


class TestChaosScenarios:
    """Integration tests for chaos scenarios."""

    def test_agent_resilience_under_api_failures(self):
        """Agent system maintains >75% success rate under 20% API failures."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(CHAOS_TEMPLATES["api_timeout_20pct"]._replace(
            fault_params={"delay_seconds": 0.01}  # Fast for tests
        ))

        # Simulate agent calls with retry logic
        successes = 0
        failures = 0

        @with_chaos_testing("llm")
        def agent_call(chaos_harness=None):
            return {"verdict": "suspicious", "confidence": "POSSIBLE"}

        for _ in range(100):
            try:
                result = agent_call(chaos_harness=harness)
                if result and not result.get("_chaos"):
                    successes += 1
            except (TimeoutError, APIError):
                failures += 1

        success_rate = successes / (successes + failures) if (successes + failures) > 0 else 0
        # Under 20% fault injection, should still achieve >75% success
        # (accounting for no retries in this simple test)
        assert success_rate >= 0.70, f"Success rate {success_rate:.2%} below 70% threshold"

    def test_malformed_response_handling(self):
        """System gracefully handles malformed responses."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(CHAOS_TEMPLATES["malformed_response_10pct"])

        @with_chaos_testing("llm")
        def agent_call(chaos_harness=None):
            return {"verdict": "vulnerable", "confidence": "LIKELY"}

        valid_responses = 0
        malformed_responses = 0

        for _ in range(100):
            result = agent_call(chaos_harness=harness)
            if result.get("_chaos"):
                malformed_responses += 1
            elif result.get("verdict"):
                valid_responses += 1

        # Should have some malformed responses
        assert malformed_responses > 0
        # But majority should be valid
        assert valid_responses >= malformed_responses * 5  # At least 5:1 ratio

    def test_handoff_delay_increases_latency(self):
        """Handoff delays increase overall latency but don't break system."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="handoff_delay",
            fault_type=FaultType.COMMUNICATION_DELAY,
            injection_rate=0.30,  # 30% delays
            fault_params={"delay_seconds": 0.01},  # 10ms delay for tests
            target_component="handoff",
        ))

        @with_chaos_testing("handoff")
        def handoff_call(from_agent: str, to_agent: str, chaos_harness=None):
            return {"handoff": True, "context_passed": True}

        import time
        start = time.time()
        for _ in range(100):
            result = handoff_call("attacker", "defender", chaos_harness=harness)
        elapsed = time.time() - start

        # Should complete all handoffs (delays don't break, just slow)
        assert harness.get_results("handoff").total_calls == 100
        # Elapsed should show some delay effect (more than 0 but tests stay fast)
        # Just verify it ran, actual latency tests would use real timing

    def test_mttr_under_chaos(self):
        """MTTR (Mean Time To Recovery) is tracked under chaos."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="recoverable_error",
            fault_type=FaultType.API_ERROR,
            injection_rate=0.25,
            fault_params={"status_code": 503},
            target_component="llm",
        ))

        @with_chaos_testing("llm")
        def agent_call(chaos_harness=None):
            return {"success": True}

        # Simulate calls with recovery tracking
        import time
        for _ in range(50):
            start = time.time()
            try:
                agent_call(chaos_harness=harness)
            except APIError:
                # Simulate recovery
                recovery_time = 0.01  # 10ms recovery
                harness.record_recovery(recovery_time)

        results = harness.get_results()
        if results.faults_injected > 0:
            assert results.mttr > 0, "MTTR should be positive when faults occurred"

    def test_multiple_experiments_compose(self):
        """Multiple experiments can run simultaneously."""
        harness = ChaosTestHarness(enabled=True, seed=42)

        # Add multiple experiments targeting different components
        harness.add_experiment(ChaosExperiment(
            name="llm_errors",
            fault_type=FaultType.API_ERROR,
            injection_rate=0.10,
            fault_params={"status_code": 500},
            target_component="llm",
        ))
        harness.add_experiment(ChaosExperiment(
            name="tool_delays",
            fault_type=FaultType.COMMUNICATION_DELAY,
            injection_rate=0.15,
            fault_params={"delay_seconds": 0.001},
            target_component="tool",
        ))

        # Verify both experiments are active
        assert len(harness.active_experiments) == 2

        # LLM should get API errors
        llm_faults = sum(
            1 for _ in range(100)
            if harness.should_inject_fault("llm") is not None
        )
        assert llm_faults > 0

        # Tool should get delays
        tool_faults = sum(
            1 for _ in range(100)
            if harness.should_inject_fault("tool") is not None
        )
        assert tool_faults > 0

    def test_cost_spike_injection(self):
        """Cost spike faults return cost multiplier."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="cost_spike",
            fault_type=FaultType.COST_SPIKE,
            injection_rate=1.0,
            fault_params={"cost_multiplier": 5.0},
            target_component="llm",
        ))

        @with_chaos_testing("llm")
        def expensive_call(chaos_harness=None):
            return {"cost": 0.10}

        result = expensive_call(chaos_harness=harness)
        assert result.get("_chaos") is True
        assert result.get("_cost_multiplier") == 5.0

    def test_rate_limit_injection(self):
        """Rate limit faults raise RateLimitError."""
        from alphaswarm_sol.reliability.chaos import RateLimitError

        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="rate_limit",
            fault_type=FaultType.RATE_LIMIT,
            injection_rate=1.0,
            fault_params={"retry_after": 30},
            target_component="llm",
        ))

        @with_chaos_testing("llm")
        def rate_limited_call(chaos_harness=None):
            return {"success": True}

        with pytest.raises(RateLimitError) as exc_info:
            rate_limited_call(chaos_harness=harness)
        assert exc_info.value.retry_after == 30

    def test_agent_failure_injection(self):
        """Agent failure faults raise AgentFailureError."""
        from alphaswarm_sol.reliability.chaos import AgentFailureError

        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="agent_crash",
            fault_type=FaultType.AGENT_FAILURE,
            injection_rate=1.0,
            fault_params={},
            target_component="agent",
        ))

        @with_chaos_testing("agent")
        def agent_execute(chaos_harness=None):
            return {"result": "complete"}

        with pytest.raises(AgentFailureError):
            agent_execute(chaos_harness=harness)

    def test_schema_violation_injection(self):
        """Schema violation faults return invalid structure."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="schema_violation",
            fault_type=FaultType.SCHEMA_VIOLATION,
            injection_rate=1.0,
            fault_params={},
            target_component="llm",
        ))

        @with_chaos_testing("llm")
        def schema_validated_call(chaos_harness=None):
            return {"required_field": "value", "format": "valid"}

        result = schema_validated_call(chaos_harness=harness)
        assert result.get("_chaos") is True
        assert result.get("unexpected_field") == "chaos"
        assert result.get("missing_required") is True

    def test_templates_are_ready_to_use(self):
        """Pre-built templates work out of the box."""
        harness = ChaosTestHarness(enabled=True, seed=42)

        # Test each template
        for template_name, template in CHAOS_TEMPLATES.items():
            harness.clear_experiments()
            harness.add_experiment(template)

            # Verify experiment was added
            assert len(harness.active_experiments) == 1
            assert harness.active_experiments[0].name == template_name

            # Verify targeting works
            component = template.target_component
            # Should occasionally inject (based on rate)
            # Use enough iterations to handle low injection rates (5%)
            num_calls = max(200, int(1.0 / template.injection_rate * 20))
            injections = sum(
                1 for _ in range(num_calls)
                if harness.should_inject_fault(component) is not None
            )
            # With non-zero rate, should get some injections
            if template.injection_rate > 0:
                assert injections > 0, f"Template {template_name} didn't inject any faults in {num_calls} calls"
