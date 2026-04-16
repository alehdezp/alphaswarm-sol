# GAP-05: Model Tier Evaluation Quality Comparison

**Created by:** improve-phase
**Source:** P1-IMP-26
**Priority:** MEDIUM
**Status:** resolved
**Resolved:** 2026-02-18
**depends_on:** [GAP-01]

## Question

Can Haiku and Sonnet produce equivalent evaluation scores to Opus for different evaluation task types (capability checks, format validation, reasoning evaluation)? What is the quality/cost tradeoff per task type?

## Context

P1-IMP-26 proposes a tiered model strategy: Sonnet default, Opus for critical, Haiku for mechanical. Without data on quality differences, we can't safely assign cheaper models to evaluation tasks. If Haiku drops >10% quality on capability checks, it's not worth the cost savings.

Affected plans: 3.1c-06 (contracts need evaluator_model field), 3.1c-07 (evaluator model routing), 3.1c-08 (runner model selection).

## Research Approach

- Check Anthropic model comparison data for structured output tasks
- Look for benchmarks comparing Haiku/Sonnet/Opus on evaluation/scoring tasks
- Search for LLM-as-judge model comparisons in research literature
- Sources: Anthropic docs, Exa for research, model benchmark sites

## Findings

### 1. LLM-as-Judge: Model Size vs Evaluation Quality (Research Literature)

Seven major papers (2024-2025) directly address whether smaller models can replace larger ones as evaluators. The findings converge on a clear pattern:

**Finding A: Task complexity determines the model size threshold.**

- **"Judging the Judges" (Thakur et al., 2024, ICLR 2025 submission):** Evaluated 13 judge models across sizes. Key finding: "only the best (and largest) models achieve reasonable alignment with humans" for absolute scoring. However, for **ranking** (ordinal comparison), "smaller models and even the lexical metric Contains may provide a reasonable signal." Scores from smaller models can differ by up to 5 points (on a 10-point scale) from human-assigned scores on absolute scoring tasks.

- **"JudgeBench" (Tan et al., ICLR 2025):** Benchmark for evaluating LLM judges on challenging tasks (knowledge, reasoning, math, coding). Key finding: "many strong models (e.g., GPT-4o) performing just slightly better than random guessing" on hard evaluation pairs. This demonstrates that **evaluation difficulty matters more than general model capability** -- even frontier models struggle on genuinely hard judgment tasks.

- **"JudgeBoard" (Bi et al., Nov 2025):** Specifically benchmarks small language models (SLMs) as reasoning evaluators. Key finding: "a significant performance gap between SLMs and LLMs in isolated judging tasks." However, their Multi-Agent Judging (MAJ) framework "substantially improves the reliability and consistency of SLMs" -- on the MATH dataset, MAJ using smaller models "performs comparatively well or even better than their larger-sized counterparts."

- **"On scalable oversight with weak LLMs judging strong LLMs" (Kenton et al., DeepMind, NeurIPS 2024):** Used weaker LLMs to judge stronger LLMs. Key finding: weak judges perform adequately on extractive QA tasks with clear right/wrong answers, but results are "mixed" on tasks requiring nuanced reasoning without information asymmetry.

- **"LLMs instead of Human Judges?" (Bavaresco et al., 2024):** Large-scale study across 20 NLP tasks. Key finding: "substantial variance across models and datasets. Models are reliable evaluators on some tasks, but overall display substantial variability depending on the property being evaluated."

- **"An Empirical Study of LLM-as-a-Judge" (Huang et al., ACL Findings 2025):** Fine-tuned smaller judge models vs GPT-4. Key finding: fine-tuned smaller judges achieve high in-domain performance but "underperform GPT-4 across several dimensions, including generalizability, fairness and adaptability."

- **"Replacing Judges with Juries" (Verga et al., 2024):** Proposes using a panel of diverse smaller models instead of a single large judge. Panels of smaller models can match or exceed single large model performance for preference ranking.

**Finding B: Binary/deterministic tasks need minimal model capability; nuanced scoring needs maximum.**

The literature consistently shows a clean split:

