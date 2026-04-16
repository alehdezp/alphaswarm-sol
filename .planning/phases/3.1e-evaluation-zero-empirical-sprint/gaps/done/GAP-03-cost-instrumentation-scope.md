# GAP-03: Cost instrumentation scope — what does 3.1f need?

**Created by:** improve-phase
**Source:** P1-IMP-04
**Priority:** MEDIUM
**Status:** active
**depends_on:** []

## Question

What does 3.1f actually need from cost data? The three levels mentioned in CONTEXT.md ("Cost instrumentation at three levels") should be defined by 3.1f's requirements, not invented here. Emitting a schema before knowing the consumer's contract risks a cascade fix later.

Specific sub-questions:
1. What cost metrics does 3.1f's "loop economics" calculation require?
2. What granularity is needed? (per-pattern, per-contract, per-pipeline-run?)
3. Are there existing cost data structures in the codebase that should be reused?

## Context

Plan 01 delivers "Cost instrumentation at three levels" and a cost-summary.json that Plan 05 consumes. If the cost data is incomplete or uses wrong units, 3.1f economics are built on sand. "Cost" in LLM contexts is ambiguous: wall-clock time, token consumption (input vs output), API call count, dollars.

## Research Approach

1. Search the codebase for any existing cost tracking, cost summary, or economics-related code
2. Check if 3.1f CONTEXT.md or any planning docs specify what cost data it expects
3. Look at the CONTEXT.md references to cost instrumentation to understand the intended scope

## Findings

**Confidence: HIGH** — The 3.1f CONTEXT.md and 3.1e CONTEXT.md together define the consumer contract precisely. The "three levels" phrase is already resolved in Plan 01's own specification.

### Sub-question 1: What cost metrics does 3.1f's "loop economics" calculation require?

3.1f does NOT define its own cost requirements. It explicitly defers to 3.1e:

> "Every component uses data from 3.1e experiments. No pre-defined categories, no theoretical schemas, no assumed risk levels. If 3.1e doesn't provide the data, this phase cannot proceed." (3.1f-CONTEXT.md, line 155)

3.1f's plans (01-03) consume cost data only indirectly — the Variant Tester (Plan 02) wraps `BaselineManager.check_batch()` for before/after comparison, and the E2E Proof (Plan 03) documents one full cycle. Neither plan specifies a cost schema. The cost data flows through Plan 05 schemas, which extract from Plan 01 observations.

The **Loop Economics Formula** in 3.1e-CONTEXT.md (line 508-509) is the authoritative definition:

> "Plan 01 computes `cost_per_FP_removed = total_pipeline_cost / FPs_removed` and `LOC_per_FP_removed = LOC_changed / FPs_removed`. Plan 01 is LLM-free: cost is measured in `compute_seconds`. Plans 02, 03/04 cost = token_count + compute_seconds. For 3.1f cost-ceiling decisions, establish a token-to-second exchange rate based on Plan 02 observed data (tokens / compute_seconds on first LLM call) to convert Plan 02+ costs to a single unit for comparison with Plan 01."

**Required metrics (complete list):**
- `compute_seconds` — wall-clock pipeline execution time (all plans)
- `wall_clock_seconds` — total elapsed time including waits (Plan 01)
- `token_count` / `cost_tokens` — LLM token consumption (Plans 02, 03/04 only)
- `cost_per_FP_removed` — derived ratio (Plan 01)
- `LOC_per_FP_removed` — derived ratio (Plan 01)
- Token-to-second exchange rate — derived from Plan 02's first LLM call (for cross-plan comparison)

**Not required:** Dollar costs. The formula operates in `compute_seconds` as the common unit, with a token-to-second exchange rate bridging LLM plans to non-LLM plans. 3.1f sets the cost ceiling threshold — 3.1e only provides the raw data.

### Sub-question 2: What granularity is needed?

**Per-pipeline-run** is the primary granularity. The "three levels" in Plan 01 (line 223 of CONTEXT.md) refers to three execution scopes, not three abstraction layers:

1. `"full_7"` — all 7 corpus contracts
2. `"targeted_3"` — SideEntrance + NaiveReceiver + control only
3. `"lens_only"` — single-lens run on pre-built graphs

These are `scope` values in `cost-summary.json`, not separate cost measurement systems. Each scope produces one `{compute_seconds, wall_clock_seconds, contracts_processed, ...}` record.

