# Reliability Guide

This guide explains how to use SLO tracking, incident detection, playbooks, and chaos testing for production reliability.

## Overview

Phase 7.1.5 reliability provides:

- **SLO Tracking**: Automated measurement of success rate, latency, cost, accuracy
- **Incident Detection**: Automatic incident creation from SLO violations
- **Playbooks**: Automated incident response with configurable steps
- **Chaos Testing**: Fault injection for resilience validation

## Quick Start

### Track SLOs

```python
from alphaswarm_sol.reliability import SLOTracker, load_slos
from alphaswarm_sol.beads.event_store import EventStore
from alphaswarm_sol.metrics.cost_ledger import CostLedger
from pathlib import Path

# Load SLO definitions
slos = load_slos(Path("configs/slo_definitions.yaml"))

# Create tracker
tracker = SLOTracker(
    event_store=EventStore(),
    cost_ledger=CostLedger(),
)

# Check single SLO
violation = tracker.check_slo("pool_success_rate")
if violation:
    print(f"SLO violated: {violation.slo_name} at {violation.measured_value}")

# Check all SLOs
violations = tracker.monitor_all_slos()
for violation in violations:
    print(f"[{violation.severity}] {violation.slo_name}: {violation.message}")
```

### Detect Incidents

```python
from alphaswarm_sol.reliability import IncidentDetector

detector = IncidentDetector(slo_tracker=tracker)

# Create incidents from violations
incidents = detector.detect_from_slo_violations(violations)

for incident in incidents:
    print(f"[{incident.severity.value}] {incident.title}")
    print(f"  Status: {incident.status.value}")
    print(f"  Created: {incident.created_at}")
```

### Execute Playbooks

```python
from alphaswarm_sol.reliability import PlaybookExecutor, load_playbooks

def send_alert(severity, channel, message):
    # Your alerting logic
    print(f"[{severity}] {channel}: {message}")

executor = PlaybookExecutor(
    event_store=event_store,
    alert_sender=send_alert,
)

# Load playbooks
playbooks = load_playbooks(Path("configs/incident_playbooks.yaml"))

# Execute playbook for incident
result = executor.execute(
    playbooks["pool_success_rate_degradation"],
    incident,
)

print(f"Playbook completed: {result.steps_completed}/{result.total_steps}")
```

## SLO Definitions

### Default SLOs

| SLO | Target | Window | Alert Threshold | Comparison |
|-----|--------|--------|-----------------|------------|
| pool_success_rate | 95% | 5 min | 90% | gte (higher is better) |
| pool_completion_latency_p95 | 300s | 5 min | 360s | lte (lower is better) |
| verdict_accuracy | 90% | 5 min | 85% | gte (higher is better) |
| cost_per_finding | $2.00 | 5 min | $3.00 | lte (lower is better) |
| bead_mttr | 60s | 5 min | 120s | lte (lower is better) |

### Custom SLOs

```yaml
# configs/slo_definitions.yaml
slos:
  - id: custom_slo
    name: Custom SLO Name
    description: "Description of what this measures"
    target: 95.0
    alert_threshold: 90.0
    measurement_window_minutes: 5
    comparison: gte  # or 'lte'
```

### SLO Measurement

```python
from alphaswarm_sol.reliability import SLOTracker

# Measure specific SLO
measurement = tracker.measure_slo(
    slo_id="pool_success_rate",
    pool_id="audit-pool-001",  # Optional: specific pool
)

print(f"Measured value: {measurement.value}")
print(f"Target: {measurement.target}")
print(f"Meets target: {measurement.meets_target}")
```

## Incident Playbooks

### Playbook Structure

```yaml
# configs/incident_playbooks.yaml
playbooks:
  - id: pool_success_rate_degradation
    name: Pool Success Rate Degradation
    description: Respond to pool success rate dropping below threshold
    trigger_slo: pool_success_rate
    steps:
      - id: step1
        name: Query failing pools
        action: query
        params:
          query_type: failed_pools
          target: event_store
          time_window_minutes: 5

      - id: step2
        name: Log degradation details
        action: log
        params:
          level: warning
          message: "Pool success rate degraded - investigating failed pools"

      - id: step3
        name: Alert operations team
        action: alert
        params:
          channel: slack
          message: "Pool success rate below threshold - check pool execution logs"

      - id: step4
        name: Escalate if critical
        action: escalate
        params:
          to: oncall
          reason: "Pool success rate critically degraded"
        condition: "success_rate < 85"
```

### Available Actions

| Action | Description | Params |
|--------|-------------|--------|
| `query` | Query data stores | `query_type`, `target`, `time_window_minutes` |
| `alert` | Send notification | `channel`, `message` |
| `log` | Log information | `level`, `message` |
| `escalate` | Escalate to on-call | `to`, `reason` |
| `retry` | Retry operation | `operation`, `max_attempts` |

### Conditional Steps

```yaml
steps:
  - id: escalate_critical
    name: Escalate if critical
    action: escalate
    params:
      to: oncall
      reason: "Critical SLO violation"
    condition: "success_rate < 85"  # Only execute if condition true
```

## Chaos Testing

### Setup Chaos Harness

```python
from alphaswarm_sol.reliability.chaos import (
    ChaosTestHarness,
    ChaosExperiment,
    FaultType,
    CHAOS_TEMPLATES,
)

harness = ChaosTestHarness(enabled=True, seed=42)

# Use pre-built template
harness.add_experiment(CHAOS_TEMPLATES["api_timeout_20pct"])

# Or create custom experiment
harness.add_experiment(ChaosExperiment(
    name="custom_fault",
    fault_type=FaultType.API_ERROR,
    injection_rate=0.15,  # 15% of calls fail
    fault_params={"status_code": 503},
    target_component="llm",
))
```

