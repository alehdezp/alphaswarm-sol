# Gap Analysis: What AlphaSwarm.sol Needs Before Agent Teams Migration

**Source:** Web research on 2026 AI QA patterns + iteration-analyst findings
**Date:** 2026-02-06

---

## Critical Gaps Identified

### Gap 1: No Confidence Calibration

**Current state:** Verifier verdicts are binary (CONFIRMED/FALSE_POSITIVE) with no calibrated confidence score.

**What's needed:** Every action needs a calibrated confidence score. Track predicted confidence vs actual outcomes. Route low-confidence to human review.

**Implementation:**
```python
class CalibratedVerdict:
    verdict: str  # CONFIRMED, FALSE_POSITIVE, NEEDS_REVIEW
    confidence: float  # 0.0 - 1.0, calibrated
    calibration_history: list  # Track predicted vs actual over time

    def should_escalate(self) -> bool:
        return self.confidence < 0.70
```

**Priority:** HIGH - Phase 1 (add to verifier agent)

---

### Gap 2: No Explicit Convergence Criteria

**Current state:** Self-improvement is manual. No defined stopping criteria for iteration loops.

**What's needed:** Convergence via quality threshold OR retry limit OR manual approval.

**Implementation:**
```python
class ConvergenceCriteria:
    max_iterations: int = 10
    plateau_threshold: float = 0.02  # Stop if delta < this
    target_f1: float = 0.85
    regression_threshold: float = -0.05  # Rollback if worse

    def should_stop(self, history: list) -> tuple[bool, str]:
        if len(history) >= self.max_iterations:
            return True, "MAX_ITERATIONS"
        if len(history) >= 2:
            delta = history[-1].f1 - history[-2].f1
            if abs(delta) < self.plateau_threshold:
                return True, "PLATEAU"
            if delta < self.regression_threshold:
                return True, "REGRESSION"
        if history[-1].f1 >= self.target_f1:
            return True, "TARGET_REACHED"
        return False, None
```

**Priority:** HIGH - Phase 3 (self-testing infrastructure)

---

### Gap 3: No Automated Quality Gates

**Current state:** No component-level or workflow-level quality gates before release.

**What's needed:**

| Gate Level | Metrics | Thresholds |
|-----------|---------|------------|
| Component (per agent) | Exploit completeness >= 0.80, Guard coverage >= 0.70, Evidence anchoring >= 0.90 |
| Workflow (per audit) | Pool consensus >= 0.75, F1 >= 0.80, False positive rate < 0.20 |
| Release (GA gate) | All component gates pass, All workflow gates pass across 10+ contracts |

**Implementation:**
```python
class QualityGateOrchestrator:
    async def run_gate(self, skill: str, corpus: list) -> GateResult:
        # Create Agent Team — these are teammates (peer DMs), not subagents
        team = await TeamCreate(f"quality-gate-{skill}")
        stress_tester = await spawn_teammate("stress-tester", model="sonnet")
        metrics_collector = await spawn_teammate("metrics-collector", model="haiku")
        gate_keeper = await spawn_teammate("gate-keeper", model="opus")

        results = await stress_tester.run_on_corpus(corpus)
        metrics = await metrics_collector.aggregate(results)
        decision = await gate_keeper.evaluate(metrics)

        return GateResult(
            decision=decision,  # APPROVE or REJECT
            metrics=metrics,
            failures=decision.failures if decision.rejected else []
        )
```

**Priority:** HIGH - Phase 3-4

---

### Gap 4: No Automated Feedback Loop

**Current state:** False positives and negatives are identified manually. Pattern refinement is human-driven.

**What's needed:** Automated false positive/negative -> pattern refinement pipeline.

**Flow:**
```
1. Audit produces findings
2. Compare against ground truth
3. For each false positive: Analyze WHY pattern over-triggered
4. For each false negative: Analyze WHY pattern missed
5. Propose pattern modification (tighter for FP, broader for FN)
6. Test modified pattern on full corpus
7. Accept if improvement, rollback if regression
```

**Priority:** MEDIUM - Phase 3 (iteration loop)

---

### Gap 5: No A2A Protocol for Direct Agent Negotiation

**Current state:** Agents communicate through orchestrator (shuttled messages).

**What's needed:** Agent-to-Agent (A2A) protocol for direct negotiation, like Google's A2A.

**Agent Teams solves this natively:**
- SendMessage(type="message", recipient="defender") enables direct DMs
- No orchestrator bottleneck
- Attacker can challenge defender directly
- Verifier observes both sides

**Priority:** SOLVED BY AGENT TEAMS - Phase 1

---

## Research Patterns to Adopt

### Pattern: Reflect-Refine Loop (from 2026 research)
```
Generator -> Validator -> Feedback -> Refined Generator -> ...
Converge via: quality threshold OR retry limit OR manual approval
```

### Pattern: Tool-MAD Debate (from academic research)
- Heterogeneous tools per agent (not all agents use same tools)
- Iterative evidence retrieval during debate
- Dynamic interaction (not scripted rounds)

### Pattern: Self-Healing Tests (5-stage)
```
Detection -> Analysis -> Adaptation -> Validation -> Learning
```
Automatically adapt tests when system changes (new patterns, updated agents).

### Pattern: GKMAD (Group Knowledge Multi-Agent Debate)
- Agents share knowledge graph context
- Debate grounded in shared evidence
- Aligns perfectly with BSKG-first approach

---

## Implementation Priority Matrix

| Gap | Phase | Impact | Effort | Priority |
|-----|-------|--------|--------|----------|
| A2A Protocol | 1 | HIGH | LOW (Agent Teams native) | DO FIRST |
| Confidence Calibration | 1-2 | HIGH | MEDIUM | DO EARLY |
| Convergence Criteria | 3 | HIGH | LOW | DO WITH ITERATION LOOP |
| Quality Gates | 3-4 | HIGH | MEDIUM | DO BEFORE GA |
| Feedback Loop | 3 | MEDIUM | HIGH | DO WITH SELF-TESTING |

---

## AlphaSwarm.sol's Unique Position

- Architecture aligns perfectly with cutting-edge research (Tool-MAD, GKMAD)
- Multi-agent debate for security is NOVEL (no other tool does this)
- Graph-first + behavioral detection is UNIQUE
- **Opportunity:** Set new standard for AI-powered security auditing by adding these missing production patterns
