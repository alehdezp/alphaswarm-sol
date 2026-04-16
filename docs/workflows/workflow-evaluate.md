# Workflow: Evaluation Pipeline

**Purpose:** Define how AlphaSwarm evaluates workflow quality through the 3.1c/3.1d evaluation pipeline.

> **v6.0 Status:** Evaluation pipeline is functional for simulated runs. Real transcript calibration in progress (Phase 3.1d-04). ~35% of scoring dimensions use heuristic fallbacks instead of model-based assessment.

## What It Does

The evaluation pipeline measures *reasoning quality*, not just output correctness. It answers three questions:

1. **"Is it working?"** — Run scenarios, compare to expected behavior, report pass/fail with evidence
2. **"What broke and why?"** — Failure narratives trace root causes, not symptoms
3. **"How do I fix it?"** — Structured improvement suggestions linked to specific scenario evidence

## Pipeline Stages

```
Scenario YAML → Collect Output → Parse Observations → Score (GVS + Dimensions) → Evaluate → Result
     ↓                                                                                        ↓
  Expected                                                                              ScoreCard
  Behavior                                                                            (pass/fail +
  Contract                                                                         failure narratives)
```

1. **Load scenario** — Read scenario YAML, find matching evaluation contract
2. **Collect output** — Bridge tool_sequence, bskg_queries, response_text into EvaluationInput
3. **Parse observations** — Read `.vrs/observations/*.jsonl` into ObservationSummary
4. **Run plugins** — GraphValueScorer (GVS) and any registered plugins
5. **Evaluate dimensions** — Score reasoning dimensions from contract
6. **Evaluate capabilities** — Check presence, ordering, count of expected behaviors
7. **Compute overall** — Weighted aggregate of all dimension and plugin scores
8. **Generate failure narrative** — Paired "what happened" / "what should have happened" for failures

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| EvaluationRunner | `tests/workflow_harness/lib/evaluation_runner.py` | Orchestrates full pipeline |
| ReasoningEvaluator | `tests/workflow_harness/graders/reasoning_evaluator.py` | Scores reasoning dimensions |
| GraphValueScorer | `tests/workflow_harness/graders/graph_value_scorer.py` | Scores graph utilization |
| ObservationParser | `tests/workflow_harness/lib/observation_parser.py` | Parses hook JSONL data |
| BaselineManager | `tests/workflow_harness/lib/regression_baseline.py` | Tracks scores, detects regressions |
| DebriefProtocol | `tests/workflow_harness/lib/debrief_protocol.py` | 4-layer agent self-assessment |

## Evaluation Contracts

Each workflow has a YAML evaluation contract defining:
- **capability_checks** — What the workflow must do (presence, ordering, count checks)
- **reasoning_dimensions** — What reasoning aspects to evaluate (evidence_quality, graph_utilization, etc.)
- **evaluation_config** — Whether to run GVS, reasoning eval, debrief
- **rule_refs** — Which testing rules apply

Contracts live in `src/alphaswarm_sol/testing/evaluation/contracts/`.

## Scoring

- **Scale:** 0–100 integer per dimension and overall
- **Pass threshold:** 60 (configurable per scenario)
- **GVS weights:** query_coverage (0.35), citation_rate (0.35), graph_first (0.30)
- **Regression threshold:** 5-point drop flags regression

## Commands

```bash
# Run single scenario
uv run pytest tests/scenarios/ -k "UC-AUDIT-001"

# Run all audit scenarios
uv run pytest tests/scenarios/ -k "audit"

# Run full regression suite
uv run pytest tests/scenarios/
```

## Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-test-scenario` | Run single scenario, produce feedback |
| `/vrs-test-regression` | Run all scenarios, compare to baseline |
| `/vrs-test-affected` | Map changed files → affected scenarios |
| `/vrs-test-suggest` | Analyze failures, propose improvements |

## What Actually Works (Honest)

- Evaluation runner executes full pipeline in simulated mode
- GVS scores graph utilization from tool_sequence and bskg_queries
- Heuristic dimension scoring for evidence, reasoning, coherence, hypothesis, graph
- Failure narratives generated for scores below threshold
- BaselineManager tracks and compares scores across sessions
- Observation parser reads JSONL from hooks
- 4-layer debrief cascade (send_message → hook_gate → transcript → skip)

## What Doesn't Work Yet

- Model-based reasoning evaluation (LLM scoring) — uses keyword heuristics instead
- Real transcript calibration — all calibration done on synthetic data
- Debrief layers 1 and 2 (send_message, hook_gate) — only transcript analysis and skip work
- Score spread on real data — needs calibration (Phase 3.1d-04)

## Testing

- Scenario-based: `.planning/testing/scenarios/use-cases/`
- Unit tests: `tests/workflow_harness/` (274+ tests)
