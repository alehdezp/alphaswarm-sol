# SLO Definitions Reference

Complete specification for `configs/slo_definitions.yaml`.

## Overview

Service Level Objectives (SLOs) define reliability targets for AlphaSwarm multi-agent orchestration. Each SLO includes a target value, alert threshold, and measurement window.

## Schema

```yaml
slos:
  - id: string                         # Unique SLO identifier
    name: string                       # Human-readable name
    description: string                # What this SLO measures
    target: float                      # Target performance level
    alert_threshold: float             # Alert trigger level
    measurement_window_minutes: int    # Measurement window (default: 5)
    comparison: string                 # 'gte' (higher is better) or 'lte' (lower is better)
```

## Comparison Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `gte` | Greater than or equal (higher is better) | Success rate ≥ 95% |
| `lte` | Less than or equal (lower is better) | Latency ≤ 300s |

## Default SLOs

### pool_success_rate

Percentage of audit pools that complete successfully without errors.

```yaml
- id: pool_success_rate
  name: Pool Success Rate
  description: Percentage of audit pools that complete successfully without errors
  target: 95.0              # 95% or higher
  alert_threshold: 90.0     # Alert if drops below 90%
  measurement_window_minutes: 5
  comparison: gte           # Higher is better
```

**Measurement:**
```
success_rate = (successful_pools / total_pools) × 100
```

**Interpretation:**
- Target: 95% of pools should succeed
- Alert: Triggered if success rate drops below 90%
- Severity: Critical (pool failures indicate system issues)

### pool_completion_latency_p95

95th percentile pool completion time in seconds.

```yaml
- id: pool_completion_latency_p95
  name: Pool Completion Latency P95
  description: 95th percentile pool completion time in seconds
  target: 300.0             # 5 minutes target
  alert_threshold: 360.0    # Alert if exceeds 6 minutes
  measurement_window_minutes: 5
  comparison: lte           # Lower is better
```

**Measurement:**
```
latency_p95 = percentile(pool_completion_times, 95)
pool_completion_time = completed_at - created_at
```

**Interpretation:**
- Target: 95% of pools complete within 5 minutes
- Alert: Triggered if P95 exceeds 6 minutes
- Severity: High (latency impacts user experience)

### verdict_accuracy

Percentage of verdicts that match ground truth (when available).

```yaml
- id: verdict_accuracy
  name: Verdict Accuracy
  description: Percentage of verdicts that match ground truth (when available)
  target: 90.0              # 90% or higher
  alert_threshold: 85.0     # Alert if drops below 85%
  measurement_window_minutes: 5
  comparison: gte           # Higher is better
```

**Measurement:**
```
accuracy = (correct_verdicts / total_verdicts_with_ground_truth) × 100
```

**Interpretation:**
- Target: 90% of verdicts match ground truth
- Alert: Triggered if accuracy drops below 85%
- Severity: High (accuracy is core to system value)
- Note: Requires ground truth labels for measurement

### cost_per_finding

Average cost in USD per vulnerability finding.

```yaml
- id: cost_per_finding
  name: Cost Per Finding
  description: Average cost in USD per vulnerability finding
  target: 2.00              # $2.00 or less
  alert_threshold: 3.00     # Alert if exceeds $3.00
  measurement_window_minutes: 5
  comparison: lte           # Lower is better
```

**Measurement:**
```
cost_per_finding = total_cost_usd / confirmed_findings_count
```

**Interpretation:**
- Target: Each finding costs ≤ $2.00
- Alert: Triggered if cost exceeds $3.00 per finding
- Severity: Medium (cost efficiency matters but not critical)

### bead_mttr

Average time in seconds to resolve failed beads (Mean Time To Resolution).

```yaml
- id: bead_mttr
  name: Bead Mean Time To Resolution
  description: Average time in seconds to resolve failed beads
  target: 60.0              # 1 minute target
  alert_threshold: 120.0    # Alert if exceeds 2 minutes
  measurement_window_minutes: 5
  comparison: lte           # Lower is better
```

**Measurement:**
```
mttr = mean(resolution_times)
resolution_time = resolved_at - failed_at
```

**Interpretation:**
- Target: Failed beads resolved within 1 minute
- Alert: Triggered if MTTR exceeds 2 minutes
- Severity: High (recovery time impacts system resilience)

