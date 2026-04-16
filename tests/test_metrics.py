"""Tests for metrics module.

Phase 8: Metrics & Observability
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from alphaswarm_sol.metrics import (
    MetricName,
    MetricStatus,
    MetricValue,
    MetricSnapshot,
    LOWER_IS_BETTER_METRICS,
    EventType,
    DetectionEvent,
    TimingEvent,
    ScaffoldEvent,
    VerdictEvent,
    EventStore,
    MetricsRecorder,
    get_recorder,
    event_from_dict,
    MetricCalculator,
    MetricsTracker,
)


class TestMetricTypes(unittest.TestCase):
    """Test metric type definitions (Task 8.0)."""

    def test_metric_names_count(self):
        """All 8 metrics defined."""
        self.assertEqual(len(MetricName), 8)

    def test_all_metric_names(self):
        """Verify all expected metric names exist."""
        expected = {
            "detection_rate",
            "false_positive_rate",
            "pattern_precision",
            "scaffold_compile_rate",
            "llm_autonomy",
            "time_to_detection",
            "token_efficiency",
            "escalation_rate",
        }
        actual = {m.value for m in MetricName}
        self.assertEqual(expected, actual)

    def test_metric_status_values(self):
        """All status values exist."""
        self.assertEqual(len(MetricStatus), 4)
        self.assertIn(MetricStatus.OK, MetricStatus)
        self.assertIn(MetricStatus.WARNING, MetricStatus)
        self.assertIn(MetricStatus.CRITICAL, MetricStatus)
        self.assertIn(MetricStatus.UNKNOWN, MetricStatus)


class TestMetricValueStatusHigherBetter(unittest.TestCase):
    """Test status evaluation for higher-is-better metrics."""

    def test_detection_rate_ok(self):
        """Detection rate above target is OK."""
        mv = MetricValue(
            name=MetricName.DETECTION_RATE,
            value=0.85,
            target=0.80,
            threshold_warning=0.70,
            threshold_critical=0.60,
        )
        self.assertEqual(mv.evaluate_status(), MetricStatus.OK)

    def test_detection_rate_warning(self):
        """Detection rate below target but above warning is WARNING."""
        mv = MetricValue(
            name=MetricName.DETECTION_RATE,
            value=0.75,
            target=0.80,
            threshold_warning=0.70,
            threshold_critical=0.60,
        )
        self.assertEqual(mv.evaluate_status(), MetricStatus.WARNING)

    def test_detection_rate_critical(self):
        """Detection rate below warning threshold is CRITICAL."""
        mv = MetricValue(
            name=MetricName.DETECTION_RATE,
            value=0.65,
            target=0.80,
            threshold_warning=0.70,
            threshold_critical=0.60,
        )
        self.assertEqual(mv.evaluate_status(), MetricStatus.CRITICAL)

    def test_pattern_precision_ok(self):
        """Pattern precision above target is OK."""
        mv = MetricValue(
            name=MetricName.PATTERN_PRECISION,
            value=0.90,
            target=0.85,
            threshold_warning=0.80,
            threshold_critical=0.75,
        )
        self.assertEqual(mv.evaluate_status(), MetricStatus.OK)


class TestMetricValueStatusLowerBetter(unittest.TestCase):
    """Test status evaluation for lower-is-better metrics."""

    def test_fp_rate_ok(self):
        """FP rate below target is OK."""
        mv = MetricValue(
            name=MetricName.FALSE_POSITIVE_RATE,
            value=0.10,
            target=0.15,
            threshold_warning=0.20,
            threshold_critical=0.25,
        )
        self.assertEqual(mv.evaluate_status(), MetricStatus.OK)

    def test_fp_rate_warning(self):
        """FP rate above target but below warning is WARNING."""
        mv = MetricValue(
            name=MetricName.FALSE_POSITIVE_RATE,
            value=0.18,
            target=0.15,
            threshold_warning=0.20,
            threshold_critical=0.25,
        )
        self.assertEqual(mv.evaluate_status(), MetricStatus.WARNING)

    def test_fp_rate_critical(self):
        """FP rate above warning threshold is CRITICAL."""
        mv = MetricValue(
            name=MetricName.FALSE_POSITIVE_RATE,
            value=0.22,
            target=0.15,
            threshold_warning=0.20,
            threshold_critical=0.25,
        )
        self.assertEqual(mv.evaluate_status(), MetricStatus.CRITICAL)

    def test_time_to_detection_ok(self):
        """Time below target is OK."""
        mv = MetricValue(
            name=MetricName.TIME_TO_DETECTION,
            value=25.0,
            target=30.0,
            threshold_warning=45.0,
            threshold_critical=60.0,
            unit="seconds",
        )
        self.assertEqual(mv.evaluate_status(), MetricStatus.OK)

    def test_escalation_rate_lower_is_better(self):
        """Escalation rate is a lower-is-better metric."""
        self.assertIn(MetricName.ESCALATION_RATE, LOWER_IS_BETTER_METRICS)

    def test_token_efficiency_lower_is_better(self):
        """Token efficiency is a lower-is-better metric."""
        self.assertIn(MetricName.TOKEN_EFFICIENCY, LOWER_IS_BETTER_METRICS)


class TestMetricValueSerialization(unittest.TestCase):
    """Test MetricValue serialization."""

    def test_to_dict(self):
        """MetricValue serializes to dict."""
        mv = MetricValue(
            name=MetricName.DETECTION_RATE,
            value=0.85,
            target=0.80,
            threshold_warning=0.70,
            threshold_critical=0.60,
            status=MetricStatus.OK,
            unit="percentage",
        )
        data = mv.to_dict()
        self.assertEqual(data["name"], "detection_rate")
        self.assertEqual(data["value"], 0.85)
        self.assertEqual(data["target"], 0.80)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["unit"], "percentage")
        self.assertIn("timestamp", data)

    def test_from_dict(self):
        """MetricValue deserializes from dict."""
        data = {
            "name": "detection_rate",
            "value": 0.85,
            "target": 0.80,
            "threshold_warning": 0.70,
            "threshold_critical": 0.60,
            "status": "ok",
            "unit": "percentage",
            "timestamp": "2026-01-08T10:00:00",
        }
        mv = MetricValue.from_dict(data)
        self.assertEqual(mv.name, MetricName.DETECTION_RATE)
        self.assertEqual(mv.value, 0.85)
        self.assertEqual(mv.status, MetricStatus.OK)

    def test_round_trip(self):
        """MetricValue survives serialization round trip."""
        original = MetricValue(
            name=MetricName.FALSE_POSITIVE_RATE,
            value=0.12,
            target=0.15,
            threshold_warning=0.20,
            threshold_critical=0.25,
            status=MetricStatus.OK,
            unit="percentage",
        )
        data = original.to_dict()
        restored = MetricValue.from_dict(data)
        self.assertEqual(original.name, restored.name)
        self.assertEqual(original.value, restored.value)
        self.assertEqual(original.target, restored.target)
        self.assertEqual(original.status, restored.status)


class TestMetricSnapshot(unittest.TestCase):
    """Test MetricSnapshot dataclass."""

    def setUp(self):
        """Create test snapshot."""
        self.metrics = {
            MetricName.DETECTION_RATE: MetricValue(
                name=MetricName.DETECTION_RATE,
                value=0.85,
                target=0.80,
                threshold_warning=0.70,
                threshold_critical=0.60,
            ),
            MetricName.FALSE_POSITIVE_RATE: MetricValue(
                name=MetricName.FALSE_POSITIVE_RATE,
                value=0.10,
                target=0.15,
                threshold_warning=0.20,
                threshold_critical=0.25,
            ),
        }
        self.snapshot = MetricSnapshot(
            timestamp=datetime(2026, 1, 8, 10, 0, 0),
            version="4.0.0",
            run_id="test-run-001",
            metrics=self.metrics,
        )

    def test_to_dict(self):
        """MetricSnapshot serializes to dict."""
        data = self.snapshot.to_dict()
        self.assertEqual(data["version"], "4.0.0")
        self.assertEqual(data["run_id"], "test-run-001")
        self.assertIn("detection_rate", data["metrics"])
        self.assertIn("false_positive_rate", data["metrics"])

    def test_from_dict(self):
        """MetricSnapshot deserializes from dict."""
        data = {
            "timestamp": "2026-01-08T10:00:00",
            "version": "4.0.0",
            "run_id": "test-001",
            "metrics": {
                "detection_rate": {
                    "name": "detection_rate",
                    "value": 0.85,
                    "target": 0.80,
                    "threshold_warning": 0.70,
                    "threshold_critical": 0.60,
                    "status": "ok",
                    "unit": "percentage",
                    "timestamp": "2026-01-08T10:00:00",
                },
            },
        }
        snapshot = MetricSnapshot.from_dict(data)
        self.assertEqual(snapshot.version, "4.0.0")
        self.assertIn(MetricName.DETECTION_RATE, snapshot.metrics)

    def test_get_status_summary(self):
        """get_status_summary counts metrics by status."""
        summary = self.snapshot.get_status_summary()
        # Both metrics should be OK (detection 0.85 >= 0.80, FP 0.10 <= 0.15)
        self.assertEqual(summary[MetricStatus.OK], 2)
        self.assertEqual(summary[MetricStatus.WARNING], 0)
        self.assertEqual(summary[MetricStatus.CRITICAL], 0)

    def test_has_critical_false(self):
        """has_critical returns False when no critical metrics."""
        self.assertFalse(self.snapshot.has_critical())

    def test_has_critical_true(self):
        """has_critical returns True when critical metric exists."""
        self.snapshot.metrics[MetricName.DETECTION_RATE] = MetricValue(
            name=MetricName.DETECTION_RATE,
            value=0.50,  # Below critical threshold
            target=0.80,
            threshold_warning=0.70,
            threshold_critical=0.60,
        )
        self.assertTrue(self.snapshot.has_critical())

    def test_has_warning_false(self):
        """has_warning returns False when no warning metrics."""
        self.assertFalse(self.snapshot.has_warning())

    def test_has_warning_true(self):
        """has_warning returns True when warning metric exists."""
        self.snapshot.metrics[MetricName.DETECTION_RATE] = MetricValue(
            name=MetricName.DETECTION_RATE,
            value=0.75,  # Between target and warning threshold
            target=0.80,
            threshold_warning=0.70,
            threshold_critical=0.60,
        )
        self.assertTrue(self.snapshot.has_warning())

    def test_unknown_metric_skipped_on_deserialize(self):
        """Unknown metrics are skipped during deserialization."""
        data = {
            "timestamp": "2026-01-08T10:00:00",
            "version": "4.0.0",
            "metrics": {
                "detection_rate": {
                    "name": "detection_rate",
                    "value": 0.85,
                    "target": 0.80,
                    "threshold_warning": 0.70,
                    "threshold_critical": 0.60,
                    "timestamp": "2026-01-08T10:00:00",
                },
                "unknown_future_metric": {  # This should be skipped
                    "name": "unknown_future_metric",
                    "value": 0.50,
                    "target": 0.50,
                    "threshold_warning": 0.40,
                    "threshold_critical": 0.30,
                    "timestamp": "2026-01-08T10:00:00",
                },
            },
        }
        snapshot = MetricSnapshot.from_dict(data)
        self.assertEqual(len(snapshot.metrics), 1)
        self.assertIn(MetricName.DETECTION_RATE, snapshot.metrics)


class TestMetricsConfig(unittest.TestCase):
    """Test metrics configuration."""

    def test_config_exists(self):
        """METRICS_CONFIG is defined in config module."""
        from alphaswarm_sol.config import METRICS_CONFIG

        self.assertIn("storage_path", METRICS_CONFIG)
        self.assertIn("history_retention_days", METRICS_CONFIG)
        self.assertIn("collection_interval", METRICS_CONFIG)

    def test_config_values(self):
        """METRICS_CONFIG has expected values."""
        from alphaswarm_sol.config import METRICS_CONFIG

        self.assertEqual(METRICS_CONFIG["storage_path"], ".vrs/metrics")
        self.assertEqual(METRICS_CONFIG["history_retention_days"], 90)


class TestMetricsImport(unittest.TestCase):
    """Test that the metrics module can be imported."""

    def test_import_from_package(self):
        """Can import from alphaswarm_sol.metrics."""
        from alphaswarm_sol.metrics import MetricName, MetricStatus, MetricValue, MetricSnapshot

        self.assertIsNotNone(MetricName)
        self.assertIsNotNone(MetricStatus)
        self.assertIsNotNone(MetricValue)
        self.assertIsNotNone(MetricSnapshot)

    def test_lower_is_better_metrics_exported(self):
        """LOWER_IS_BETTER_METRICS is exported."""
        from alphaswarm_sol.metrics import LOWER_IS_BETTER_METRICS

        self.assertIsInstance(LOWER_IS_BETTER_METRICS, frozenset)
        self.assertEqual(len(LOWER_IS_BETTER_METRICS), 4)


class TestMetricDefinitions(unittest.TestCase):
    """Test metric definitions (Task 8.1)."""

    def test_all_8_metrics_defined(self):
        """All 8 metrics have definitions."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        self.assertEqual(len(METRIC_DEFINITIONS), 8)
        for name in MetricName:
            self.assertIn(name, METRIC_DEFINITIONS)

    def test_detection_rate_thresholds(self):
        """Detection rate has correct thresholds."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        defn = METRIC_DEFINITIONS[MetricName.DETECTION_RATE]
        self.assertEqual(defn.target, 0.80)
        self.assertEqual(defn.threshold_warning, 0.75)
        self.assertEqual(defn.threshold_critical, 0.70)
        self.assertTrue(defn.higher_is_better)

    def test_fp_rate_lower_is_better(self):
        """FP rate is a lower-is-better metric."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        defn = METRIC_DEFINITIONS[MetricName.FALSE_POSITIVE_RATE]
        self.assertFalse(defn.higher_is_better)
        self.assertEqual(defn.target, 0.15)

    def test_all_definitions_have_data_sources(self):
        """All metrics have documented data sources."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        for name, defn in METRIC_DEFINITIONS.items():
            self.assertGreater(
                len(defn.data_sources),
                0,
                f"{name.value} missing data sources",
            )

    def test_scaffold_compile_rate_depends_on_beads(self):
        """Scaffold compile rate depends on Beads phase."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        defn = METRIC_DEFINITIONS[MetricName.SCAFFOLD_COMPILE_RATE]
        self.assertIn("Phase 6 (Beads)", defn.dependencies)

    def test_llm_autonomy_depends_on_beads_and_llm(self):
        """LLM autonomy depends on both Beads and LLM phases."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        defn = METRIC_DEFINITIONS[MetricName.LLM_AUTONOMY]
        self.assertIn("Phase 6 (Beads)", defn.dependencies)
        self.assertIn("Phase 11 (LLM)", defn.dependencies)

    def test_token_efficiency_depends_on_llm(self):
        """Token efficiency depends on LLM phase."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        defn = METRIC_DEFINITIONS[MetricName.TOKEN_EFFICIENCY]
        self.assertIn("Phase 11 (LLM)", defn.dependencies)

    def test_get_definition(self):
        """get_definition returns correct definition."""
        from alphaswarm_sol.metrics.definitions import get_definition

        defn = get_definition(MetricName.DETECTION_RATE)
        self.assertEqual(defn.name, MetricName.DETECTION_RATE)
        self.assertEqual(defn.target, 0.80)

    def test_get_all_definitions(self):
        """get_all_definitions returns all 8 definitions."""
        from alphaswarm_sol.metrics.definitions import get_all_definitions

        definitions = get_all_definitions()
        self.assertEqual(len(definitions), 8)

    def test_create_value_from_definition(self):
        """MetricDefinition.create_value creates correct MetricValue."""
        from alphaswarm_sol.metrics.definitions import get_definition

        defn = get_definition(MetricName.DETECTION_RATE)
        value = defn.create_value(0.85)

        self.assertEqual(value.name, MetricName.DETECTION_RATE)
        self.assertEqual(value.value, 0.85)
        self.assertEqual(value.target, 0.80)
        self.assertEqual(value.evaluate_status(), MetricStatus.OK)


