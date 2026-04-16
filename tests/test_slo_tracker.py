"""Tests for SLO tracking and incident response.

Test Coverage:
- SLOTracker measurement and violation detection
- IncidentDetector creates incidents from violations
- PlaybookExecutor runs automated response steps
- Configuration loading (YAML)
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock

from alphaswarm_sol.reliability.slo import (
    SLO,
    SLOStatus,
    SLOMeasurement,
    SLOViolation,
    SLOTracker,
    load_slos,
)
from alphaswarm_sol.reliability.incidents import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    IncidentDetector,
)
from alphaswarm_sol.reliability.playbooks import (
    Playbook,
    PlaybookStep,
    PlaybookResult,
    PlaybookExecutor,
    StepAction,
    load_playbooks,
)


@pytest.fixture
def sample_slo():
    """Create sample SLO for testing."""
    return SLO(
        id="test_success_rate",
        name="Test Success Rate",
        description="Test SLO",
        target=95.0,
        alert_threshold=90.0,
        comparison="gte",
    )


@pytest.fixture
def mock_event_store():
    """Create mock event store."""
    store = Mock()
    store.list_events = Mock(return_value=[])
    return store


@pytest.fixture
def mock_cost_ledger():
    """Create mock cost ledger."""
    ledger = Mock()

    # Create a proper mock summary with required attributes
    summary = Mock()
    summary.pool_id = "test-pool"
    summary.total_cost_usd = 5.0
    summary.cost_by_bead = {"VKG-001": 2.5, "VKG-002": 2.5}

    ledger.summary = Mock(return_value=summary)
    return ledger


@pytest.fixture
def slo_tracker(sample_slo, mock_event_store, mock_cost_ledger):
    """Create SLOTracker with test fixtures."""
    slos = {"test_success_rate": sample_slo}
    return SLOTracker(
        slos=slos,
        event_store=mock_event_store,
        cost_ledger=mock_cost_ledger,
    )


class TestSLO:
    """Test SLO dataclass."""

    def test_slo_creation(self, sample_slo):
        """Test SLO can be created."""
        assert sample_slo.id == "test_success_rate"
        assert sample_slo.name == "Test Success Rate"
        assert sample_slo.target == 95.0
        assert sample_slo.alert_threshold == 90.0
        assert sample_slo.comparison == "gte"

    def test_slo_to_dict(self, sample_slo):
        """Test SLO serialization."""
        data = sample_slo.to_dict()
        assert data["id"] == "test_success_rate"
        assert data["target"] == 95.0
        assert "name" in data

    def test_slo_from_dict(self):
        """Test SLO deserialization."""
        data = {
            "id": "test_slo",
            "name": "Test SLO",
            "description": "Test description",
            "target": 90.0,
            "alert_threshold": 85.0,
            "comparison": "gte",
        }
        slo = SLO.from_dict(data)
        assert slo.id == "test_slo"
        assert slo.target == 90.0


class TestSLOMeasurement:
    """Test SLOMeasurement dataclass."""

    def test_measurement_creation(self):
        """Test measurement can be created."""
        measurement = SLOMeasurement(
            slo_id="test_slo",
            value=92.5,
            timestamp=datetime.now(),
            pool_id="pool-001",
            affected_pools=["pool-001", "pool-002"],
        )
        assert measurement.slo_id == "test_slo"
        assert measurement.value == 92.5
        assert measurement.pool_id == "pool-001"
        assert len(measurement.affected_pools) == 2

    def test_measurement_to_dict(self):
        """Test measurement serialization."""
        measurement = SLOMeasurement(
            slo_id="test_slo",
            value=92.5,
            timestamp=datetime.now(),
        )
        data = measurement.to_dict()
        assert data["slo_id"] == "test_slo"
        assert data["value"] == 92.5
        assert "timestamp" in data


class TestSLOTracker:
    """Test SLOTracker functionality."""

    def test_tracker_initialization(self, slo_tracker):
        """Test tracker initializes with SLOs."""
        assert "test_success_rate" in slo_tracker.slos
        assert slo_tracker.event_store is not None
        assert slo_tracker.cost_ledger is not None

    def test_tracker_uses_default_slos(self):
        """Test tracker uses default SLOs when none provided."""
        tracker = SLOTracker()
        assert "pool_success_rate" in tracker.slos
        assert "pool_completion_latency_p95" in tracker.slos
        assert "cost_per_finding" in tracker.slos
        assert len(tracker.slos) == 5

    def test_measure_slo_returns_measurement(self, slo_tracker):
        """Test measure_slo returns valid measurement."""
        # This will use the default measurement logic
        measurement = slo_tracker.measure_slo("test_success_rate")

        assert isinstance(measurement, SLOMeasurement)
        assert measurement.slo_id == "test_success_rate"
        assert isinstance(measurement.value, float)
        assert isinstance(measurement.timestamp, datetime)

    def test_measure_slo_unknown_raises_error(self, slo_tracker):
        """Test measuring unknown SLO raises KeyError."""
        with pytest.raises(KeyError, match="Unknown SLO"):
            slo_tracker.measure_slo("nonexistent_slo")

    def test_check_slo_healthy_returns_none(self, slo_tracker):
        """Test check_slo returns None for healthy SLO."""
        measurement = SLOMeasurement(
            slo_id="test_success_rate",
            value=96.0,  # Above target of 95.0
            timestamp=datetime.now(),
        )
        violation = slo_tracker.check_slo("test_success_rate", measurement)
        assert violation is None

    def test_check_slo_warning_returns_violation(self, slo_tracker):
        """Test check_slo returns WARNING violation."""
        measurement = SLOMeasurement(
            slo_id="test_success_rate",
            value=92.0,  # Below target but above alert threshold
            timestamp=datetime.now(),
        )
        violation = slo_tracker.check_slo("test_success_rate", measurement)

        assert violation is not None
        assert violation.status == SLOStatus.WARNING
        assert violation.measured_value == 92.0
        assert violation.slo_id == "test_success_rate"

    def test_check_slo_violated_returns_critical(self, slo_tracker):
        """Test check_slo returns VIOLATED for critical threshold."""
        measurement = SLOMeasurement(
            slo_id="test_success_rate",
            value=85.0,  # Below alert threshold of 90.0
            timestamp=datetime.now(),
        )
        violation = slo_tracker.check_slo("test_success_rate", measurement)

        assert violation is not None
        assert violation.status == SLOStatus.VIOLATED
        assert violation.measured_value == 85.0

    def test_check_slo_lower_is_better(self, slo_tracker):
        """Test check_slo handles 'lte' comparison."""
        # Add a lower-is-better SLO
        slo_tracker.slos["test_latency"] = SLO(
            id="test_latency",
            name="Test Latency",
            description="Test",
            target=100.0,
            alert_threshold=120.0,
            comparison="lte",
        )

        # Value below target - healthy
        measurement = SLOMeasurement(
            slo_id="test_latency",
            value=90.0,
            timestamp=datetime.now(),
        )
        violation = slo_tracker.check_slo("test_latency", measurement)
        assert violation is None

        # Value above threshold - violated
        measurement = SLOMeasurement(
            slo_id="test_latency",
            value=130.0,
            timestamp=datetime.now(),
        )
        violation = slo_tracker.check_slo("test_latency", measurement)
        assert violation is not None
        assert violation.status == SLOStatus.VIOLATED

    def test_get_measurements_filters_by_slo(self, slo_tracker):
        """Test get_measurements filters by SLO ID."""
        # Create some measurements
        m1 = slo_tracker.measure_slo("test_success_rate")

        measurements = slo_tracker.get_measurements(slo_id="test_success_rate")
        assert len(measurements) >= 1
        assert all(m.slo_id == "test_success_rate" for m in measurements)

    def test_get_violations_filters_by_slo(self, slo_tracker):
        """Test get_violations filters by SLO ID."""
        # Create a violation
        measurement = SLOMeasurement(
            slo_id="test_success_rate",
            value=85.0,
            timestamp=datetime.now(),
        )
        violation = slo_tracker.check_slo("test_success_rate", measurement)

        violations = slo_tracker.get_violations(slo_id="test_success_rate")
        assert len(violations) >= 1
        assert all(v.slo_id == "test_success_rate" for v in violations)

    def test_measure_cost_per_finding(self, mock_cost_ledger):
        """Test cost_per_finding measurement with mock ledger."""
        tracker = SLOTracker(cost_ledger=mock_cost_ledger)
        measurement = tracker.measure_slo("cost_per_finding")

        assert isinstance(measurement, SLOMeasurement)
        assert measurement.value > 0  # Should calculate cost per finding


class TestIncidentDetector:
    """Test IncidentDetector functionality."""

    def test_detector_initialization(self):
        """Test detector can be initialized."""
        detector = IncidentDetector()
        assert detector is not None

    def test_detect_from_slo_violations_creates_incidents(self):
        """Test detector creates incidents from violations."""
        detector = IncidentDetector()

        violation = SLOViolation(
            slo_id="test_slo",
            status=SLOStatus.VIOLATED,
            measured_value=85.0,
            target=95.0,
            alert_threshold=90.0,
            timestamp=datetime.now(),
            affected_pools=["pool-001"],
            message="Test violation",
        )

        incidents = detector.detect_from_slo_violations([violation])

        assert len(incidents) == 1
        incident = incidents[0]
        assert incident.slo_id == "test_slo"
        assert incident.severity == IncidentSeverity.HIGH
        assert incident.status == IncidentStatus.OPEN
        assert "pool-001" in incident.affected_pools

    def test_detect_maps_warning_to_medium(self):
        """Test WARNING status maps to MEDIUM severity."""
        detector = IncidentDetector()

        violation = SLOViolation(
            slo_id="test_slo",
            status=SLOStatus.WARNING,
            measured_value=92.0,
            target=95.0,
            alert_threshold=90.0,
            timestamp=datetime.now(),
        )

        incidents = detector.detect_from_slo_violations([violation])

        assert len(incidents) == 1
        assert incidents[0].severity == IncidentSeverity.MEDIUM

    def test_get_incident_by_id(self):
        """Test getting incident by ID."""
        detector = IncidentDetector()

        violation = SLOViolation(
            slo_id="test_slo",
            status=SLOStatus.VIOLATED,
            measured_value=85.0,
            target=95.0,
            alert_threshold=90.0,
            timestamp=datetime.now(),
        )

        incidents = detector.detect_from_slo_violations([violation])
        incident_id = incidents[0].id

        retrieved = detector.get_incident(incident_id)
        assert retrieved is not None
        assert retrieved.id == incident_id

    def test_list_incidents_filters_by_status(self):
        """Test listing incidents with status filter."""
        detector = IncidentDetector()

        violation = SLOViolation(
            slo_id="test_slo",
            status=SLOStatus.VIOLATED,
            measured_value=85.0,
            target=95.0,
            alert_threshold=90.0,
            timestamp=datetime.now(),
        )

        detector.detect_from_slo_violations([violation])

        open_incidents = detector.list_incidents(status=IncidentStatus.OPEN)
        assert len(open_incidents) >= 1
        assert all(i.status == IncidentStatus.OPEN for i in open_incidents)

    def test_update_incident_status(self):
        """Test updating incident status."""
        detector = IncidentDetector()

        violation = SLOViolation(
            slo_id="test_slo",
            status=SLOStatus.VIOLATED,
            measured_value=85.0,
            target=95.0,
            alert_threshold=90.0,
            timestamp=datetime.now(),
        )

        incidents = detector.detect_from_slo_violations([violation])
        incident_id = incidents[0].id

        updated = detector.update_incident_status(
            incident_id, IncidentStatus.ACKNOWLEDGED
        )

        assert updated is not None
        assert updated.status == IncidentStatus.ACKNOWLEDGED
        assert updated.acknowledged_at is not None

    def test_resolve_incident(self):
        """Test resolving incident."""
        detector = IncidentDetector()

        violation = SLOViolation(
            slo_id="test_slo",
            status=SLOStatus.VIOLATED,
            measured_value=85.0,
            target=95.0,
            alert_threshold=90.0,
            timestamp=datetime.now(),
        )

        incidents = detector.detect_from_slo_violations([violation])
        incident_id = incidents[0].id

        resolved = detector.resolve_incident(incident_id, "Fixed issue")

        assert resolved is not None
        assert resolved.status == IncidentStatus.RESOLVED
        assert resolved.resolution == "Fixed issue"
        assert resolved.resolved_at is not None


class TestPlaybookExecutor:
    """Test PlaybookExecutor functionality."""

    def test_executor_initialization(self):
        """Test executor can be initialized."""
        executor = PlaybookExecutor()
        assert executor is not None

    def test_execute_playbook_runs_steps(self):
        """Test executor runs playbook steps in order."""
        executor = PlaybookExecutor()

        playbook = Playbook(
            id="test_playbook",
            name="Test Playbook",
            description="Test",
            trigger_slo="test_slo",
            steps=[
                PlaybookStep(
                    id="step1",
                    name="Log message",
                    action=StepAction.LOG,
                    params={"level": "info", "message": "Test log"},
                ),
                PlaybookStep(
                    id="step2",
                    name="Query data",
                    action=StepAction.QUERY,
                    params={"query_type": "test", "target": "store"},
                ),
            ],
        )

        result = executor.execute(playbook)

        assert result.success is True
        assert result.steps_executed == 2
        assert result.steps_failed == 0
        assert len(result.step_results) == 2

    def test_execute_playbook_with_context(self):
        """Test executor passes context to steps."""
        executor = PlaybookExecutor()

        playbook = Playbook(
            id="test_playbook",
            name="Test Playbook",
            description="Test",
            trigger_slo="test_slo",
            steps=[
                PlaybookStep(
                    id="step1",
                    name="Alert",
                    action=StepAction.ALERT,
                    params={"channel": "slack", "message": "Test alert"},
                ),
            ],
        )

        context = {"pool_id": "pool-001", "success_rate": 85.0}
        result = executor.execute(playbook, context=context)

        assert result.success is True
        assert result.steps_executed == 1

    def test_execute_playbook_skips_conditional_step(self):
        """Test executor skips steps when condition not met."""
        executor = PlaybookExecutor()

        playbook = Playbook(
            id="test_playbook",
            name="Test Playbook",
            description="Test",
            trigger_slo="test_slo",
            steps=[
                PlaybookStep(
                    id="step1",
                    name="Unconditional",
                    action=StepAction.LOG,
                    params={"message": "Always run"},
                ),
                PlaybookStep(
                    id="step2",
                    name="Conditional",
                    action=StepAction.ALERT,
                    params={"message": "Only if success_rate < 90"},
                    condition="success_rate < 90",
                ),
            ],
        )

        # Context doesn't meet condition
        context = {"success_rate": 95.0}
        result = executor.execute(playbook, context=context)

        assert result.success is True
        assert result.steps_executed == 1  # Only first step
        assert len(result.step_results) == 2  # Both logged (one skipped)
        assert result.step_results[1]["status"] == "skipped"

    def test_execute_playbook_stops_on_failure(self):
        """Test executor stops execution on step failure."""
        executor = PlaybookExecutor()

        # Create step with unknown action to trigger failure
        playbook = Playbook(
            id="test_playbook",
            name="Test Playbook",
            description="Test",
            trigger_slo="test_slo",
            steps=[
                PlaybookStep(
                    id="step1",
                    name="Good step",
                    action=StepAction.LOG,
                    params={"message": "This works"},
                ),
                PlaybookStep(
                    id="step2",
                    name="Bad step",
                    action="invalid_action",  # This will fail
                    params={},
                ),
                PlaybookStep(
                    id="step3",
                    name="Never reached",
                    action=StepAction.LOG,
                    params={"message": "Should not run"},
                ),
            ],
        )

        result = executor.execute(playbook)

        assert result.success is False
        assert result.steps_failed == 1
        assert result.steps_executed == 1  # Only first step succeeded
        assert "failed" in result.step_results[1]["status"]


class TestConfigurationLoading:
    """Test YAML configuration loading."""

    def test_load_slos_from_config(self, tmp_path):
        """Test loading SLOs from YAML config."""
        config_path = tmp_path / "test_slos.yaml"
        config_path.write_text("""
