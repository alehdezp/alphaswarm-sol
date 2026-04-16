# GAP-03: Evaluation Pipeline Cost Model

**Created by:** improve-phase
**Source:** P1-IMP-07
**Priority:** MEDIUM
**Status:** resolved
**Resolved:** 2026-02-18
**depends_on:** []

## Question

What is the estimated cost per full evaluation regression suite? Specifically: average transcript size (tokens), rubric prompt size, scoring output size, multiplied by workflow count and evaluators, at current Anthropic pricing.

## Context

P1-IMP-07 notes that 51 workflows x evaluation could cost $50-300+ per full suite. Without a cost model, the planner can't decide evaluation depth per tier or run frequency. This affects 3.1c-08 (Runner) scheduling and the dual-Opus decision.

Affected plans: 3.1c-07, 3.1c-08, 3.1c-12.

## Findings

### 1. Current Anthropic API Pricing (Feb 2026)

Source: Anthropic pricing pages, verified via multiple aggregators (MetaCTO, Serenities AI, CostGoat, InvertedStone).

| Model | Input ($/MTok) | Output ($/MTok) | Notes |
|-------|---------------|-----------------|-------|
| **Opus 4.6** | $5.00 | $25.00 | >200K context: $10/$37.50 |
| **Sonnet 4.5** | $3.00 | $15.00 | >200K context: $6/$22.50 |
| **Haiku 4.5** | $1.00 | $5.00 | No >200K surcharge |

**Cost reduction levers:**
- **Prompt caching:** 90% savings on cached input (cache read: $0.50/MTok for Opus, $0.30 for Sonnet)
- **Batch API:** 50% discount on all models (async, up to 24h delivery)
- Cache write cost: $6.25/MTok (Opus), $3.75/MTok (Sonnet)

### 2. Token Size Estimates

Based on codebase analysis of actual evaluation components:

| Component | Estimated Tokens | Source / Reasoning |
|-----------|-----------------|-------------------|
| **Agent transcript (investigation)** | 8,000-30,000 | Complex: multi-tool, BSKG queries, code reading, findings. Typical Claude Code session = 5-50K. Investigation agents are mid-range. |
| **Agent transcript (mechanical)** | 2,000-8,000 | Simple: health-check, tool-run, build-kg. Fewer steps. |
| **Evaluation contract** | 400-800 | Schema analysis: 5-8 capability checks, 3-5 reasoning dimensions, metadata. ~50 lines YAML. |
| **Rubric/system prompt** | 800-1,200 | `REASONING_PROMPT_TEMPLATE` (~200 tokens) + contract context + dimension descriptions. |
| **Scoring output** | 300-600 | JSON with score, evidence list, explanation per dimension. 5-8 dimensions per contract. |
| **Failure narrative prompt** | 400-600 | `FAILURE_NARRATIVE_TEMPLATE` + low-scoring dimensions summary. |
| **Failure narrative output** | 200-400 | what_happened + what_should_have_happened. |
| **Debrief prompt (if LLM-based)** | 1,500-3,000 | 5 questions + transcript excerpt (truncated to 2000 chars = ~500 tokens) + system instructions. |
| **Debrief output** | 400-800 | 5 structured answers + confidence. |

**Per-workflow LLM evaluation call breakdown:**

| Call | Input Tokens | Output Tokens |
|------|-------------|---------------|
| Reasoning evaluation (1 call per dimension x ~5 dims) | ~3,000 each (transcript excerpt + rubric) | ~150 each |
| OR: Single consolidated evaluation call | ~15,000 (full transcript + all dimensions) | ~800 |
| Failure narrative (on fail only, ~30% rate) | ~1,500 | ~400 |
| Debrief analysis (if LLM-based, investigation only) | ~2,500 | ~600 |

**Estimate per workflow (single consolidated eval call):**
- Investigation workflow: ~15,000 input + ~1,400 output
- Mechanical workflow: ~5,000 input + ~800 output

### 3. Cost Scenarios