class TestAvailableMetrics(unittest.TestCase):
    """Test available metrics functionality."""

    def test_available_metrics_without_dependencies(self):
        """Available metrics with no completed phases returns core only."""
        from alphaswarm_sol.metrics.definitions import get_available_metrics

        available = get_available_metrics()
        # Should include 4 core metrics
        self.assertIn(MetricName.DETECTION_RATE, available)
        self.assertIn(MetricName.FALSE_POSITIVE_RATE, available)
        self.assertIn(MetricName.PATTERN_PRECISION, available)
        self.assertIn(MetricName.TIME_TO_DETECTION, available)
        # Should NOT include Bead-dependent metrics
        self.assertNotIn(MetricName.SCAFFOLD_COMPILE_RATE, available)
        self.assertNotIn(MetricName.ESCALATION_RATE, available)
        # Should NOT include LLM-dependent metrics
        self.assertNotIn(MetricName.LLM_AUTONOMY, available)
        self.assertNotIn(MetricName.TOKEN_EFFICIENCY, available)

    def test_available_metrics_with_beads(self):
        """Available metrics with Beads phase includes Bead-dependent."""
        from alphaswarm_sol.metrics.definitions import get_available_metrics

        completed = {"Phase 6 (Beads)"}
        available = get_available_metrics(completed)
        # Should include Bead-dependent
        self.assertIn(MetricName.SCAFFOLD_COMPILE_RATE, available)
        self.assertIn(MetricName.ESCALATION_RATE, available)
        # Still not LLM-only metrics
        self.assertNotIn(MetricName.TOKEN_EFFICIENCY, available)

    def test_available_metrics_with_all_phases(self):
        """Available metrics with all phases returns all 8."""
        from alphaswarm_sol.metrics.definitions import get_available_metrics

        completed = {"Phase 6 (Beads)", "Phase 11 (LLM)"}
        available = get_available_metrics(completed)
        self.assertEqual(len(available), 8)

    def test_get_core_metrics(self):
        """get_core_metrics returns 4 core metrics."""
        from alphaswarm_sol.metrics.definitions import get_core_metrics

        core = get_core_metrics()
        self.assertEqual(len(core), 4)
        self.assertIn(MetricName.DETECTION_RATE, core)
        self.assertIn(MetricName.FALSE_POSITIVE_RATE, core)
        self.assertIn(MetricName.PATTERN_PRECISION, core)
        self.assertIn(MetricName.TIME_TO_DETECTION, core)

    def test_get_bead_dependent_metrics(self):
        """get_bead_dependent_metrics returns Bead-dependent metrics."""
        from alphaswarm_sol.metrics.definitions import get_bead_dependent_metrics

        bead = get_bead_dependent_metrics()
        self.assertEqual(len(bead), 2)
        self.assertIn(MetricName.SCAFFOLD_COMPILE_RATE, bead)
        self.assertIn(MetricName.ESCALATION_RATE, bead)

    def test_get_llm_dependent_metrics(self):
        """get_llm_dependent_metrics returns LLM-dependent metrics."""
        from alphaswarm_sol.metrics.definitions import get_llm_dependent_metrics

        llm = get_llm_dependent_metrics()
        self.assertEqual(len(llm), 2)
        self.assertIn(MetricName.LLM_AUTONOMY, llm)
        self.assertIn(MetricName.TOKEN_EFFICIENCY, llm)


