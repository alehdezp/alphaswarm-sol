"""
Tests for P0-T0d: Efficiency Metrics & Feedback Loop

Tests telemetry collection, metrics analysis, drift detection,
and continuous feedback loop.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from alphaswarm_sol.llm.telemetry import (
    TelemetryCollector,
    AnalysisEvent,
    SessionMetrics,
    TriageLevel,
    Verdict,
    get_collector,
)
from alphaswarm_sol.llm.metrics import (
    MetricsAnalyzer,
    DriftDetector,
    FeedbackLoop,
    DriftAlert,
    MetricsTrend,
)


# Test Fixtures

@pytest.fixture
def temp_storage():
    """Create temporary storage for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test_telemetry.jsonl")
        yield storage_path


@pytest.fixture
def collector(temp_storage):
    """Create telemetry collector."""
    return TelemetryCollector(storage_path=temp_storage)


@pytest.fixture
def sample_event():
    """Create sample analysis event."""
    return AnalysisEvent(
        event_id="evt_001",
        timestamp=datetime.now(),
        session_id="sess_001",
        function_id="fn_withdraw",
        contract_name="TestContract",
        source_tokens=500,
        triage_level=TriageLevel.DEEP,
        triage_reason="high reentrancy risk",
        context_tokens=100,
        compression_ratio=5.0,
        context_tier=3,
        provider="google",
        model="gemini-2.0-flash",
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=1200,
        cached=False,
        cost_usd=0.00015,
        verdict=Verdict.VULNERABLE,
        confidence=0.92,
        findings=[{"type": "reentrancy", "severity": "critical"}],
        ground_truth=Verdict.VULNERABLE,
    )


# Telemetry Tests

class TestTelemetryCollector:
    """Test telemetry collection."""

    def test_start_session(self, collector):
        """Should create new session with unique ID."""
        session_id = collector.start_session()

        assert session_id is not None
        assert isinstance(session_id, str)
        assert collector.current_session is not None
        assert collector.current_session.session_id == session_id

    def test_record_event(self, collector, sample_event):
        """Should record event and update session."""
        collector.start_session()
        collector.record_event(sample_event)

        assert len(collector.events) == 1
        assert collector.current_session.functions_analyzed == 1
        assert collector.current_session.total_tokens == 150  # 100 + 50
        assert collector.current_session.level_3_deep == 1

    def test_quality_metrics_update(self, collector, sample_event):
        """Should update quality metrics with ground truth."""
        collector.start_session()
        collector.record_event(sample_event)

        session = collector.current_session
        assert session.true_positives == 1  # Predicted vulnerable, actually vulnerable
        assert session.precision == 1.0
        assert session.recall == 1.0

    def test_false_positive(self, collector, sample_event):
        """Should track false positives."""
        collector.start_session()
        sample_event.ground_truth = Verdict.SAFE  # Actually safe
        collector.record_event(sample_event)

        session = collector.current_session
        assert session.false_positives == 1
        assert session.precision == 0.0

    def test_false_negative(self, collector, sample_event):
        """Should track false negatives."""
        collector.start_session()
        sample_event.verdict = Verdict.SAFE  # Predicted safe
        sample_event.ground_truth = Verdict.VULNERABLE  # Actually vulnerable
        collector.record_event(sample_event)

        session = collector.current_session
        assert session.false_negatives == 1
        assert session.recall == 0.0

    def test_end_session(self, collector, sample_event):
        """Should finalize session metrics."""
        session_id = collector.start_session()
        collector.record_event(sample_event)

        session = collector.end_session()

        assert session is not None
        assert session.end_time is not None
        assert session.session_id == session_id

    def test_session_metrics_properties(self, collector):
        """Should calculate derived metrics correctly."""
        collector.start_session()

        # Add true positive
        evt1 = AnalysisEvent(
            event_id="evt_1",
            timestamp=datetime.now(),
            session_id=collector.current_session.session_id,
            function_id="fn_1",
            contract_name="Test",
            source_tokens=100,
            triage_level=TriageLevel.DEEP,
            triage_reason="test",
            context_tokens=50,
            compression_ratio=2.0,
            context_tier=2,
            provider="google",
            model="gemini",
            prompt_tokens=50,
            completion_tokens=25,
            latency_ms=1000,
            cached=True,
            cost_usd=0.0001,
            verdict=Verdict.VULNERABLE,
            confidence=0.9,
            ground_truth=Verdict.VULNERABLE
        )
        collector.record_event(evt1)

        session = collector.current_session
        assert session.skip_rate == 0.0
        assert session.cost_per_function == 0.0001
        assert session.avg_latency_ms == 1000.0
        assert session.cache_hit_rate == 1.0
        assert session.cost_per_true_positive == 0.0001

    def test_persistence(self, collector, sample_event):
        """Should persist events to storage."""
        collector.start_session()
        collector.record_event(sample_event)

        assert os.path.exists(collector.storage_path)

        # Should be able to reload
        loaded = collector.load_events()
        assert len(loaded) == 1
        assert loaded[0].event_id == sample_event.event_id


