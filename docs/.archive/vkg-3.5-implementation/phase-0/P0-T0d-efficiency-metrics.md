# [P0-T0d] Efficiency Metrics & Continuous Feedback Loop

**Phase**: 0 - Knowledge Foundation (Pre-requisite)
**Task ID**: P0-T0d
**Status**: NOT_STARTED
**Priority**: CRITICAL (Enables measurable improvement)
**Estimated Effort**: 2-3 days
**Actual Effort**: -
**Depends On**: P0-T0a (Research), P0-T0c (Context Optimization)

---

## The Brutal Truth About Metrics

**Without metrics, we're flying blind.**

Every claim about VKG's effectiveness must be backed by hard numbers:
- "VKG improves LLM precision" → Prove it with A/B tests
- "Context optimization saves tokens" → Show the before/after
- "Business logic detection works" → Measure against labeled corpus
- "Cost is acceptable" → Track actual $ spent per audit

**This task creates the infrastructure for continuous, honest self-assessment.**

---

## Core Metrics Framework

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BSKG EFFICIENCY METRICS DASHBOARD                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      QUALITY METRICS                                 │    │
│  │                                                                      │    │
│  │  Precision        Recall          F1 Score        Consistency       │    │
│  │  ┌────────┐      ┌────────┐      ┌────────┐      ┌────────┐        │    │
│  │  │  85%   │      │  78%   │      │  81%   │      │  92%   │        │    │
│  │  │  ▲ +5% │      │  ▲ +3% │      │  ▲ +4% │      │  ▲ +7% │        │    │
│  │  └────────┘      └────────┘      └────────┘      └────────┘        │    │
│  │                                                                      │    │
│  │  FP Rate         FN Rate         BL Detection    Confidence         │    │
│  │  ┌────────┐      ┌────────┐      ┌────────┐      ┌────────┐        │    │
│  │  │  4.2%  │      │  22%   │      │  45%   │      │  0.82  │        │    │
│  │  │  ▼ -2% │      │  ▼ -3% │      │  ▲ +10%│      │  ▲ +0.1│        │    │
│  │  └────────┘      └────────┘      └────────┘      └────────┘        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     EFFICIENCY METRICS                               │    │
│  │                                                                      │    │
│  │  Tokens/Function  Cost/TP         Latency         Triage Accuracy   │    │
│  │  ┌────────┐      ┌────────┐      ┌────────┐      ┌────────┐        │    │
│  │  │  450   │      │ $0.08  │      │  1.2s  │      │  94%   │        │    │
│  │  │  ▼ -85%│      │  ▼ -92%│      │  ▼ -65%│      │  ▲ +4% │        │    │
│  │  └────────┘      └────────┘      └────────┘      └────────┘        │    │
│  │                                                                      │    │
│  │  Cache Hit Rate  Compression     Level 0 Skip    Escalation Rate   │    │
│  │  ┌────────┐      ┌────────┐      ┌────────┐      ┌────────┐        │    │
│  │  │  78%   │      │  6.2x  │      │  42%   │      │  15%   │        │    │
│  │  │  ▲ +12%│      │  ▲ +0.5│      │  ▲ +5% │      │  ▼ -3% │        │    │
│  │  └────────┘      └────────┘      └────────┘      └────────┘        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      TREND ANALYSIS                                  │    │
│  │                                                                      │    │
│  │  Precision Over Time:                                                │    │
│  │  100% ┤                                                              │    │
│  │   90% ┤                              ●●●●                           │    │
│  │   80% ┤                    ●●●●●●●●●●                               │    │
│  │   70% ┤          ●●●●●●●●●●                                         │    │
│  │   60% ┤  ●●●●●●●●                                                   │    │
│  │       └──────────────────────────────────────────────▶ Time         │    │
│  │         Week 1  Week 2  Week 3  Week 4  Week 5                      │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Metric Categories

### 1. Quality Metrics (Primary)

| Metric | Definition | Target | Why It Matters |
|--------|------------|--------|----------------|
| **Precision** | TP / (TP + FP) | >= 85% | False positives waste auditor time |
| **Recall** | TP / (TP + FN) | >= 80% | Missed vulns are catastrophic |
| **F1 Score** | 2 * (P * R) / (P + R) | >= 82% | Balanced quality measure |
| **Consistency** | Agreement across 3 runs | >= 90% | Unreliable results are useless |
| **FP Rate** | FP / (FP + TN) | <= 5% | Safe code flagged wastes time |
| **BL Detection** | Recall on business logic corpus | >= 50% | Core BSKG 3.5 differentiator |
| **Confidence Calibration** | How often 80% confidence = 80% correct | r² >= 0.9 | Trustworthy confidence scores |