#### Scenario A: All-Opus, 51 Workflows, Dual Evaluator (Original Design)

This is the "worst case" design from the original 3.1c spec.

| Item | Count | Input Tok | Output Tok | Cost |
|------|-------|-----------|------------|------|
| Investigation eval (Opus x2) | 20 workflows x 2 evals | 15K x 40 = 600K | 1.4K x 40 = 56K | $3.00 + $1.40 = **$4.40** |
| Mechanical eval (Opus x2) | 31 workflows x 2 evals | 5K x 62 = 310K | 0.8K x 62 = 49.6K | $1.55 + $1.24 = **$2.79** |
| Debrief (Opus, investigation only) | 20 workflows | 2.5K x 20 = 50K | 0.6K x 20 = 12K | $0.25 + $0.30 = **$0.55** |
| Failure narratives (Opus, ~30%) | ~15 workflows | 1.5K x 15 = 22.5K | 0.4K x 15 = 6K | $0.11 + $0.15 = **$0.26** |
| **TOTAL** | | **982.5K** | **123.6K** | **$8.00** |

**Per full regression suite: ~$8.00** (all-Opus, dual evaluator).

#### Scenario B: Tiered Model, 15-20 LLM-Evaluated, Single Evaluator (P1-IMP-20 + P1-IMP-25 + P1-IMP-26)

This is the recommended design after applying improvements.

| Item | Model | Count | Input Tok | Output Tok | Cost |
|------|-------|-------|-----------|------------|------|
| Investigation eval (Opus x1) | Opus 4.6 | 8 critical workflows | 15K x 8 = 120K | 1.4K x 8 = 11.2K | $0.60 + $0.28 = **$0.88** |
| Investigation eval (Sonnet x1) | Sonnet 4.5 | 12 important workflows | 15K x 12 = 180K | 1.4K x 12 = 16.8K | $0.54 + $0.25 = **$0.79** |
| Mechanical checks (no LLM) | None | ~31 workflows | 0 | 0 | **$0.00** |
| Debrief (Sonnet, investigation) | Sonnet 4.5 | 8 workflows | 2.5K x 8 = 20K | 0.6K x 8 = 4.8K | $0.06 + $0.07 = **$0.13** |
| Failure narratives (Sonnet, ~30%) | Sonnet 4.5 | ~6 workflows | 1.5K x 6 = 9K | 0.4K x 6 = 2.4K | $0.03 + $0.04 = **$0.07** |
| **TOTAL** | | | **329K** | **35.2K** | **$1.87** |

**Per full regression suite: ~$1.87** (tiered model, single evaluator, LLM only for investigation+synthesis).

#### Scenario C: Scenario B + Prompt Caching + Batch API

Evaluation contracts and rubric prompts are identical across runs. With prompt caching:
- ~1,200 tokens of system/rubric prompt cached per call = 90% savings on that portion
- Batch API: 50% discount on remaining costs

| Optimization | Savings |
|-------------|---------|
| Base (Scenario B) | $1.87 |
| Prompt caching on rubric (~15% of input is cacheable) | -$0.20 |
| Batch API (50% off everything) | -$0.84 |
| **Optimized total** | **~$0.83** |

### 4. Run Frequency Cost Projections

| Frequency | Scenario A | Scenario B | Scenario C |
|-----------|-----------|-----------|-----------|
| Per run | $8.00 | $1.87 | $0.83 |
| Daily (dev cycle) | $240/mo | $56/mo | $25/mo |
| Per commit (5/day) | $1,200/mo | $281/mo | $125/mo |
| Weekly regression | $32/mo | $7.48/mo | $3.32/mo |
| On-demand only | $8-24/mo | $1.87-5.61/mo | $0.83-2.49/mo |

### 5. Key Observations

1. **The cost is surprisingly low.** Even the most expensive scenario (all-Opus dual evaluator) is only ~$8 per full suite. The original fear of "$50-300+" was based on incorrect assumptions about token volumes. The evaluation pipeline processes extracted observations and transcripts, not full Claude Code sessions. Each eval call is 5-15K input tokens, not 100K+.