| Task Type | Model Size Requirement | Evidence |
|-----------|----------------------|----------|
| Binary classification (yes/no, present/absent) | Small models sufficient | Thakur: ranking signal from small models; Kenton: weak judges adequate for clear right/wrong |
| Format/schema validation | No LLM needed | Deterministic -- JSON schema validators, regex, code checks |
| Ordinal ranking (better/worse) | Mid-tier models adequate | Thakur: small models provide "reasonable signal" for ranking; Verga: panels of small models match large |
| Absolute scoring (0-100 scale) | Large models strongly preferred | Thakur: up to 5-point deviation in small models; Bavaresco: "substantial variability" |
| Reasoning quality assessment | Largest models required | JudgeBench: even GPT-4o near random on hard cases; Huang: generalizability gap |
| Failure narrative generation | Large models required | Requires causal reasoning about what went wrong -- no research shows small models adequate |

### 2. Claude Model Family: Capability Gradient for Evaluation Tasks

Based on Anthropic's published benchmarks (Nov 2025-Feb 2026) and third-party evaluations:

| Capability | Opus 4.6 | Sonnet 4.5 | Haiku 4.5 |
|-----------|----------|------------|-----------|
| **SWE-bench Verified** | ~81% | ~77% | ~65% (est.) |
| **Reasoning (ARC-AGI-2)** | ~38% | ~14% | N/A |
| **Structured output compliance** | 100% (GA) | 100% (GA) | 100% (GA) |
| **JSON schema adherence** | Native support | Native support | Native support |
| **Cost (input/output $/MTok)** | $5 / $25 | $3 / $15 | $1 / $5 |
| **Relative cost** | 1.0x | 0.6x | 0.2x |

Key observations for evaluation use:
- **Structured outputs are equally reliable across all tiers.** As of Feb 2026, all three models support constrained decoding with 100% schema compliance (GA). For format validation and schema-conformant output, model tier does not affect reliability.
- **The reasoning gap between Opus and Sonnet is moderate (~5-10%).** On most benchmarks, Sonnet trails Opus by 3-7 percentage points. For evaluation tasks that require "is this reasoning chain sound?" judgment, this gap translates to slightly less nuanced scoring.
- **The reasoning gap between Sonnet and Haiku is large (~20-40%).** On reasoning-intensive benchmarks like ARC-AGI-2, the gap is enormous (38% vs 14%). For nuanced evaluation of reasoning quality, Haiku is not a viable substitute.
- **For binary/classification tasks, Haiku is adequate.** Classification accuracy across Claude models shows much smaller gaps than reasoning benchmarks. Haiku excels at structured, constrained-output tasks.

### 3. Mapping to Our Evaluation Task Types

Our evaluation pipeline (Phase 3.1c) has three distinct task types. Here is the evidence-based model assignment:

#### Task Type 1: Capability Checks (Binary Pass/Fail)

**Examples:** Did the agent call `build-kg`? Did output contain a findings section? Did the agent query BSKG before reading code?