### 2. Efficiency Metrics

| Metric | Definition | Target | Why It Matters |
|--------|------------|--------|----------------|
| **Tokens/Function** | Average input tokens per analysis | <= 500 | Cost and latency driver |
| **Cost/True Positive** | Total cost / true positives found | <= $0.10 | Economic viability |
| **Latency/Function** | Time from input to verdict | <= 2s | User experience |
| **Compression Ratio** | Original tokens / compressed tokens | >= 5x | Efficiency measure |
| **Cache Hit Rate** | Cached responses / total requests | >= 70% | Cost reduction |
| **Level 0 Skip Rate** | Functions triaged to no-LLM | >= 40% | Token savings |
| **Escalation Rate** | L1 → L2/L3 escalations | <= 20% | Triage accuracy |

### 3. Provider Metrics

| Metric | Per Provider | Why Track |
|--------|--------------|-----------|
| **Availability** | Uptime % | Failover planning |
| **Latency P50/P95** | Response times | Performance tuning |
| **Error Rate** | Failed requests % | Reliability |
| **Token Accuracy** | Estimated vs actual tokens | Budget accuracy |
| **Cost Variance** | Estimated vs actual cost | Budget planning |

---

## Data Collection Infrastructure

### Telemetry Schema

```python
# src/true_vkg/llm/telemetry.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum
import json

class TriageLevel(Enum):
    SKIP = 0
    QUICK = 1
    FOCUSED = 2
    DEEP = 3

class Verdict(Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    VULNERABLE = "vulnerable"

@dataclass
class AnalysisEvent:
    """Single function analysis telemetry."""
    # Identity
    event_id: str
    timestamp: datetime
    session_id: str

    # Input
    function_id: str
    contract_name: str
    source_tokens: int  # Raw source token count

    # Triage
    triage_level: TriageLevel
    triage_reason: str

    # Context
    context_tokens: int  # After compression
    compression_ratio: float
    context_tier: int  # 1-5

    # LLM Interaction
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cached: bool
    cost_usd: float

    # Output
    verdict: Verdict
    confidence: float
    findings: List[Dict]

    # Ground Truth (when available)
    ground_truth: Optional[Verdict] = None
    is_correct: Optional[bool] = None

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "function_id": self.function_id,
            "contract_name": self.contract_name,
            "source_tokens": self.source_tokens,
            "triage_level": self.triage_level.value,
            "context_tokens": self.context_tokens,
            "compression_ratio": self.compression_ratio,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
            "cost_usd": self.cost_usd,
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "is_correct": self.is_correct
        }


@dataclass
class SessionMetrics:
    """Aggregated metrics for an analysis session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None

    # Counts
    functions_analyzed: int = 0
    level_0_skipped: int = 0
    level_1_quick: int = 0
    level_2_focused: int = 0
    level_3_deep: int = 0

    # Quality (when ground truth available)
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    # Efficiency
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    cache_hits: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def skip_rate(self) -> float:
        return self.level_0_skipped / self.functions_analyzed if self.functions_analyzed > 0 else 0.0

    @property
    def cost_per_function(self) -> float:
        return self.total_cost_usd / self.functions_analyzed if self.functions_analyzed > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.functions_analyzed if self.functions_analyzed > 0 else 0.0


class TelemetryCollector:
    """Collects and persists telemetry data."""

    def __init__(self, storage_path: str = "metrics/telemetry.jsonl"):
        self.storage_path = storage_path
        self.current_session: Optional[SessionMetrics] = None
        self.events: List[AnalysisEvent] = []

    def start_session(self) -> str:
        """Start a new analysis session."""
        import uuid
        session_id = str(uuid.uuid4())
        self.current_session = SessionMetrics(
            session_id=session_id,
            start_time=datetime.now()
        )
        return session_id

    def record_event(self, event: AnalysisEvent):
        """Record a single analysis event."""
        self.events.append(event)
        self._update_session(event)
        self._persist_event(event)

    def end_session(self) -> SessionMetrics:
        """End current session and return metrics."""
        if self.current_session:
            self.current_session.end_time = datetime.now()
            self._persist_session(self.current_session)
        return self.current_session

    def _update_session(self, event: AnalysisEvent):
        """Update session aggregates from event."""
        s = self.current_session
        if not s:
            return

        s.functions_analyzed += 1
        s.total_tokens += event.prompt_tokens + event.completion_tokens
        s.total_cost_usd += event.cost_usd
        s.total_latency_ms += event.latency_ms

        if event.cached:
            s.cache_hits += 1

        # Update level counts
        level_map = {
            TriageLevel.SKIP: "level_0_skipped",
            TriageLevel.QUICK: "level_1_quick",
            TriageLevel.FOCUSED: "level_2_focused",
            TriageLevel.DEEP: "level_3_deep",
        }
        attr = level_map.get(event.triage_level)
        if attr:
            setattr(s, attr, getattr(s, attr) + 1)

        # Update quality metrics if ground truth available
        if event.ground_truth is not None:
            predicted_vuln = event.verdict == Verdict.VULNERABLE
            actual_vuln = event.ground_truth == Verdict.VULNERABLE

            if predicted_vuln and actual_vuln:
                s.true_positives += 1
            elif predicted_vuln and not actual_vuln:
                s.false_positives += 1
            elif not predicted_vuln and actual_vuln:
                s.false_negatives += 1
            else:
                s.true_negatives += 1

    def _persist_event(self, event: AnalysisEvent):
        """Persist event to storage."""
        with open(self.storage_path, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def _persist_session(self, session: SessionMetrics):
        """Persist session summary."""
        session_path = self.storage_path.replace(".jsonl", "_sessions.jsonl")
        with open(session_path, "a") as f:
            f.write(json.dumps(session.__dict__, default=str) + "\n")
```