class TestMetricDefinitionFields(unittest.TestCase):
    """Test that all metric definitions have required fields."""

    def test_all_have_formulas(self):
        """All metrics have formula defined."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        for name, defn in METRIC_DEFINITIONS.items():
            self.assertIsNotNone(defn.formula, f"{name.value} missing formula")
            self.assertGreater(len(defn.formula), 0)

    def test_all_have_descriptions(self):
        """All metrics have description defined."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        for name, defn in METRIC_DEFINITIONS.items():
            self.assertIsNotNone(defn.description, f"{name.value} missing description")
            self.assertGreater(len(defn.description), 0)

    def test_all_have_units(self):
        """All metrics have unit defined."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        for name, defn in METRIC_DEFINITIONS.items():
            self.assertIsNotNone(defn.unit, f"{name.value} missing unit")
            self.assertGreater(len(defn.unit), 0)

    def test_thresholds_ordered_correctly_higher_better(self):
        """For higher-is-better metrics: target > warning > critical."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        for name, defn in METRIC_DEFINITIONS.items():
            if defn.higher_is_better:
                self.assertGreater(
                    defn.target,
                    defn.threshold_warning,
                    f"{name.value} target should be > warning",
                )
                self.assertGreater(
                    defn.threshold_warning,
                    defn.threshold_critical,
                    f"{name.value} warning should be > critical",
                )

    def test_thresholds_ordered_correctly_lower_better(self):
        """For lower-is-better metrics: target < warning < critical."""
        from alphaswarm_sol.metrics.definitions import METRIC_DEFINITIONS

        for name, defn in METRIC_DEFINITIONS.items():
            if not defn.higher_is_better:
                self.assertLess(
                    defn.target,
                    defn.threshold_warning,
                    f"{name.value} target should be < warning",
                )
                self.assertLess(
                    defn.threshold_warning,
                    defn.threshold_critical,
                    f"{name.value} warning should be < critical",
                )