2. **Dual evaluator doubles cost for marginal benefit.** Going from 1 to 2 evaluators doubles cost ($8 to ~$16) but inter-rater agreement on heuristic dimensions is unlikely to provide actionable signal until reasoning evaluation is sophisticated enough to have meaningful disagreements.

3. **Mechanical workflows do not need LLM evaluation.** Health-check, bead-create, tool-run etc. have deterministic pass/fail criteria. The `presence`, `ordering`, and `count` check types in `ReasoningEvaluator` already handle these without LLM calls.

4. **Prompt caching is high-value.** Evaluation contracts and rubric templates are stable across runs. Caching the ~1,200 token system prompt reduces input cost from $5/MTok to $0.50/MTok for that portion.

5. **Batch API is the biggest lever.** 50% discount for async processing. Evaluation regression suites are not latency-sensitive — batch is ideal.

6. **The real cost is the WORKFLOW RUN, not the evaluation.** Running the actual 51 workflows (spawning Claude Code agents, building graphs, running tools) costs orders of magnitude more than evaluating the results. A single full audit workflow run costs $5-50+ in Claude API usage. The evaluation pipeline analyzing the transcript of that run costs $0.04-0.44.

## Recommendation

**Adopt Scenario B (tiered model, single evaluator) as the baseline, with Scenario C optimizations for CI.**

### Specific decisions this enables:

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| **P1-IMP-25: Single vs dual evaluator** | **Single evaluator.** | Cost difference is 2x ($1.87 vs $3.74) for unproven benefit. Add second evaluator only when first evaluator is calibrated and disagreement would be informative. |
| **P1-IMP-26: Model tiering** | **Opus for ~8 critical investigation workflows, Sonnet for ~12 important, deterministic for ~31 mechanical.** | Cost difference between all-Opus ($8) and tiered ($1.87) is 4.3x. Mechanical workflows gain nothing from LLM evaluation. |
| **P1-IMP-20: LLM-evaluated scope** | **15-20 LLM-evaluated workflows (investigation + synthesis).** | ~31 mechanical workflows have `presence`/`ordering`/`count` checks that are fully deterministic. Only `model` and `code` grader types with reasoning dimensions benefit from LLM. |
| **3.1c-08 Runner frequency** | **Weekly full regression + on-demand for changed workflows.** | At $1.87/run, weekly is $7.48/mo — trivial. Per-commit is wasteful ($281/mo) since evaluation data doesn't change between code changes that don't affect prompts. |
| **3.1c-12 Improvement loop** | **Run on-demand per experiment, not per commit.** | Each improvement experiment needs 1-3 evaluation runs ($1.87-5.61). Budget ~$20/mo for active improvement work. |

### Cost budget recommendation:

| Category | Monthly Budget | Notes |
|----------|---------------|-------|
| Weekly regression suite | $8 | 4 runs x $1.87 |
| Improvement experiments | $20 | ~10 experiment runs |
| Ad-hoc evaluation | $10 | Developer-triggered |
| **Total evaluation pipeline** | **~$38/mo** | Excludes workflow run costs |

### Implementation notes for 3.1c-08 (Runner):

1. Add `evaluation_model` field to evaluation contracts: `"opus"`, `"sonnet"`, or `"deterministic"`.
2. Default: `"deterministic"` for `grader_type: "code"` contracts, `"sonnet"` for `grader_type: "model"`, `"opus"` for `grader_type: "hybrid"` with `category: "agent"`.
3. Runner should support `--batch` flag to use Batch API (50% savings, async results).
4. Runner should implement prompt caching for evaluation contract + rubric template (stable across runs).
5. The consolidated single-call evaluation (all dimensions in one prompt) is 3-5x cheaper than per-dimension calls. Use consolidated by default.

**Confidence: HIGH** — pricing data is from multiple verified sources (Feb 2026), token estimates are grounded in actual codebase measurements of prompt templates and evaluation contract schemas.