---

## Continuous Feedback Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS FEEDBACK LOOP                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                      │    │
│  │      ┌──────────┐                                                    │    │
│  │      │  AUDIT   │ ◀─────────────────────────────────────────────┐   │    │
│  │      │  SESSION │                                                │   │    │
│  │      └────┬─────┘                                                │   │    │
│  │           │                                                      │   │    │
│  │           ▼                                                      │   │    │
│  │      ┌──────────┐                                                │   │    │
│  │      │ TELEMETRY│  Record every: triage, compression,           │   │    │
│  │      │ COLLECT  │  LLM call, verdict, timing, cost              │   │    │
│  │      └────┬─────┘                                                │   │    │
│  │           │                                                      │   │    │
│  │           ▼                                                      │   │    │
│  │      ┌──────────┐                                                │   │    │
│  │      │ SESSION  │  Aggregate: P/R/F1, cost, latency,            │   │    │
│  │      │ SUMMARY  │  skip rate, cache hits                        │   │    │
│  │      └────┬─────┘                                                │   │    │
│  │           │                                                      │   │    │
│  │           ▼                                                      │   │    │
│  │      ┌──────────┐     ┌──────────┐                              │   │    │
│  │      │  DRIFT   │────▶│  ALERT   │  If metrics drift > 10%     │   │    │
│  │      │ DETECTOR │     │          │  from target                 │   │    │
│  │      └────┬─────┘     └──────────┘                              │   │    │
│  │           │                                                      │   │    │
│  │           ▼                                                      │   │    │
│  │      ┌──────────┐                                                │   │    │
│  │      │  WEEKLY  │  Human review of:                             │   │    │
│  │      │  REVIEW  │  - Worst failures (FP/FN examples)            │   │    │
│  │      │          │  - Cost outliers                               │   │    │
│  │      │          │  - Trend changes                               │   │    │
│  │      └────┬─────┘                                                │   │    │
│  │           │                                                      │   │    │
│  │           ▼                                                      │   │    │
│  │      ┌──────────┐                                                │   │    │
│  │      │  TUNING  │  Adjust: thresholds, budgets, prompts         │   │    │
│  │      │  ACTION  │─────────────────────────────────────────────▶│   │    │
│  │      └──────────┘                                                │   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  CADENCE:                                                                   │
│  • Telemetry: Every function                                                │
│  • Session summary: Every audit                                             │
│  • Drift detection: Daily                                                   │
│  • Human review: Weekly                                                     │
│  • Tuning cycle: Bi-weekly                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Drift Detection

### What is Drift?

Metrics drifting from baseline indicates something changed:
- LLM model update (provider-side)
- Input distribution changed (different project types)
- Bug introduced in code
- Prompt template degraded

### Drift Detection Rules