# =============================================================================
# Task 8.2a: Recording Infrastructure Tests
# =============================================================================


class TestEventTypes(unittest.TestCase):
    """Test event type definitions."""

    def test_event_type_enum(self):
        """EventType enum has all expected values."""
        self.assertEqual(len(EventType), 4)
        self.assertIn(EventType.DETECTION, EventType)
        self.assertIn(EventType.TIMING, EventType)
        self.assertIn(EventType.SCAFFOLD, EventType)
        self.assertIn(EventType.VERDICT, EventType)

    def test_detection_event_to_dict(self):
        """DetectionEvent serializes correctly."""
        event = DetectionEvent(
            event_id="evt-12345678",
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="withdraw",
            line_number=42,
            expected=True,
            detected=True,
        )
        data = event.to_dict()
        self.assertEqual(data["event_id"], "evt-12345678")
        self.assertEqual(data["event_type"], "detection")
        self.assertEqual(data["contract_id"], "test.sol")
        self.assertEqual(data["pattern_id"], "vm-001")
        self.assertEqual(data["expected"], True)
        self.assertEqual(data["detected"], True)

    def test_detection_event_from_dict(self):
        """DetectionEvent deserializes correctly."""
        data = {
            "event_id": "evt-12345678",
            "event_type": "detection",
            "timestamp": "2026-01-08T10:00:00",
            "contract_id": "test.sol",
            "pattern_id": "vm-001",
            "function_name": "withdraw",
            "line_number": 42,
            "expected": True,
            "detected": True,
        }
        event = DetectionEvent.from_dict(data)
        self.assertEqual(event.event_id, "evt-12345678")
        self.assertEqual(event.contract_id, "test.sol")
        self.assertTrue(event.detected)

    def test_timing_event_to_dict(self):
        """TimingEvent serializes correctly."""
        event = TimingEvent(
            event_id="evt-12345678",
            operation="scan",
            contract_id="test.sol",
            duration_seconds=2.5,
        )
        data = event.to_dict()
        self.assertEqual(data["event_type"], "timing")
        self.assertEqual(data["operation"], "scan")
        self.assertEqual(data["duration_seconds"], 2.5)

    def test_scaffold_event_to_dict(self):
        """ScaffoldEvent serializes correctly."""
        event = ScaffoldEvent(
            event_id="evt-12345678",
            finding_id="VKG-001",
            pattern_id="vm-001",
            compiled=False,
            error_message="Compilation failed",
        )
        data = event.to_dict()
        self.assertEqual(data["event_type"], "scaffold")
        self.assertEqual(data["compiled"], False)
        self.assertEqual(data["error_message"], "Compilation failed")

    def test_verdict_event_to_dict(self):
        """VerdictEvent serializes correctly."""
        event = VerdictEvent(
            event_id="evt-12345678",
            finding_id="VKG-001",
            pattern_id="vm-001",
            verdict="confirmed",
            auto_resolved=True,
            tokens_used=5000,
        )
        data = event.to_dict()
        self.assertEqual(data["event_type"], "verdict")
        self.assertEqual(data["verdict"], "confirmed")
        self.assertEqual(data["tokens_used"], 5000)


class TestEventFromDict(unittest.TestCase):
    """Test event_from_dict factory function."""

    def test_detection_event(self):
        """event_from_dict creates DetectionEvent."""
        data = {
            "event_id": "evt-12345678",
            "event_type": "detection",
            "timestamp": "2026-01-08T10:00:00",
            "contract_id": "test.sol",
            "pattern_id": "vm-001",
            "function_name": "withdraw",
            "line_number": 42,
            "expected": True,
            "detected": True,
        }
        event = event_from_dict(data)
        self.assertIsInstance(event, DetectionEvent)

    def test_timing_event(self):
        """event_from_dict creates TimingEvent."""
        data = {
            "event_id": "evt-12345678",
            "event_type": "timing",
            "timestamp": "2026-01-08T10:00:00",
            "operation": "scan",
            "contract_id": "test.sol",
            "duration_seconds": 2.5,
        }
        event = event_from_dict(data)
        self.assertIsInstance(event, TimingEvent)

    def test_unknown_event_type(self):
        """event_from_dict raises for unknown type."""
        data = {
            "event_id": "evt-12345678",
            "event_type": "unknown",
        }
        with self.assertRaises(ValueError):
            event_from_dict(data)