## Custom SLOs

You can add custom SLOs for project-specific needs:

```yaml
slos:
  - id: custom_slo
    name: Custom SLO Name
    description: "Description of what this measures"
    target: 95.0
    alert_threshold: 90.0
    measurement_window_minutes: 10  # 10 minute window
    comparison: gte
```

### Example: Agent Utilization

```yaml
- id: agent_utilization
  name: Agent Utilization Rate
  description: Percentage of time agents are actively working vs idle
  target: 70.0              # Target 70% utilization
  alert_threshold: 50.0     # Alert if drops below 50%
  measurement_window_minutes: 15
  comparison: gte
```

### Example: Evidence Quality

```yaml
- id: evidence_quality_score
  name: Evidence Quality Score
  description: Average quality score of evidence references (0-100)
  target: 80.0              # Target quality score of 80
  alert_threshold: 70.0     # Alert if quality drops below 70
  measurement_window_minutes: 5
  comparison: gte
```

## SLO Violation

When an SLO is violated, the system generates an `SLOViolation`:

```python
@dataclass
class SLOViolation:
    slo_id: str                # SLO identifier (e.g., "pool_success_rate")
    slo_name: str              # Human-readable name
    measured_value: float      # Actual measured value
    target_value: float        # Target value
    alert_threshold: float     # Alert threshold
    severity: str              # "critical", "high", "medium", "low"
    message: str               # Violation description
    timestamp: datetime        # When violation occurred
```

**Example:**
```python
SLOViolation(
    slo_id="pool_success_rate",
    slo_name="Pool Success Rate",
    measured_value=88.5,
    target_value=95.0,
    alert_threshold=90.0,
    severity="critical",
    message="Pool success rate 88.5% below alert threshold 90.0%",
    timestamp=datetime.now(timezone.utc),
)
```

## Usage

### Loading SLOs

```python
from alphaswarm_sol.reliability import load_slos
from pathlib import Path

slos = load_slos(Path("configs/slo_definitions.yaml"))
```

### Creating SLOTracker

```python
from alphaswarm_sol.reliability import SLOTracker
from alphaswarm_sol.beads.event_store import EventStore
from alphaswarm_sol.metrics.cost_ledger import CostLedger

tracker = SLOTracker(
    event_store=EventStore(),
    cost_ledger=CostLedger(),
)
```

### Measuring SLOs

```python
# Measure specific SLO
measurement = tracker.measure_slo(
    slo_id="pool_success_rate",
    pool_id="audit-pool-001",  # Optional: specific pool
)

print(f"Measured: {measurement.value}")
print(f"Target: {measurement.target}")
print(f"Meets target: {measurement.meets_target}")

# Check for violations
violation = tracker.check_slo("pool_success_rate", measurement)
if violation:
    print(f"SLO violated: {violation.message}")
```

### Monitoring All SLOs

```python
# Check all SLOs
violations = tracker.monitor_all_slos()

for violation in violations:
    print(f"[{violation.severity}] {violation.slo_name}")
    print(f"  Measured: {violation.measured_value}")
    print(f"  Threshold: {violation.alert_threshold}")
```

## Best Practices

1. **Measurement windows**: Use 5 minutes for real-time monitoring, longer for trend analysis
2. **Alert thresholds**: Set at 90-95% of target to catch degradation early
3. **Comparison operators**: Use `gte` for rates/percentages, `lte` for latencies/costs
4. **Custom SLOs**: Add project-specific SLOs for business metrics
5. **Ground truth**: Maintain ground truth labels for accuracy measurement
6. **Review regularly**: Adjust targets based on actual performance trends

## Severity Levels

| Severity | When to Use | Response Time |
|----------|-------------|---------------|
| `critical` | System-wide failures, data loss | Immediate |
| `high` | Performance degradation, accuracy issues | < 15 minutes |
| `medium` | Cost overruns, minor latency | < 1 hour |
| `low` | Non-urgent optimization opportunities | < 1 day |

## See Also

- [Reliability Guide](../guides/reliability.md)
- [Incident Playbooks](../guides/reliability.md#incident-playbooks)
- [SLO Tracking Guide](../guides/reliability.md#track-slos)