```python
# src/true_vkg/llm/drift.py

from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta

@dataclass
class DriftAlert:
    """Alert for detected metric drift."""
    metric: str
    baseline: float
    current: float
    drift_pct: float
    severity: str  # "warning" or "critical"
    timestamp: datetime


class DriftDetector:
    """Detect drift in quality and efficiency metrics."""

    # Thresholds for drift detection
    THRESHOLDS = {
        "precision": {"warning": 0.05, "critical": 0.10},
        "recall": {"warning": 0.05, "critical": 0.10},
        "cost_per_function": {"warning": 0.20, "critical": 0.50},
        "latency_ms": {"warning": 0.30, "critical": 0.50},
        "fp_rate": {"warning": 0.02, "critical": 0.05},
    }

    def __init__(self, baseline: Dict[str, float]):
        self.baseline = baseline
        self.alerts: List[DriftAlert] = []

    def check(self, current: Dict[str, float]) -> List[DriftAlert]:
        """Check current metrics against baseline."""
        alerts = []

        for metric, threshold in self.THRESHOLDS.items():
            if metric not in current or metric not in self.baseline:
                continue

            base_val = self.baseline[metric]
            curr_val = current[metric]

            if base_val == 0:
                continue

            drift = abs(curr_val - base_val) / base_val

            if drift >= threshold["critical"]:
                alerts.append(DriftAlert(
                    metric=metric,
                    baseline=base_val,
                    current=curr_val,
                    drift_pct=drift,
                    severity="critical",
                    timestamp=datetime.now()
                ))
            elif drift >= threshold["warning"]:
                alerts.append(DriftAlert(
                    metric=metric,
                    baseline=base_val,
                    current=curr_val,
                    drift_pct=drift,
                    severity="warning",
                    timestamp=datetime.now()
                ))

        self.alerts.extend(alerts)
        return alerts

    def get_trend(
        self,
        metric: str,
        window_days: int = 7
    ) -> Dict[str, float]:
        """Get trend for a metric over time window."""
        # Implementation would query historical data
        pass
```

---

## Reporting Infrastructure

### Daily Report (Automated)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BSKG DAILY METRICS REPORT                                  │
│                    Date: 2026-01-03                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SESSIONS: 3 completed                                                       │
│  FUNCTIONS ANALYZED: 247                                                     │
│                                                                              │
│  QUALITY                              vs Baseline                            │
│  ──────────────────────────────────────────────────                         │
│  Precision:     87.2%                 ▲ +2.2%                               │
│  Recall:        79.5%                 ▲ +1.5%                               │
│  F1:            83.1%                 ▲ +1.8%                               │
│  FP Rate:       3.8%                  ▼ -0.4%                               │
│                                                                              │
│  EFFICIENCY                           vs Baseline                            │
│  ──────────────────────────────────────────────────                         │
│  Tokens/fn:     412                   ▼ -88 (18% savings)                   │
│  Cost/fn:       $0.006                ▼ -15%                                │
│  Latency:       1.3s                  ▲ +0.1s                               │
│  Cache hits:    72%                   ▲ +5%                                 │
│                                                                              │
│  TRIAGE DISTRIBUTION                                                         │
│  ──────────────────────────────────────────────────                         │
│  Level 0 (Skip):    45% (111 functions)                                     │
│  Level 1 (Quick):   32% (79 functions)                                      │
│  Level 2 (Focused): 18% (44 functions)                                      │
│  Level 3 (Deep):    5% (13 functions)                                       │
│                                                                              │
│  ALERTS: 0 critical, 1 warning                                              │
│  ⚠️ Latency P95 increased 25% (monitoring)                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Weekly Review Template

```markdown
# BSKG Weekly Metrics Review

**Week**: 2026-W01
**Reviewer**: [Name]

## Summary Statistics

| Metric | Week | Previous | Change | Status |
|--------|------|----------|--------|--------|
| Sessions | X | Y | +/-Z% | 🟢/🟡/🔴 |
| Functions | X | Y | +/-Z% | 🟢/🟡/🔴 |
| Precision | X% | Y% | +/-Z% | 🟢/🟡/🔴 |
| Recall | X% | Y% | +/-Z% | 🟢/🟡/🔴 |
| Cost/TP | $X | $Y | +/-Z% | 🟢/🟡/🔴 |

## Notable Failures

### False Positive Analysis
| Function | Why FP? | Proposed Fix |
|----------|---------|--------------|
| ... | ... | ... |

### False Negative Analysis
| Function | Why Missed? | Proposed Fix |
|----------|-------------|--------------|
| ... | ... | ... |

## Actions Taken
- [ ] Action 1
- [ ] Action 2

## Next Week Focus
- Focus area 1
- Focus area 2
```

---

## Success Criteria

- [ ] TelemetryCollector implemented and integrated
- [ ] SessionMetrics automatically calculated
- [ ] Drift detection running daily
- [ ] Daily report generation automated
- [ ] Weekly review template created
- [ ] Historical data stored and queryable
- [ ] Dashboard visualization (CLI or web)
- [ ] Baseline established from first 100 functions

---

## Integration Points

**Consumes from:**
- P0-T0c (Context Optimization): Compression metrics, triage decisions
- P0-T0 (Provider Abstraction): Provider latency, cost, token counts

**Provides to:**
- P0-T0c (Context Optimization): Feedback for tuning triage thresholds
- P2-T5 (Arbiter): Quality metrics for verdict calibration
- All tasks: Ground truth for improvement experiments

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-03 | Created task | Claude |