class TestEventStore(unittest.TestCase):
    """Test EventStore class."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = EventStore(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_detection_event(self):
        """Can record detection events."""
        event_id = self.store.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="withdraw",
            line_number=42,
            expected=True,
            detected=True,
        )

        self.assertTrue(event_id.startswith("evt-"))

        events = self.store.get_events(EventType.DETECTION)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["contract_id"], "test.sol")
        self.assertEqual(events[0]["detected"], True)

    def test_record_timing_event(self):
        """Can record timing events."""
        event_id = self.store.record_timing(
            operation="scan",
            contract_id="test.sol",
            duration_seconds=2.5,
        )

        self.assertTrue(event_id.startswith("evt-"))

        events = self.store.get_events(EventType.TIMING)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["duration_seconds"], 2.5)

    def test_record_scaffold_event(self):
        """Can record scaffold events."""
        event_id = self.store.record_scaffold(
            finding_id="VKG-001",
            pattern_id="vm-001",
            compiled=True,
        )

        self.assertTrue(event_id.startswith("evt-"))

        events = self.store.get_events(EventType.SCAFFOLD)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["compiled"], True)

    def test_record_verdict_event(self):
        """Can record verdict events."""
        event_id = self.store.record_verdict(
            finding_id="VKG-001",
            pattern_id="vm-001",
            verdict="confirmed",
            auto_resolved=True,
            tokens_used=5000,
        )

        self.assertTrue(event_id.startswith("evt-"))

        events = self.store.get_events(EventType.VERDICT)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["verdict"], "confirmed")

    def test_events_persisted_to_file(self):
        """Events written to daily JSON file."""
        self.store.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="withdraw",
            line_number=42,
            expected=True,
            detected=True,
        )

        # Check file exists
        files = list(Path(self.temp_dir).glob("events-*.json"))
        self.assertEqual(len(files), 1)

    def test_get_events_filters_by_type(self):
        """get_events filters by event type."""
        self.store.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="withdraw",
            line_number=42,
            expected=True,
            detected=True,
        )
        self.store.record_timing(
            operation="scan",
            contract_id="test.sol",
            duration_seconds=2.5,
        )

        detection_events = self.store.get_events(EventType.DETECTION)
        timing_events = self.store.get_events(EventType.TIMING)
        all_events = self.store.get_events()

        self.assertEqual(len(detection_events), 1)
        self.assertEqual(len(timing_events), 1)
        self.assertEqual(len(all_events), 2)

    def test_get_events_typed(self):
        """get_events_typed returns typed objects."""
        self.store.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="withdraw",
            line_number=42,
            expected=True,
            detected=True,
        )

        events = self.store.get_events_typed(EventType.DETECTION)
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], DetectionEvent)

    def test_count_events(self):
        """count_events returns correct count."""
        for i in range(5):
            self.store.record_detection(
                contract_id=f"test{i}.sol",
                pattern_id="vm-001",
                function_name="withdraw",
                line_number=42,
                expected=True,
                detected=True,
            )

        count = self.store.count_events(EventType.DETECTION)
        self.assertEqual(count, 5)

    def test_clear(self):
        """clear removes all events."""
        self.store.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="withdraw",
            line_number=42,
            expected=True,
            detected=True,
        )

        self.assertEqual(len(self.store.get_events()), 1)

        self.store.clear()

        self.assertEqual(len(self.store.get_events()), 0)

    def test_unique_event_ids(self):
        """Each event gets a unique ID."""
        ids = set()
        for i in range(10):
            event_id = self.store.record_detection(
                contract_id=f"test{i}.sol",
                pattern_id="vm-001",
                function_name="withdraw",
                line_number=42,
                expected=True,
                detected=True,
            )
            ids.add(event_id)

        self.assertEqual(len(ids), 10)


class TestMetricsRecorder(unittest.TestCase):
    """Test MetricsRecorder class."""

    def setUp(self):
        """Create temp directory and reset singleton."""
        self.temp_dir = tempfile.mkdtemp()
        MetricsRecorder.reset_instance()

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        MetricsRecorder.reset_instance()

    def test_singleton_pattern(self):
        """MetricsRecorder follows singleton pattern."""
        r1 = MetricsRecorder.get_instance(self.temp_dir)
        r2 = MetricsRecorder.get_instance()
        self.assertIs(r1, r2)

    def test_detection_method(self):
        """Recorder detection method works."""
        recorder = MetricsRecorder.get_instance(self.temp_dir)
        event_id = recorder.detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="withdraw",
            line_number=42,
            expected=True,
            detected=True,
        )
        self.assertTrue(event_id.startswith("evt-"))

    def test_timing_method(self):
        """Recorder timing method works."""
        recorder = MetricsRecorder.get_instance(self.temp_dir)
        event_id = recorder.timing(
            operation="scan",
            contract_id="test.sol",
            duration_seconds=2.5,
        )
        self.assertTrue(event_id.startswith("evt-"))

    def test_scaffold_method(self):
        """Recorder scaffold method works."""
        recorder = MetricsRecorder.get_instance(self.temp_dir)
        event_id = recorder.scaffold(
            finding_id="VKG-001",
            pattern_id="vm-001",
            compiled=True,
        )
        self.assertTrue(event_id.startswith("evt-"))

    def test_verdict_method(self):
        """Recorder verdict method works."""
        recorder = MetricsRecorder.get_instance(self.temp_dir)
        event_id = recorder.verdict(
            finding_id="VKG-001",
            pattern_id="vm-001",
            verdict="confirmed",
            auto_resolved=True,
            tokens_used=5000,
        )
        self.assertTrue(event_id.startswith("evt-"))

    def test_get_recorder_function(self):
        """get_recorder returns singleton."""
        r1 = get_recorder(self.temp_dir)
        r2 = get_recorder()
        self.assertIs(r1, r2)


# =============================================================================
# Task 8.2b: Metric Calculation Tests
# =============================================================================


class TestMetricCalculator(unittest.TestCase):
    """Test MetricCalculator class."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = EventStore(self.temp_dir)
        self.calc = MetricCalculator(self.store)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detection_rate_calculation(self):
        """Detection rate calculated correctly."""
        # Record 10 expected vulnerabilities, 8 detected
        for i in range(10):
            self.store.record_detection(
                contract_id="test.sol",
                pattern_id="vm-001",
                function_name=f"func{i}",
                line_number=i,
                expected=True,
                detected=i < 8,  # First 8 detected
            )

        snapshot = self.calc.calculate_all()

        self.assertIn(MetricName.DETECTION_RATE, snapshot.metrics)
        rate = snapshot.metrics[MetricName.DETECTION_RATE]
        self.assertEqual(rate.value, 0.8)  # 8/10
        self.assertEqual(rate.status, MetricStatus.OK)  # >= 80% target

    def test_detection_rate_warning(self):
        """Detection rate below target but above warning shows warning."""
        # Record 10 expected vulnerabilities, 7.6 ~= 8 detected for ~76%
        # Actually we need exactly 76% or higher to be WARNING
        # Let's use 100 expected, 76 detected for 76% (above warning threshold 75%)
        for i in range(100):
            self.store.record_detection(
                contract_id="test.sol",
                pattern_id="vm-001",
                function_name=f"func{i}",
                line_number=i,
                expected=True,
                detected=i < 76,  # 76 detected = 76%
            )

        snapshot = self.calc.calculate_all()
        rate = snapshot.metrics[MetricName.DETECTION_RATE]
        self.assertEqual(rate.value, 0.76)
        # 76% is above warning threshold (75%) but below target (80%)
        self.assertEqual(rate.status, MetricStatus.WARNING)

    def test_detection_rate_critical(self):
        """Detection rate below warning threshold shows critical."""
        # Record 10 expected vulnerabilities, 7 detected = 70%
        for i in range(10):
            self.store.record_detection(
                contract_id="test.sol",
                pattern_id="vm-001",
                function_name=f"func{i}",
                line_number=i,
                expected=True,
                detected=i < 7,  # Only 7 detected = 70%
            )

        snapshot = self.calc.calculate_all()
        rate = snapshot.metrics[MetricName.DETECTION_RATE]
        self.assertEqual(rate.value, 0.7)
        # 70% is below warning threshold (75%), so it's CRITICAL
        self.assertEqual(rate.status, MetricStatus.CRITICAL)

    def test_fp_rate_calculation(self):
        """False positive rate calculated correctly."""
        # 8 TP (expected and detected)
        for i in range(8):
            self.store.record_detection(
                contract_id="test.sol",
                pattern_id="vm-001",
                function_name=f"tp{i}",
                line_number=i,
                expected=True,
                detected=True,
            )

        # 2 FP (not expected but detected)
        for i in range(2):
            self.store.record_detection(
                contract_id="test.sol",
                pattern_id="vm-001",
                function_name=f"fp{i}",
                line_number=100 + i,
                expected=False,
                detected=True,
            )

        snapshot = self.calc.calculate_all()
        fp_rate = snapshot.metrics[MetricName.FALSE_POSITIVE_RATE]
        self.assertAlmostEqual(fp_rate.value, 0.2, places=3)  # 2/(2+8)

    def test_pattern_precision_per_pattern(self):
        """Pattern precision calculated per pattern then averaged."""
        # Pattern A: 4 TP, 0 FP = 100% precision
        for i in range(4):
            self.store.record_detection(
                contract_id="test.sol",
                pattern_id="pattern-a",
                function_name=f"a{i}",
                line_number=i,
                expected=True,
                detected=True,
            )

        # Pattern B: 3 TP, 3 FP = 50% precision
        for i in range(3):
            self.store.record_detection(
                contract_id="test.sol",
                pattern_id="pattern-b",
                function_name=f"b-tp{i}",
                line_number=100 + i,
                expected=True,
                detected=True,
            )
        for i in range(3):
            self.store.record_detection(
                contract_id="test.sol",
                pattern_id="pattern-b",
                function_name=f"b-fp{i}",
                line_number=200 + i,
                expected=False,
                detected=True,
            )

        snapshot = self.calc.calculate_all()
        precision = snapshot.metrics[MetricName.PATTERN_PRECISION]
        # Average of 100% and 50% = 75%
        self.assertAlmostEqual(precision.value, 0.75, places=3)

    def test_time_to_detection_calculation(self):
        """Time to detection calculated from timing events."""
        # Record several scan timings
        self.store.record_timing("scan", "test1.sol", 2.0)
        self.store.record_timing("scan", "test2.sol", 4.0)
        self.store.record_timing("scan", "test3.sol", 6.0)

        snapshot = self.calc.calculate_all()
        time_metric = snapshot.metrics[MetricName.TIME_TO_DETECTION]
        # Average: (2 + 4 + 6) / 3 = 4
        self.assertAlmostEqual(time_metric.value, 4.0, places=3)

    def test_time_to_detection_filters_to_scan(self):
        """Time to detection only counts scan operations."""
        self.store.record_timing("scan", "test.sol", 5.0)
        self.store.record_timing("build_graph", "test.sol", 10.0)  # Should be ignored

        snapshot = self.calc.calculate_all()
        time_metric = snapshot.metrics[MetricName.TIME_TO_DETECTION]
        self.assertEqual(time_metric.value, 5.0)

    def test_unknown_when_no_data(self):
        """Returns UNKNOWN status when no events recorded."""
        snapshot = self.calc.calculate_all()

        for metric in snapshot.metrics.values():
            self.assertEqual(metric.status, MetricStatus.UNKNOWN)

    def test_calculate_single_metric(self):
        """Can calculate a single metric."""
        self.store.record_timing("scan", "test.sol", 5.0)

        time_metric = self.calc.calculate_single(MetricName.TIME_TO_DETECTION)

        self.assertIsNotNone(time_metric)
        self.assertEqual(time_metric.value, 5.0)

    def test_snapshot_has_version(self):
        """MetricSnapshot includes VKG version."""
        snapshot = self.calc.calculate_all()
        self.assertIsNotNone(snapshot.version)

    def test_snapshot_has_timestamp(self):
        """MetricSnapshot includes timestamp."""
        snapshot = self.calc.calculate_all()
        self.assertIsNotNone(snapshot.timestamp)
        self.assertIsInstance(snapshot.timestamp, datetime)