# Metrics Analyzer Tests

class TestMetricsAnalyzer:
    """Test metrics analysis."""

    def test_analyze_session(self, collector, sample_event):
        """Should analyze session and generate insights."""
        collector.start_session()
        collector.record_event(sample_event)
        session = collector.current_session

        analyzer = MetricsAnalyzer(collector)
        analysis = analyzer.analyze_session(session)

        assert "quality" in analysis
        assert "efficiency" in analysis
        assert "distribution" in analysis
        assert analysis["quality"]["precision"] == 1.0
        assert analysis["efficiency"]["cache_hit_rate"] == 0.0

    def test_compute_trend(self, collector):
        """Should compute trends over time window."""
        collector.start_session()

        # Add multiple events with varying confidence
        for i in range(10):
            evt = AnalysisEvent(
                event_id=f"evt_{i}",
                timestamp=datetime.now() - timedelta(hours=i),
                session_id=collector.current_session.session_id,
                function_id=f"fn_{i}",
                contract_name="Test",
                source_tokens=100,
                triage_level=TriageLevel.QUICK,
                triage_reason="test",
                context_tokens=50,
                compression_ratio=2.0,
                context_tier=1,
                provider="google",
                model="gemini",
                prompt_tokens=50,
                completion_tokens=25,
                latency_ms=1000 + i*100,
                cached=False,
                cost_usd=0.0001,
                verdict=Verdict.SAFE,
                confidence=0.8 + i*0.01
            )
            collector.record_event(evt)

        analyzer = MetricsAnalyzer(collector)
        trend = analyzer.compute_trend("confidence", window_days=1)

        assert trend is not None
        assert len(trend.values) == 10
        assert trend.mean > 0.8
        assert trend.trend_direction in ["increasing", "decreasing", "stable"]


# Drift Detector Tests