### Pre-built Templates

| Template | Fault Type | Injection Rate | Description |
|----------|-----------|----------------|-------------|
| `api_timeout_20pct` | API_TIMEOUT | 20% | 20% of API calls timeout |
| `api_error_10pct` | API_ERROR | 10% | 10% return 500 errors |
| `malformed_response_5pct` | MALFORMED_RESPONSE | 5% | 5% return invalid JSON |
| `rate_limit_15pct` | RATE_LIMIT | 15% | 15% hit rate limits |
| `cost_spike_10pct` | COST_SPIKE | 10% | 10% have inflated costs |

### Instrument Functions

```python
from alphaswarm_sol.reliability.chaos import with_chaos_testing

@with_chaos_testing("llm")
def call_llm(prompt: str, chaos_harness=None):
    # Normal LLM call
    return llm.generate(prompt)

# Faults injected based on experiment
result = call_llm("test", chaos_harness=harness)
```

### Fault Types

| Type | Description | Params |
|------|-------------|--------|
| `API_TIMEOUT` | Delay then timeout | `delay_seconds`, `timeout_seconds` |
| `API_ERROR` | HTTP error response | `status_code`, `error_message` |
| `MALFORMED_RESPONSE` | Invalid JSON/schema | `malformed_type` |
| `AGENT_FAILURE` | Agent crash | `error_type` |
| `COMMUNICATION_DELAY` | Slow handoff | `delay_seconds` |
| `COST_SPIKE` | Inflated cost | `multiplier` |
| `SCHEMA_VIOLATION` | Wrong output format | `violation_type` |
| `RATE_LIMIT` | Quota exceeded | `retry_after_seconds` |

### Measure Resilience

```python
# Run chaos tests
for i in range(100):
    try:
        result = call_llm("test", chaos_harness=harness)
    except Exception as e:
        # System should handle gracefully
        harness.record_recovery(recovery_time_seconds=0.01)

# Get results
results = harness.get_results()
print(f"Success rate: {results.success_rate:.1%}")
print(f"MTTR: {results.mttr:.2f}s")
print(f"Total faults injected: {results.total_faults}")
print(f"Recoveries: {results.total_recoveries}")

# Assert resilience targets
assert results.success_rate >= 0.75, "System not resilient enough"
assert results.mttr <= 0.1, "Recovery too slow"
```

### Integration with Tests

```python
# tests/test_chaos_scenarios.py
import pytest
from alphaswarm_sol.reliability.chaos import ChaosTestHarness, CHAOS_TEMPLATES

def test_llm_resilience():
    harness = ChaosTestHarness(enabled=True)
    harness.add_experiment(CHAOS_TEMPLATES["api_timeout_20pct"])

    # Run pool with chaos
    pool_manager = PoolManager(chaos_harness=harness)
    result = pool_manager.execute_pool("test-pool")

    # Should still complete despite faults
    assert result.status == "completed"

    # Check resilience metrics
    chaos_results = harness.get_results()
    assert chaos_results.success_rate >= 0.75
```

## Dashboards

### Generate Ops Dashboard

```bash
# CLI command
uv run alphaswarm ops dashboard --format markdown --type ops

# Or programmatically
from alphaswarm_sol.dashboards import render_ops_dashboard
print(render_ops_dashboard(format="markdown"))
```

### Dashboard Types

| Type | Content |
|------|---------|
| `ops` | Pool health, SLO status, incidents, cost |
| `latency` | P50/P95/P99, per-agent breakdown |
| `accuracy` | Precision, recall, per-pattern metrics |
| `cost` | Total spend, by agent, by pool |

### Dashboard Output

```markdown
# Operations Dashboard

**Generated:** 2026-01-29T18:30:00Z
**Time Range:** Last 5 minutes

## SLO Status

| SLO | Current | Target | Status |
|-----|---------|--------|--------|
| pool_success_rate | 96.5% | 95.0% | ✅ PASS |
| pool_completion_latency_p95 | 285s | 300s | ✅ PASS |
| cost_per_finding | $1.85 | $2.00 | ✅ PASS |

## Active Incidents

**None**

## Pool Health

- Total pools: 142
- Completed: 137 (96.5%)
- Failed: 5 (3.5%)
```

## Best Practices

1. **Run SLO checks every 5 minutes** (automated monitoring)
2. **Start chaos testing at 1% injection rate**, increase gradually
3. **Target >75% success rate** under 20% fault injection
4. **Define playbooks** for all critical SLO violations
5. **Track MTTR** to measure recovery capability
6. **Use conditional steps** in playbooks to avoid alert fatigue
7. **Seed chaos experiments** for reproducible tests

## Integration Patterns

### Continuous Monitoring

```python
import schedule
import time

def monitor_slos():
    violations = tracker.monitor_all_slos()
    if violations:
        for v in violations:
            incident = detector.create_incident_from_violation(v)
            playbook = playbooks[v.slo_name]
            executor.execute(playbook, incident)

# Run every 5 minutes
schedule.every(5).minutes.do(monitor_slos)

while True:
    schedule.run_pending()
    time.sleep(1)
```

### Pre-deployment Chaos Testing

```bash
# Run before deploying to production
uv run pytest tests/test_chaos_scenarios.py -v

# All chaos tests must pass
```

## See Also

- [SLO Definitions Reference](../reference/slo-definitions.md)
- [Observability Guide](observability.md) - Traces for debugging
- [Governance Guide](governance.md) - Policy enforcement