class TestMetricsTracker(unittest.TestCase):
    """Test MetricsTracker unified interface."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = MetricsTracker(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_and_calculate(self):
        """Can record events and calculate metrics."""
        # Record detections
        for i in range(10):
            self.tracker.record_detection(
                contract_id="test.sol",
                pattern_id="vm-001",
                function_name=f"func{i}",
                line_number=i,
                expected=True,
                detected=i < 8,
            )

        # Calculate metrics
        snapshot = self.tracker.calculate_metrics()

        self.assertIn(MetricName.DETECTION_RATE, snapshot.metrics)
        self.assertEqual(snapshot.metrics[MetricName.DETECTION_RATE].value, 0.8)

    def test_get_event_count(self):
        """get_event_count returns correct count."""
        self.tracker.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="test",
            line_number=1,
            expected=True,
            detected=True,
        )
        self.tracker.record_timing("scan", "test.sol", 1.0)

        count = self.tracker.get_event_count()
        self.assertEqual(count, 2)

    def test_clear_events(self):
        """clear_events removes all events."""
        self.tracker.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="test",
            line_number=1,
            expected=True,
            detected=True,
        )

        self.assertEqual(self.tracker.get_event_count(), 1)

        self.tracker.clear_events()

        self.assertEqual(self.tracker.get_event_count(), 0)

    def test_record_all_event_types(self):
        """Tracker can record all event types."""
        self.tracker.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="test",
            line_number=1,
            expected=True,
            detected=True,
        )
        self.tracker.record_timing("scan", "test.sol", 1.0)
        self.tracker.record_scaffold("VKG-001", "vm-001", True)
        self.tracker.record_verdict("VKG-001", "vm-001", "confirmed", True, 5000)

        self.assertEqual(self.tracker.get_event_count(), 4)


# =============================================================================
# Task 8.3: Historical Storage Tests
# =============================================================================


class TestHistoryStore(unittest.TestCase):
    """Test historical storage."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load(self):
        """Snapshot can be saved and loaded."""
        from alphaswarm_sol.metrics.storage import HistoryStore

        store = HistoryStore(self.temp_dir)

        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={},
        )
        filepath = store.save(snapshot)

        loaded = store.load(filepath)
        self.assertEqual(loaded.version, "4.0.0")

    def test_get_latest(self):
        """get_latest returns most recent."""
        from alphaswarm_sol.metrics.storage import HistoryStore
        from datetime import timedelta

        store = HistoryStore(self.temp_dir)

        # Save oldest first
        for i in range(2, -1, -1):  # 2, 1, 0
            snapshot = MetricSnapshot(
                timestamp=datetime.now() - timedelta(hours=i),
                version=f"v{i}",
                metrics={},
            )
            store.save(snapshot)

        latest = store.get_latest()
        self.assertEqual(latest.version, "v0")  # Most recent

    def test_get_history_days(self):
        """get_history filters by days."""
        from alphaswarm_sol.metrics.storage import HistoryStore
        from datetime import timedelta

        store = HistoryStore(self.temp_dir)

        # Snapshot from 10 days ago
        old = MetricSnapshot(
            timestamp=datetime.now() - timedelta(days=10),
            version="old",
            metrics={},
        )
        store.save(old)

        # Snapshot from today
        new = MetricSnapshot(
            timestamp=datetime.now(),
            version="new",
            metrics={},
        )
        store.save(new)

        history = store.get_history(days=5)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].version, "new")

    def test_get_history_limit(self):
        """get_history respects limit."""
        from alphaswarm_sol.metrics.storage import HistoryStore
        from datetime import timedelta

        store = HistoryStore(self.temp_dir)

        base = datetime.now()
        for i in range(5):
            snapshot = MetricSnapshot(
                timestamp=base - timedelta(seconds=5 - i),  # Different timestamps
                version=f"v{i}",
                metrics={},
            )
            store.save(snapshot)

        history = store.get_history(days=30, limit=2)
        self.assertEqual(len(history), 2)

    def test_get_range(self):
        """get_range returns snapshots within date range."""
        from alphaswarm_sol.metrics.storage import HistoryStore
        from datetime import timedelta

        store = HistoryStore(self.temp_dir)

        # Create snapshots across time
        base = datetime.now()
        for i in range(5):
            snapshot = MetricSnapshot(
                timestamp=base - timedelta(days=i),
                version=f"v{i}",
                metrics={},
            )
            store.save(snapshot)

        # Get middle range
        start = base - timedelta(days=3)
        end = base - timedelta(days=1)
        range_snapshots = store.get_range(start, end)

        self.assertEqual(len(range_snapshots), 3)  # days 1, 2, 3

    def test_cleanup_retention(self):
        """cleanup removes old snapshots."""
        from alphaswarm_sol.metrics.storage import HistoryStore
        from datetime import timedelta

        store = HistoryStore(self.temp_dir)

        # Snapshot from 100 days ago
        old = MetricSnapshot(
            timestamp=datetime.now() - timedelta(days=100),
            version="old",
            metrics={},
        )
        store.save(old)

        # Snapshot from today
        new = MetricSnapshot(
            timestamp=datetime.now(),
            version="new",
            metrics={},
        )
        store.save(new)

        removed = store.cleanup(retention_days=90)
        self.assertEqual(removed, 1)
        self.assertEqual(store.count(), 1)

    def test_count(self):
        """count returns correct number of snapshots."""
        from alphaswarm_sol.metrics.storage import HistoryStore
        from datetime import timedelta

        store = HistoryStore(self.temp_dir)

        self.assertEqual(store.count(), 0)

        base = datetime.now()
        for i in range(3):
            snapshot = MetricSnapshot(
                timestamp=base - timedelta(seconds=3 - i),  # Different timestamps
                version=f"v{i}",
                metrics={},
            )
            store.save(snapshot)

        self.assertEqual(store.count(), 3)

    def test_get_metric_trend(self):
        """get_metric_trend returns time series for a metric."""
        from alphaswarm_sol.metrics.storage import HistoryStore
        from datetime import timedelta

        store = HistoryStore(self.temp_dir)

        # Create snapshots with different detection rates
        base = datetime.now()
        for i, rate in enumerate([0.80, 0.85, 0.90]):
            snapshot = MetricSnapshot(
                timestamp=base - timedelta(days=2 - i),
                version=f"v{i}",
                metrics={
                    MetricName.DETECTION_RATE: MetricValue(
                        name=MetricName.DETECTION_RATE,
                        value=rate,
                        target=0.80,
                        threshold_warning=0.75,
                        threshold_critical=0.70,
                    )
                },
            )
            store.save(snapshot)

        trend = store.get_metric_trend(MetricName.DETECTION_RATE, days=30)
        self.assertEqual(len(trend), 3)
        # Check values are in chronological order
        self.assertEqual(trend[0][1], 0.80)
        self.assertEqual(trend[1][1], 0.85)
        self.assertEqual(trend[2][1], 0.90)

    def test_get_statistics(self):
        """get_statistics calculates min/max/avg correctly."""
        from alphaswarm_sol.metrics.storage import HistoryStore
        from datetime import timedelta

        store = HistoryStore(self.temp_dir)

        # Create snapshots with known values
        base = datetime.now()
        for i, rate in enumerate([0.70, 0.80, 0.90]):
            snapshot = MetricSnapshot(
                timestamp=base - timedelta(days=2 - i),
                version=f"v{i}",
                metrics={
                    MetricName.DETECTION_RATE: MetricValue(
                        name=MetricName.DETECTION_RATE,
                        value=rate,
                        target=0.80,
                        threshold_warning=0.75,
                        threshold_critical=0.70,
                    )
                },
            )
            store.save(snapshot)

        stats = store.get_statistics(MetricName.DETECTION_RATE, days=30)
        self.assertIsNotNone(stats)
        self.assertEqual(stats["min"], 0.70)
        self.assertEqual(stats["max"], 0.90)
        self.assertAlmostEqual(stats["avg"], 0.80, places=2)
        self.assertEqual(stats["latest"], 0.90)
        self.assertEqual(stats["count"], 3)

    def test_empty_history(self):
        """get_latest returns None for empty history."""
        from alphaswarm_sol.metrics.storage import HistoryStore

        store = HistoryStore(self.temp_dir)
        self.assertIsNone(store.get_latest())

    def test_get_statistics_no_data(self):
        """get_statistics returns None when no data."""
        from alphaswarm_sol.metrics.storage import HistoryStore

        store = HistoryStore(self.temp_dir)
        stats = store.get_statistics(MetricName.DETECTION_RATE, days=30)
        self.assertIsNone(stats)