Plan 01 also tracks **per-pattern** data implicitly via `fps_removed` and `LOC_changed`, yielding per-pattern ratios. But the JSON schema is per-pipeline-run with two records (before/after).

Plan 02 tracks **per-scoring-call** via `llm-scores.jsonl` with `cost_tokens` per row.

Plan 03/04 tracks **per-failure-category** via `fix_cost_classification` (YAML-fixable | builder-fixable | architectural | graph-property-error) — this is effort classification, not compute cost.

### Sub-question 3: Are there existing cost data structures that should be reused?

**Yes, but they serve a different purpose.** The codebase has two cost tracking systems:

1. **`src/alphaswarm_sol/metrics/cost_ledger.py`** — Pool-scoped cost ledger tracking per-pool USD spend, token consumption (input/output), agent-type breakdown, bead attribution. Key types: `CostLedger`, `CostEntry`, `PoolCostSummary`, `PoolBudget`. Tracks: `input_tokens`, `output_tokens`, `cost_usd`, `model`, `agent_type`, `bead_id`.

2. **`src/alphaswarm_sol/agents/cost.py`** — Agent-level cost tracker with budget enforcement. Key types: `CostTracker`, `CostReport`, `BudgetExceededError`.

**These should NOT be reused for 3.1e cost instrumentation.** Reasons:
- They are product-runtime cost trackers (for the audit pipeline running against user contracts), not experiment-measurement infrastructure.
- They track USD, agent types, and bead IDs — none of which apply to 3.1e experiments.
- 3.1e's cost-summary.json is a static 2-record JSON file written once per experiment, not a running ledger.
- Plan 01 is LLM-free, so the token-based cost structures do not apply.

However, **3.1f's Variant Tester** (which runs the evaluation pipeline on prompt variants) WILL use the product infrastructure indirectly when it invokes `BaselineManager.check_batch()`. At that point, the `CostLedger` could track LLM costs of evaluation runs. This is a 3.1f design decision, not a 3.1e concern.

## Recommendation

**Status: RESOLVED.** The "three levels" ambiguity is a documentation clarity issue, not a missing specification. The data contract is fully defined.

### Prescriptive actions for 3.1e:

1. **No schema invention needed.** The `cost-summary.json` schema is already fully specified in Plan 01 (3.1e-01-PLAN.md, Task 3). Follow it exactly:
   ```json
   [
     {"level": "before", "scope": "full_7", "compute_seconds": <measured>, "wall_clock_seconds": <measured>, ...},
     {"level": "after", "scope": "full_7", "compute_seconds": <measured>, ..., "cost_per_FP_removed": <computed>, "LOC_per_FP_removed": <computed>}
   ]
   ```

2. **Plan 02 cost tracking** is also specified: `cost_tokens` field per row in `llm-scores.jsonl`. No additional schema needed.

3. **Do NOT import or use `CostLedger` or `CostTracker`** for experiment cost measurement. Use simple `time.perf_counter()` for `compute_seconds` and extract `cost_tokens` from LLM API responses for Plans 02/03/04.

4. **Token-to-second exchange rate**: Compute from Plan 02's first LLM scoring call as `cost_tokens / compute_seconds`. Record this in a top-level field in Plan 02's summary artifact (not in cost-summary.json, which is Plan 01-only).

5. **Clarify "three levels" in CONTEXT.md** if editing is permitted: replace "Cost instrumentation at three levels" with "Cost instrumentation at three pipeline scopes (full_7, targeted_3, lens_only)" to prevent future misreading. This is cosmetic — the Plan 01 specification is unambiguous.

### What 3.1f needs to decide (not 3.1e's problem):

- **Cost ceiling threshold**: What `cost_per_FP_removed` value is acceptable? 3.1e provides the data; 3.1f sets the threshold.
- **Whether to wrap `CostLedger` for variant testing**: If the variant tester invokes LLM evaluation, it could use `CostLedger` to track per-variant costs. This is a 3.1f Plan 02 design decision.
- **Unified cost reporting format**: If 3.1f wants to compare Plan 01 (compute_seconds) with Plan 02+ (tokens + compute_seconds) in a single view, it needs the exchange rate from Plan 02. This is already specified in the Loop Economics Formula.