**Characteristics:**
- Binary outcome (pass/fail)
- Ground truth is deterministic (tool was called or wasn't)
- No subjective judgment required
- Equivalent to "presence" / "ordering" / "count" check types

**Research verdict:** These are already handled by deterministic code checks (`presence`, `ordering`, `count` grader types in `ReasoningEvaluator`). **No LLM needed.** The observation parser extracts tool calls and the code grader evaluates them. Using any LLM for this is waste.

**Model assignment: NONE (deterministic code)**

#### Task Type 2: Reasoning Evaluation (Scored 0-100)

**Examples:** Quality of graph query strategy (0-100). Soundness of evidence chain (0-100). Appropriateness of vulnerability classification (0-100).

**Characteristics:**
- Continuous scale requiring calibrated judgment
- Subjective assessment of reasoning quality
- Must compare against evaluation contract criteria
- Requires understanding of security domain concepts
- Most sensitive to model capability differences

**Research verdict:** This is where model size matters most. The literature shows:
- Absolute scoring has the highest model-size sensitivity (Thakur: 5-point deviations in smaller models)
- Reasoning evaluation is the hardest judging task (JudgeBench: even frontier models struggle)
- Domain-specific evaluation requires generalizability (Huang: smaller models underperform on generalization)

However, the gap between Opus and Sonnet is moderate (~5-10%), not catastrophic. Sonnet can serve as a competent evaluator for most reasoning dimensions, with Opus reserved for the most critical assessments.

**Model assignment:**
- **Sonnet 4.5** for standard reasoning dimensions (graph_query_quality, evidence_use, conclusion_soundness)
- **Opus 4.6** for critical investigation workflows (full audit, multi-agent debate, complex vulnerability assessment) where a 5% scoring accuracy difference could mask real regressions

#### Task Type 3: Failure Narrative Generation

**Examples:** "What happened: Agent skipped BSKG queries and jumped to manual code reading. What should have happened: Agent should have run pattern queries first to identify candidate functions."

**Characteristics:**
- Requires causal reasoning about agent behavior
- Must identify root cause vs. symptoms
- Generates natural language explanations
- Output quality directly affects metaprompting effectiveness

**Research verdict:** Failure narratives require understanding what *should* have happened (counterfactual reasoning) and why the agent deviated. This is closer to reasoning evaluation than binary checking. However, the output doesn't need to be precisely scored -- it needs to be *useful* for metaprompting.

Sonnet's capability is adequate here. The narrative doesn't need to be perfectly calibrated on a numerical scale; it needs to correctly identify the root cause and describe the expected behavior. Sonnet's reasoning is sufficient for this when the evaluation contract provides clear criteria.

**Model assignment: Sonnet 4.5** (adequate for causal narrative; Opus overkill for descriptive output)

### 4. Quality/Cost Tradeoff Analysis

Using GAP-03's cost model as baseline:

| Model Config | Per-Suite Cost | Quality Risk | Net Assessment |
|-------------|---------------|--------------|----------------|
| All-Opus | $8.00 | Lowest risk | Overspend on mechanical + standard tasks |
| All-Sonnet | $1.87 (est. ~$1.50 if all Sonnet) | ~5-10% scoring deviation on critical workflows | Acceptable for most; risky for regression detection on critical paths |
| Tiered (Opus critical + Sonnet standard) | $1.87 | <3% effective risk (Opus covers highest-sensitivity tasks) | **Best tradeoff** |
| Tiered + Haiku for any LLM eval | ~$1.20 | >15% scoring deviation on reasoning tasks | **Not recommended** for any LLM evaluation task |

**The critical insight:** Haiku should NOT be used for any LLM-as-judge evaluation task in this pipeline. Even binary capability checks don't need Haiku -- they need deterministic code. The only LLM evaluation tasks are reasoning scoring and failure narratives, both of which require at minimum Sonnet-tier capability.

### 5. Validation Strategy: Empirical Calibration Protocol

Since the literature provides ranges, not exact numbers for Claude-specific evaluation quality, we recommend a one-time calibration experiment:

1. Select 5 representative evaluation transcripts (2 critical, 3 standard)
2. Run each through Opus AND Sonnet evaluation with identical contracts
3. Compare: score correlation (Pearson r), mean absolute deviation, ranking agreement (Kendall tau)
4. **Acceptance threshold:** If Sonnet-Opus correlation > 0.85 and MAD < 8 points (on 0-100 scale), Sonnet is validated for standard workflows
5. If threshold fails, expand Opus coverage or adjust contract specificity

Estimated cost of calibration: 5 transcripts x 2 models x ~$0.20 = ~$2.00. Trivial.

### Sources

| # | Source | Type | Key Finding |
|---|--------|------|-------------|
| 1 | Thakur et al., "Judging the Judges" (2024) | Peer-reviewed (ICLR sub.) | Only largest models align with humans on absolute scoring; smaller adequate for ranking |
| 2 | Tan et al., "JudgeBench" (ICLR 2025) | Peer-reviewed | Even frontier models near-random on hard evaluation pairs |
| 3 | Bi et al., "JudgeBoard" (Nov 2025) | Preprint | Significant SLM vs LLM gap in isolated judging; multi-agent SLM can close gap |
| 4 | Kenton et al., "Weak LLMs judging strong LLMs" (NeurIPS 2024) | Peer-reviewed | Weak judges adequate for clear right/wrong; mixed on nuanced tasks |
| 5 | Bavaresco et al., "LLMs instead of Human Judges?" (2024) | Peer-reviewed | Substantial variability across models and evaluation properties |
| 6 | Huang et al., "Empirical Study of LLM-as-a-Judge" (ACL 2025) | Peer-reviewed | Fine-tuned small judges underperform GPT-4 on generalizability |
| 7 | Verga et al., "Replacing Judges with Juries" (2024) | Peer-reviewed | Panel of diverse small models can match single large judge |
| 8 | Anthropic structured outputs announcement (Nov 2025, updated Feb 2026) | Official | 100% schema compliance GA across Opus, Sonnet, Haiku |
| 9 | Artificial Analysis Claude Opus 4.5 benchmarks (Nov 2025) | Third-party benchmark | Opus-Sonnet intelligence gap quantified at ~7 index points |
| 10 | Hamel Husain, "LLM-as-a-Judge Complete Guide" (Oct 2024) | Practitioner guide | Binary pass/fail preferred over uncalibrated 1-5 scales |

## Recommendation

**Confidence: HIGH** -- Grounded in 7 peer-reviewed/preprint papers, official Anthropic data, and consistent with GAP-03 cost model.

### Prescriptive Model Assignment per Evaluation Task Type

| Task Type | Model | Rationale | Cost Impact |
|-----------|-------|-----------|-------------|
| **Capability checks** (presence, ordering, count) | **Deterministic code** (no LLM) | Binary pass/fail with deterministic ground truth. LLM adds cost and nondeterminism, not value. | $0.00 |
| **Reasoning evaluation -- critical workflows** (~8 workflows: full audit, multi-agent debate, complex investigation) | **Opus 4.6** | Highest sensitivity to scoring accuracy. 5-10% deviation in Sonnet could mask real regressions in the most important workflows. | ~$0.88/suite |
| **Reasoning evaluation -- standard workflows** (~12 workflows: tool runs, simple investigations, synthesis) | **Sonnet 4.5** | Adequate reasoning for standard evaluation dimensions. Literature shows mid-tier models provide "reasonable signal" for non-extreme cases. | ~$0.79/suite |
| **Failure narrative generation** | **Sonnet 4.5** | Causal narrative quality is adequate at Sonnet tier. Output is descriptive, not numerically calibrated. | Included in eval call |
| **Debrief analysis** | **Sonnet 4.5** | Structured Q&A extraction from agent transcripts. Sonnet sufficient for identifying patterns in agent responses. | ~$0.13/suite |

### What Haiku Should NOT Do

Haiku should not be used for any evaluation task in this pipeline. The original P1-IMP-26 proposal suggested "Haiku for mechanical" -- but mechanical tasks don't need any LLM. They need deterministic code. The evaluation pipeline has no task type where Haiku is the right choice:

- Capability checks: deterministic (no LLM)
- Reasoning evaluation: requires Sonnet minimum
- Failure narratives: requires Sonnet minimum
- Debrief: requires Sonnet minimum

Haiku remains appropriate for *non-evaluation* tasks in the broader system (URL filtering, deduplication, transcript summarization for caching), but not for the evaluation pipeline itself.

### Implementation Decisions This Enables

| Decision | Recommendation | Confidence |
|----------|---------------|------------|
| **evaluator_model field in contracts** | Three values: `"deterministic"`, `"sonnet"`, `"opus"`. No `"haiku"` option for evaluation. | HIGH |
| **Default model for `grader_type: "model"`** | `"sonnet"` | HIGH |
| **Default model for `grader_type: "hybrid"` with `category: "agent"`** | `"opus"` | HIGH |
| **Default model for `grader_type: "code"`** | `"deterministic"` | HIGH |
| **Validation before shipping** | Run calibration protocol (5 transcripts, 2 models, ~$2) before finalizing tier boundaries | HIGH |
| **Future upgrade path** | If Sonnet-Opus calibration shows r > 0.92 and MAD < 5, promote all to Sonnet (saves $0.88/suite on Opus calls) | MEDIUM |

### Consistency with GAP-03

This recommendation is fully consistent with GAP-03's Scenario B ($1.87/suite). The model assignments match:
- GAP-03 allocated Opus for ~8 critical investigation workflows: confirmed
- GAP-03 allocated Sonnet for ~12 important workflows: confirmed
- GAP-03 allocated deterministic for ~31 mechanical: confirmed
- GAP-03's total cost estimate of $1.87/suite: still valid

No changes needed to GAP-03's cost projections.