# =============================================================================
# Task 8.4: Alerting System Tests
# =============================================================================


class TestAlerting(unittest.TestCase):
    """Test alerting system."""

    def _make_metric(self, name, value, target, warning, critical):
        """Helper to create a MetricValue with evaluated status."""
        mv = MetricValue(
            name=name,
            value=value,
            target=target,
            threshold_warning=warning,
            threshold_critical=critical,
        )
        mv.status = mv.evaluate_status()
        return mv

    def test_warning_alert_generated(self):
        """Alert generated for WARNING status metric."""
        from alphaswarm_sol.metrics.alerting import AlertChecker, AlertLevel, AlertType

        checker = AlertChecker()

        # Detection rate at 76% (below target 80%, above warning 75%)
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: self._make_metric(
                    MetricName.DETECTION_RATE, 0.76, 0.80, 0.75, 0.70
                )
            },
        )

        alerts = checker.check_snapshot(snapshot)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].level, AlertLevel.WARNING)
        self.assertEqual(alerts[0].alert_type, AlertType.THRESHOLD_BREACH)

    def test_critical_alert_generated(self):
        """Alert generated for CRITICAL status metric."""
        from alphaswarm_sol.metrics.alerting import AlertChecker, AlertLevel

        checker = AlertChecker()

        # Detection rate at 65% (below critical threshold 70%)
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: self._make_metric(
                    MetricName.DETECTION_RATE, 0.65, 0.80, 0.75, 0.70
                )
            },
        )

        alerts = checker.check_snapshot(snapshot)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].level, AlertLevel.CRITICAL)

    def test_no_alert_for_ok_metric(self):
        """No alert generated for OK status metric."""
        from alphaswarm_sol.metrics.alerting import AlertChecker

        checker = AlertChecker()

        # Detection rate at 85% (above target 80%)
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: self._make_metric(
                    MetricName.DETECTION_RATE, 0.85, 0.80, 0.75, 0.70
                )
            },
        )

        alerts = checker.check_snapshot(snapshot)
        self.assertEqual(len(alerts), 0)

    def test_regression_alert(self):
        """Alert generated for regression from baseline."""
        from alphaswarm_sol.metrics.alerting import AlertChecker, AlertType

        checker = AlertChecker(regression_threshold=0.05)

        # Baseline: 90% detection rate
        baseline = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: self._make_metric(
                    MetricName.DETECTION_RATE, 0.90, 0.80, 0.75, 0.70
                )
            },
        )

        # Current: 80% detection rate (> 5% decrease)
        current = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: self._make_metric(
                    MetricName.DETECTION_RATE, 0.80, 0.80, 0.75, 0.70
                )
            },
        )

        alerts = checker.check_snapshot(current, baseline)

        # Should have regression alert
        regressions = [a for a in alerts if a.alert_type == AlertType.DEGRADATION]
        self.assertEqual(len(regressions), 1)
        self.assertIn("decreased", regressions[0].message)

    def test_no_regression_for_small_change(self):
        """No regression alert for changes below threshold."""
        from alphaswarm_sol.metrics.alerting import AlertChecker, AlertType

        checker = AlertChecker(regression_threshold=0.05)

        # Baseline: 85%
        baseline = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: self._make_metric(
                    MetricName.DETECTION_RATE, 0.85, 0.80, 0.75, 0.70
                )
            },
        )

        # Current: 83% (< 5% decrease from 85%)
        current = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: self._make_metric(
                    MetricName.DETECTION_RATE, 0.83, 0.80, 0.75, 0.70
                )
            },
        )

        alerts = checker.check_snapshot(current, baseline)

        # No regression alert (threshold not exceeded)
        regressions = [a for a in alerts if a.alert_type == AlertType.DEGRADATION]
        self.assertEqual(len(regressions), 0)

    def test_lower_is_better_warning(self):
        """Alert for lower-is-better metric exceeding target but below warning threshold."""
        from alphaswarm_sol.metrics.alerting import AlertChecker, AlertLevel

        checker = AlertChecker()

        # FP rate at 17% (above target 15%, but below warning threshold 18%)
        # For lower-is-better: value <= target=OK, value <= warning=WARNING, else=CRITICAL
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.FALSE_POSITIVE_RATE: self._make_metric(
                    MetricName.FALSE_POSITIVE_RATE, 0.17, 0.15, 0.18, 0.20
                )
            },
        )

        alerts = checker.check_snapshot(snapshot)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].level, AlertLevel.WARNING)

    def test_lower_is_better_critical(self):
        """Critical alert for lower-is-better metric exceeding critical threshold."""
        from alphaswarm_sol.metrics.alerting import AlertChecker, AlertLevel

        checker = AlertChecker()

        # FP rate at 22% (above critical threshold 20%)
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.FALSE_POSITIVE_RATE: self._make_metric(
                    MetricName.FALSE_POSITIVE_RATE, 0.22, 0.15, 0.18, 0.20
                )
            },
        )

        alerts = checker.check_snapshot(snapshot)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].level, AlertLevel.CRITICAL)

    def test_lower_is_better_regression(self):
        """Regression alert for lower-is-better metric increasing."""
        from alphaswarm_sol.metrics.alerting import AlertChecker, AlertType

        checker = AlertChecker(regression_threshold=0.05)

        # Baseline: 10% FP rate
        baseline = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.FALSE_POSITIVE_RATE: self._make_metric(
                    MetricName.FALSE_POSITIVE_RATE, 0.10, 0.15, 0.18, 0.20
                )
            },
        )

        # Current: 12% (> 5% increase = 10.5%)
        current = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.FALSE_POSITIVE_RATE: self._make_metric(
                    MetricName.FALSE_POSITIVE_RATE, 0.12, 0.15, 0.18, 0.20
                )
            },
        )

        alerts = checker.check_snapshot(current, baseline)

        regressions = [a for a in alerts if a.alert_type == AlertType.DEGRADATION]
        self.assertEqual(len(regressions), 1)
        self.assertIn("increased", regressions[0].message)

    def test_has_critical_helper(self):
        """has_critical returns True when critical alert exists."""
        from alphaswarm_sol.metrics.alerting import AlertChecker

        checker = AlertChecker()

        # Critical metric
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: self._make_metric(
                    MetricName.DETECTION_RATE, 0.65, 0.80, 0.75, 0.70
                )
            },
        )

        alerts = checker.check_snapshot(snapshot)
        self.assertTrue(checker.has_critical(alerts))

    def test_check_alerts_convenience_function(self):
        """check_alerts convenience function works."""
        from alphaswarm_sol.metrics.alerting import check_alerts

        # Warning metric
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: self._make_metric(
                    MetricName.DETECTION_RATE, 0.76, 0.80, 0.75, 0.70
                )
            },
        )

        alerts = check_alerts(snapshot)
        self.assertEqual(len(alerts), 1)

    def test_alert_to_dict(self):
        """Alert serializes to dict correctly."""
        from alphaswarm_sol.metrics.alerting import Alert, AlertLevel, AlertType

        alert = Alert(
            metric_name=MetricName.DETECTION_RATE,
            level=AlertLevel.WARNING,
            alert_type=AlertType.THRESHOLD_BREACH,
            message="Test message",
            current_value=0.76,
            threshold_value=0.75,
        )

        data = alert.to_dict()
        self.assertEqual(data["metric_name"], "detection_rate")
        self.assertEqual(data["level"], "warning")
        self.assertEqual(data["message"], "Test message")

    def test_alert_str(self):
        """Alert has readable string representation."""
        from alphaswarm_sol.metrics.alerting import Alert, AlertLevel, AlertType

        alert = Alert(
            metric_name=MetricName.DETECTION_RATE,
            level=AlertLevel.CRITICAL,
            alert_type=AlertType.THRESHOLD_BREACH,
            message="Detection rate is low",
            current_value=0.65,
            threshold_value=0.70,
        )

        self.assertIn("CRITICAL", str(alert))
        self.assertIn("Detection rate is low", str(alert))

    def test_skip_unknown_status(self):
        """No alert for UNKNOWN status metrics."""
        from alphaswarm_sol.metrics.alerting import AlertChecker

        checker = AlertChecker()

        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="4.0.0",
            metrics={
                MetricName.DETECTION_RATE: MetricValue(
                    name=MetricName.DETECTION_RATE,
                    value=0.0,
                    target=0.80,
                    threshold_warning=0.75,
                    threshold_critical=0.70,
                    status=MetricStatus.UNKNOWN,
                )
            },
        )

        alerts = checker.check_snapshot(snapshot)
        self.assertEqual(len(alerts), 0)