class TestDriftDetector:
    """Test drift detection."""

    def test_no_drift(self):
        """Should not alert when metrics are stable."""
        baseline = {"precision": 0.85, "recall": 0.80, "f1": 0.82}
        detector = DriftDetector(baseline)

        current = {"precision": 0.86, "recall": 0.81, "f1": 0.83}
        alerts = detector.check(current)

        assert len(alerts) == 0

    def test_warning_drift(self):
        """Should alert on warning-level drift."""
        baseline = {"precision": 0.85, "recall": 0.80}
        detector = DriftDetector(baseline)

        current = {"precision": 0.80, "recall": 0.75}  # ~6% drift
        alerts = detector.check(current)

        assert len(alerts) == 2
        assert all(a.severity == "warning" for a in alerts)

    def test_critical_drift(self):
        """Should alert on critical-level drift."""
        baseline = {"precision": 0.85, "recall": 0.80}
        detector = DriftDetector(baseline)

        current = {"precision": 0.75, "recall": 0.70}  # >10% drift
        alerts = detector.check(current)

        assert len(alerts) == 2
        assert all(a.severity == "critical" for a in alerts)

    def test_drift_direction(self):
        """Should detect both increasing and decreasing drift."""
        baseline = {"cost_per_function": 0.001}
        detector = DriftDetector(baseline)

        current = {"cost_per_function": 0.002}  # 100% increase
        alerts = detector.check(current)

        assert len(alerts) == 1
        assert alerts[0].drift_pct == 1.0  # 100% drift

    def test_update_baseline(self):
        """Should allow updating baseline."""
        baseline = {"precision": 0.85}
        detector = DriftDetector(baseline)

        new_baseline = {"precision": 0.90}
        detector.set_baseline(new_baseline)

        current = {"precision": 0.89}
        alerts = detector.check(current)

        # Should now compare against 0.90, so minimal drift
        assert len(alerts) == 0

    def test_get_alerts_by_severity(self):
        """Should filter alerts by severity."""
        baseline = {"precision": 0.85, "recall": 0.80}
        detector = DriftDetector(baseline)

        current = {"precision": 0.80, "recall": 0.65}  # Warning and critical
        detector.check(current)

        critical_alerts = detector.get_alerts(severity="critical")
        warning_alerts = detector.get_alerts(severity="warning")

        assert len(critical_alerts) >= 1
        assert len(warning_alerts) >= 1


# Feedback Loop Tests

class TestFeedbackLoop:
    """Test continuous feedback loop."""

    def test_run_cycle(self, collector, sample_event):
        """Should run complete feedback cycle."""
        collector.start_session()
        collector.record_event(sample_event)

        baseline = {
            "precision": 0.85,
            "recall": 0.80,
            "f1": 0.82,
            "cost_per_function": 0.0001,
            "avg_latency_ms": 1000.0,
            "fp_rate": 0.02,
            "skip_rate": 0.40,
        }
        loop = FeedbackLoop(collector, baseline)

        result = loop.run_cycle()

        assert "analysis" in result
        assert "alerts" in result
        assert "recommendations" in result

    def test_generates_recommendations(self, collector):
        """Should generate actionable recommendations."""
        collector.start_session()

        # Add events that will trigger recommendations
        for i in range(10):
            evt = AnalysisEvent(
                event_id=f"evt_{i}",
                timestamp=datetime.now(),
                session_id=collector.current_session.session_id,
                function_id=f"fn_{i}",
                contract_name="Test",
                source_tokens=100,
                triage_level=TriageLevel.QUICK,  # Not skipping much
                triage_reason="test",
                context_tokens=50,
                compression_ratio=2.0,
                context_tier=1,
                provider="google",
                model="gemini",
                prompt_tokens=50,
                completion_tokens=25,
                latency_ms=1000,
                cached=False,  # Low cache hit
                cost_usd=0.01,  # High cost
                verdict=Verdict.VULNERABLE,
                confidence=0.9,
                ground_truth=Verdict.SAFE  # False positive
            )
            collector.record_event(evt)

        baseline = {"precision": 0.90, "skip_rate": 0.50}
        loop = FeedbackLoop(collector, baseline)
        result = loop.run_cycle()

        recs = result["recommendations"]
        assert len(recs) > 0
        # Should recommend improving precision and skip rate
        assert any("Precision" in r or "precision" in r for r in recs)

    def test_apply_tuning(self, collector):
        """Should record tuning history."""
        baseline = {"precision": 0.85}
        loop = FeedbackLoop(collector, baseline)

        adjustments = {
            "triage_threshold": 0.7,
            "compression_tier": 2,
        }
        loop.apply_tuning(adjustments)

        assert len(loop.improvement_history) == 1
        assert loop.improvement_history[0]["adjustments"] == adjustments


# Integration Tests