slos:
  - id: test_slo
    name: Test SLO
    description: Test description
    target: 95.0
    alert_threshold: 90.0
    comparison: gte
""")

        slos = load_slos(config_path)

        assert "test_slo" in slos
        assert slos["test_slo"].target == 95.0

    def test_load_slos_missing_file_raises(self):
        """Test loading missing config raises error."""
        with pytest.raises(FileNotFoundError):
            load_slos(Path("/nonexistent/config.yaml"))

    def test_load_playbooks_from_config(self, tmp_path):
        """Test loading playbooks from YAML config."""
        config_path = tmp_path / "test_playbooks.yaml"
        config_path.write_text("""
playbooks:
  - id: test_playbook
    name: Test Playbook
    description: Test description
    trigger_slo: test_slo
    steps:
      - id: step1
        name: Test step
        action: log
        params:
          message: Test
""")

        playbooks = load_playbooks(config_path)

        assert "test_playbook" in playbooks
        assert len(playbooks["test_playbook"].steps) == 1

    def test_load_playbooks_missing_file_raises(self):
        """Test loading missing playbook config raises error."""
        with pytest.raises(FileNotFoundError):
            load_playbooks(Path("/nonexistent/playbooks.yaml"))


class TestIntegration:
    """Integration tests for SLO tracking workflow."""

    def test_end_to_end_slo_violation_to_incident(self):
        """Test complete workflow: measure → violation → incident → playbook."""
        # Setup
        slo = SLO(
            id="test_slo",
            name="Test SLO",
            description="Test",
            target=95.0,
            alert_threshold=90.0,
            comparison="gte",
        )
        tracker = SLOTracker(slos={"test_slo": slo})
        detector = IncidentDetector()
        executor = PlaybookExecutor()

        # Measure SLO (returns violation)
        measurement = SLOMeasurement(
            slo_id="test_slo",
            value=85.0,
            timestamp=datetime.now(),
            affected_pools=["pool-001"],
        )

        # Check for violation
        violation = tracker.check_slo("test_slo", measurement)
        assert violation is not None

        # Create incident from violation
        incidents = detector.detect_from_slo_violations([violation])
        assert len(incidents) == 1
        incident = incidents[0]

        # Execute response playbook
        playbook = Playbook(
            id="response_playbook",
            name="Response Playbook",
            description="Automated response",
            trigger_slo="test_slo",
            steps=[
                PlaybookStep(
                    id="step1",
                    name="Log incident",
                    action=StepAction.LOG,
                    params={"level": "warning", "message": "Incident detected"},
                ),
                PlaybookStep(
                    id="step2",
                    name="Alert team",
                    action=StepAction.ALERT,
                    params={"channel": "slack", "message": "SLO violated"},
                ),
            ],
        )

        result = executor.execute(playbook, context={"incident_id": incident.id})
        assert result.success is True

        # Resolve incident
        resolved = detector.resolve_incident(incident.id, "Playbook executed")
        assert resolved.status == IncidentStatus.RESOLVED