class TestTrackerHistory(unittest.TestCase):
    """Test MetricsTracker history integration."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = MetricsTracker(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_snapshot(self):
        """Tracker can save snapshots."""
        # Record some data
        self.tracker.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="test",
            line_number=1,
            expected=True,
            detected=True,
        )

        # Save snapshot
        filepath = self.tracker.save_snapshot()
        self.assertTrue(filepath.exists())

    def test_get_latest_snapshot(self):
        """Tracker can retrieve latest snapshot."""
        self.tracker.record_detection(
            contract_id="test.sol",
            pattern_id="vm-001",
            function_name="test",
            line_number=1,
            expected=True,
            detected=True,
        )

        # No history yet
        self.assertIsNone(self.tracker.get_latest_snapshot())

        # Save and retrieve
        self.tracker.save_snapshot()
        latest = self.tracker.get_latest_snapshot()
        self.assertIsNotNone(latest)
        self.assertIn(MetricName.DETECTION_RATE, latest.metrics)

    def test_tracker_history_integration(self):
        """Full workflow: record, calculate, save, retrieve."""
        # Record detections
        for i in range(10):
            self.tracker.record_detection(
                contract_id="test.sol",
                pattern_id="vm-001",
                function_name=f"func{i}",
                line_number=i,
                expected=True,
                detected=i < 8,
            )

        # Calculate and save
        snapshot = self.tracker.calculate_metrics()
        self.tracker.save_snapshot(snapshot)

        # Retrieve
        history = self.tracker.get_history(days=1)
        self.assertEqual(len(history), 1)
        self.assertEqual(
            history[0].metrics[MetricName.DETECTION_RATE].value,
            0.8,
        )


if __name__ == "__main__":
    unittest.main()
