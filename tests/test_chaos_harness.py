"""Unit tests for ChaosTestHarness."""

import pytest
from alphaswarm_sol.reliability.chaos import (
    ChaosTestHarness,
    ChaosExperiment,
    FaultType,
    with_chaos_testing,
    APIError,
)


class TestChaosTestHarness:
    """Unit tests for ChaosTestHarness."""

    def test_harness_disabled_no_faults(self):
        """Disabled harness never injects faults."""
        harness = ChaosTestHarness(enabled=False)
        harness.add_experiment(ChaosExperiment(
            name="test",
            fault_type=FaultType.API_TIMEOUT,
            injection_rate=1.0,  # 100% injection
            fault_params={"delay_seconds": 1},
            target_component="llm",
        ))
        # Should return None even at 100% rate when disabled
        assert harness.should_inject_fault("llm") is None

    def test_harness_enabled_injects_at_rate(self):
        """Enabled harness injects at configured rate."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="test",
            fault_type=FaultType.API_ERROR,
            injection_rate=0.5,  # 50%
            fault_params={"status_code": 500},
            target_component="llm",
        ))

        # With seed=42, should have predictable injection pattern
        injections = sum(
            1 for _ in range(100)
            if harness.should_inject_fault("llm") is not None
        )
        # Should be roughly 50% (allow some variance)
        assert 40 <= injections <= 60

    def test_experiment_targets_specific_component(self):
        """Experiments only affect targeted component."""
        harness = ChaosTestHarness(enabled=True)
        harness.add_experiment(ChaosExperiment(
            name="llm_only",
            fault_type=FaultType.API_TIMEOUT,
            injection_rate=1.0,
            fault_params={"delay_seconds": 1},
            target_component="llm",
        ))

        # LLM should be targeted
        assert harness.should_inject_fault("llm") is not None
        # Tool should not be affected
        assert harness.should_inject_fault("tool") is None

    def test_decorator_injects_faults(self):
        """with_chaos_testing decorator injects faults."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="test",
            fault_type=FaultType.API_ERROR,
            injection_rate=1.0,
            fault_params={"status_code": 503},
            target_component="llm",
        ))

        @with_chaos_testing("llm")
        def mock_llm_call(prompt: str, chaos_harness=None):
            return {"response": "ok"}

        with pytest.raises(APIError) as exc_info:
            mock_llm_call("test", chaos_harness=harness)
        assert "503" in str(exc_info.value)

    def test_results_aggregation(self):
        """Results correctly aggregate fault counts."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="test",
            fault_type=FaultType.COMMUNICATION_DELAY,
            injection_rate=0.5,
            fault_params={"delay_seconds": 0.01},  # Fast for tests
            target_component="handoff",
        ))

        for _ in range(100):
            harness.should_inject_fault("handoff")

        results = harness.get_results("handoff")
        assert results.total_calls == 100
        assert results.faults_injected > 0
        assert 0 < results.success_rate < 1

    def test_remove_experiment(self):
        """Experiments can be removed by name."""
        harness = ChaosTestHarness(enabled=True)
        harness.add_experiment(ChaosExperiment(
            name="test1",
            fault_type=FaultType.API_ERROR,
            injection_rate=0.5,
            fault_params={"status_code": 500},
            target_component="llm",
        ))
        harness.add_experiment(ChaosExperiment(
            name="test2",
            fault_type=FaultType.API_TIMEOUT,
            injection_rate=0.3,
            fault_params={"delay_seconds": 1},
            target_component="tool",
        ))

        assert len(harness.active_experiments) == 2
        harness.remove_experiment("test1")
        assert len(harness.active_experiments) == 1
        assert harness.active_experiments[0].name == "test2"

    def test_clear_experiments(self):
        """All experiments can be cleared."""
        harness = ChaosTestHarness(enabled=True)
        harness.add_experiment(ChaosExperiment(
            name="test",
            fault_type=FaultType.API_ERROR,
            injection_rate=0.5,
            fault_params={"status_code": 500},
            target_component="llm",
        ))

        assert len(harness.active_experiments) == 1
        harness.clear_experiments()
        assert len(harness.active_experiments) == 0

    def test_malformed_response_injection(self):
        """Malformed responses are returned instead of raising."""
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="malformed",
            fault_type=FaultType.MALFORMED_RESPONSE,
            injection_rate=1.0,
            fault_params={"corruption_type": "json_syntax"},
            target_component="llm",
        ))

        @with_chaos_testing("llm")
        def mock_llm_call(chaos_harness=None):
            return {"response": "ok"}

        result = mock_llm_call(chaos_harness=harness)
        assert result.get("_chaos") is True
        assert result.get("error") == "malformed"

    def test_recovery_time_tracking(self):
        """Recovery times are recorded and aggregated."""
        harness = ChaosTestHarness(enabled=True)

        harness.record_recovery(10.5)
        harness.record_recovery(15.3)
        harness.record_recovery(8.2)

        results = harness.get_results()
        assert results.mttr > 0
        # MTTR should be average of recorded times
        expected_mttr = (10.5 + 15.3 + 8.2) / 3
        assert abs(results.mttr - expected_mttr) < 0.01