class TestMetricsIntegration:
    """Test full metrics pipeline integration."""

    def test_end_to_end_workflow(self, collector):
        """Should support complete analysis workflow."""
        # Start session
        session_id = collector.start_session()

        # Record multiple events
        for i in range(20):
            level = [TriageLevel.SKIP, TriageLevel.QUICK, TriageLevel.FOCUSED, TriageLevel.DEEP][i % 4]
            is_vuln = i % 3 == 0

            evt = AnalysisEvent(
                event_id=f"evt_{i}",
                timestamp=datetime.now(),
                session_id=session_id,
                function_id=f"fn_{i}",
                contract_name=f"Contract_{i//5}",
                source_tokens=100 * (i % 4 + 1),
                triage_level=level,
                triage_reason="automated test",
                context_tokens=50,
                compression_ratio=4.0,
                context_tier=level.value if level != TriageLevel.SKIP else 0,
                provider="google",
                model="gemini",
                prompt_tokens=50 if level != TriageLevel.SKIP else 0,
                completion_tokens=25 if level != TriageLevel.SKIP else 0,
                latency_ms=1000 if level != TriageLevel.SKIP else 0,
                cached=i % 2 == 0,
                cost_usd=0.0001 if level != TriageLevel.SKIP else 0.0,
                verdict=Verdict.VULNERABLE if is_vuln else Verdict.SAFE,
                confidence=0.85 + (i % 10) * 0.01,
                ground_truth=Verdict.VULNERABLE if is_vuln else Verdict.SAFE
            )
            collector.record_event(evt)

        # End session
        session = collector.end_session()

        # Analyze
        analyzer = MetricsAnalyzer(collector)
        analysis = analyzer.analyze_session(session)

        # Verify comprehensive metrics
        assert session.functions_analyzed == 20
        assert session.skip_rate > 0  # Some Level 0
        assert session.cache_hit_rate == 0.5  # Half cached
        assert analysis["quality"]["precision"] == 1.0  # All correct
        assert analysis["efficiency"]["skip_rate"] > 0

    def test_global_collector(self, temp_storage):
        """Should provide global collector instance."""
        collector1 = get_collector(temp_storage)
        collector2 = get_collector(temp_storage)

        # Should return same instance
        assert collector1 is collector2


# Success Criteria Tests

class TestSuccessCriteria:
    """Validate P0-T0d success criteria."""

    def test_tracks_quality_metrics(self, collector, sample_event):
        """Should track all required quality metrics."""
        collector.start_session()
        collector.record_event(sample_event)
        session = collector.current_session

        assert hasattr(session, "precision")
        assert hasattr(session, "recall")
        assert hasattr(session, "f1")
        assert hasattr(session, "false_positive_rate")

    def test_tracks_efficiency_metrics(self, collector, sample_event):
        """Should track all required efficiency metrics."""
        collector.start_session()
        collector.record_event(sample_event)
        session = collector.current_session

        assert hasattr(session, "skip_rate")
        assert hasattr(session, "cost_per_function")
        assert hasattr(session, "cost_per_true_positive")
        assert hasattr(session, "avg_latency_ms")
        assert hasattr(session, "cache_hit_rate")

    def test_persistence_survives_reload(self, collector, sample_event):
        """Should persist and reload telemetry data."""
        collector.start_session()
        collector.record_event(sample_event)

        # Create new collector with same storage
        new_collector = TelemetryCollector(storage_path=collector.storage_path)
        events = new_collector.load_events()

        assert len(events) == 1
        assert events[0].function_id == sample_event.function_id

    def test_drift_detection_works(self):
        """Should detect metric drift reliably."""
        baseline = {"precision": 0.85, "recall": 0.80}
        detector = DriftDetector(baseline)

        # No drift
        current1 = {"precision": 0.86, "recall": 0.81}
        assert len(detector.check(current1)) == 0

        # Warning drift
        current2 = {"precision": 0.80, "recall": 0.76}
        alerts = detector.check(current2)
        assert len(alerts) > 0
        assert all(a.severity in ["warning", "critical"] for a in alerts)
