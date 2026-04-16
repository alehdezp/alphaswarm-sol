# GAP-04: Reasoning Dimension Extraction Viability

**Created by:** improve-phase
**Source:** P1-IMP-15
**Priority:** HIGH
**Status:** RESOLVED
**depends_on:** [GAP-01]
**Researched:** 2026-02-18
**Confidence:** HIGH

## Question

Can an LLM (via `claude --print`) reliably extract and score 3 reasoning dimensions (graph_query_quality, evidence_utilization, conclusion_grounding) from a real agent transcript? What prompt structure produces usable scores?

## Context

P1-IMP-15 identifies that the 7-move reasoning extraction has no prototype. The existing heuristic evaluator uses keyword matching (P2-IMP-03 shows this is wrong). If LLM-based dimension scoring doesn't work reliably, 3.1c-07's core differentiator fails. Depends on GAP-01 confirming the `claude --print` mechanism works.

Affected plans: 3.1c-07 (Evaluator) fundamentally.

## Findings

### 1. LLM-as-Judge Is Proven for Multi-Dimension Rubric Scoring

**Confidence: HIGH** (extensive literature, multiple production frameworks)

The LLM-as-judge paradigm is well-established for structured multi-dimensional evaluation. Key evidence:

- **G-Eval** (NeurIPS 2023, widely adopted): Uses chain-of-thought prompting + LLM scoring on custom criteria. DeepEval's implementation scores 0-1 per dimension with CoT-generated evaluation steps. Achieves highest correlation with human judgment among automated metrics for subjective criteria.
- **LLM-Rubric** (Hashemi et al., ACL 2024, Microsoft): Prompts LLM with per-dimension rubric questions, producing score distributions. With 9 dimensions (naturalness, conciseness, citation quality, etc.), achieves RMS error < 0.5 on a 1-4 scale vs. human judges --- a 2x improvement over uncalibrated baselines.
- **RAGAS**: Framework specifically for evaluating RAG pipelines on 4 dimensions (contextual recall, contextual precision, faithfulness, answer relevancy). Each dimension scored independently by an LLM judge. Directly analogous to our 3-dimension problem.
- **Chain-of-Rubrics (CoR)** (2025): Decomposes evaluation into modular rubric-guided steps, with each rubric item producing a sub-score. Up to 38.9% scoring improvement over non-prompt-engineered baselines.

**Bottom line:** Scoring 3 dimensions from a transcript is a well-solved problem class. The question is not *if* it works, but *how to maximize reliability* for our specific dimensions.

### 2. Critical Design Principles from Research

**Confidence: HIGH** (consensus across 8+ sources, 2024-2026)

#### 2a. Score each dimension SEPARATELY

Every source agrees: never combine multiple qualities into a single scoring prompt. Evaluate one dimension per rubric question. This is the single highest-impact design choice.

- Rhesis AI: "Combining multiple qualities into a single score is tempting but harmful."
- LLM-Rubric: Each of 9 dimensions gets its own prompt + scoring.
- DeepEval: Separate `GEval` metric instance per dimension.

**Implication for us:** 3 separate LLM calls (or 3 structured sections in one call with `--json-schema` enforcing all 3). Given our `--json-schema` guarantees, one call with all 3 dimensions is viable since the schema forces structured separation.

#### 2b. Chain-of-thought BEFORE score, in structured output

CoT reasoning improves scoring accuracy, but ONLY when paired with structured output format. Unstructured CoT + score can actually degrade reliability.

- Rhesis AI: "CoT with structured output formats achieves substantially better human alignment compared to unstructured judge responses."
- G-Eval: CoT generates evaluation steps first, then scores.
- Practical consensus: Require `reasoning` field BEFORE `score` field in JSON schema to force the model to think before scoring.

**Implication:** Our JSON schema must order fields as: `reasoning` -> `evidence` -> `score` for each dimension (though JSON is unordered, the prompt should instruct this sequence).

#### 2c. Anchored rubrics with level descriptions are essential

Numeric scores (1-5, 0-100) are meaningless without concrete anchors. Research consistently shows:

- GoDaddy calibration study: "Uncalibrated LLM scores don't just introduce noise: they can invert your preferences, ranking worse models as better."
- Rhesis AI: "A numeric score between 1 and 5 is only meaningful if each number corresponds to something concrete."
- ResearchRubrics (2025): Expert-written rubric criteria with ternary grading (yes/partial/no) outperformed binary grading for agreement with human evaluators.

**Implication:** Each of our 3 dimensions needs explicit score-level descriptions (what a 0-20, 20-40, 40-60, 60-80, 80-100 looks like for THAT specific dimension).

#### 2d. Use 1-5 categorical scale, map to 0-100 afterward

**Confidence: MEDIUM-HIGH** (strong practitioner consensus, weaker theoretical backing)

Multiple sources recommend categorical/ordinal scales over continuous numeric:

- Arize AI: "Binary outputs tend to produce more stable and reliable evaluations than more subtle numeric scoring."
- Hamel Husain (AI Evals guide): "We recommend starting with binary Pass/Fail evaluations in most cases."
- Rhesis AI: "Categorical scores are more stable and interpretable."

However, we need granularity for trend tracking. Compromise: **Use a 5-level ordinal scale** (1-5) with concrete anchors, then map to 0-100 (1=10, 2=30, 3=50, 4=70, 5=90). This gives us 5 stable buckets + continuous aggregation.

### 3. Known Biases and Mitigations

**Confidence: HIGH** (well-documented in literature)

| Bias | Description | Mitigation |
|---|---|---|
| **Position bias** | Judge favors content earlier/later in prompt | Fixed: our transcripts have natural ordering; no pairwise comparison needed |
| **Verbosity bias** | Longer responses scored higher | Anchor rubric to *quality* not *length*; explicitly state "length does not affect score" |
| **Self-enhancement** | Model rates its own style higher | Use different model as judge vs. agent (e.g., Sonnet judges Opus agent) |
| **Leniency bias** | LLMs tend to give high scores | Calibrate: include "what a 1 looks like" in rubric; use ternary sub-questions that force identification of weaknesses |
| **Score bunching** | All scores cluster around 3-4/5 | Use 5-level ordinal with forced anchoring; include negative indicators per level |

**Key finding from Shi et al. (2025, ACL):** Position bias is "strongly affected by the quality gap between solutions" --- when quality differences are clear, bias is minimal. Our dimensions have clear observable indicators (graph queries present/absent, evidence cited/not-cited), so we expect LOW bias risk.

### 4. Our 3 Dimensions Are Well-Suited for LLM Judgment

**Confidence: HIGH**

Mapping our dimensions to established evaluation categories:

| Our Dimension | Analogous In Literature | Observable Signals |
|---|---|---|
| `graph_query_quality` | RAGAS `contextual_precision` + `contextual_recall` | BSKG queries present, query types, query specificity, query results used |
| `evidence_utilization` | RAGAS `faithfulness`, LLM-Rubric `citation_quality` | References to graph nodes, code locations cited, evidence-claim links |
| `conclusion_grounding` | RAGAS `answer_relevancy`, ResearchRubrics `factual_grounding` | Conclusions trace to evidence, no unsupported claims, finding severity justified |

All three have **concrete, observable indicators** in the transcript (tool calls, BSKG query text, response text referencing node IDs). This makes them ideal for LLM-as-judge --- the judge can point to specific transcript segments as evidence for its score.

### 5. Existing Heuristic Approach Is Fundamentally Wrong

**Confidence: HIGH** (confirmed by codebase inspection)

The current `_heuristic_dimension_score()` in `reasoning_evaluator.py` (lines 359-443) uses proxy metrics:
- "evidence" dimension: Scores based on `len(bskg_queries) * 15` --- counts queries, not quality
- "reasoning" dimension: Scores based on `unique_tools` count --- tool diversity != reasoning quality
- "graph" dimension: Checks if "Bash" appears early in tool sequence --- completely wrong proxy

These heuristics cannot distinguish between an agent that ran 10 irrelevant BSKG queries vs. one that ran 3 precise, targeted queries. They cannot assess whether conclusions are grounded in evidence. This confirms P2-IMP-03's finding and the necessity of LLM-based evaluation.

### 6. Single-Call vs. Multi-Call Architecture

**Confidence: MEDIUM-HIGH**

Two viable patterns for evaluating 3 dimensions:

**Option A: One call, structured schema for all 3 dimensions.**
- Pro: 1 subprocess call instead of 3. Lower latency (2-5s vs 6-15s).
- Pro: Model sees full context once, can cross-reference dimensions.
- Con: Longer prompt, slightly higher risk of score contamination between dimensions.
- Con: If one dimension fails, all fail.

**Option B: Three separate calls, one per dimension.**
- Pro: Clean isolation per dimension. Easier to retry individual failures.
- Pro: Can use different models per dimension (e.g., Haiku for presence-checks, Sonnet for reasoning).
- Con: 3x latency, 3x cost.

**Recommendation: Option A** for v1. The `--json-schema` guarantee means the model MUST produce all 3 dimension scores in one call. Cross-contamination risk is mitigated by the structured rubric forcing separate reasoning per dimension. Upgrade to Option B only if calibration tests show dimension correlation issues.

## Recommendation

**PRESCRIPTIVE: Use a single `claude -p` call per evaluation with a 5-level anchored rubric per dimension, chain-of-thought reasoning per dimension, and `--json-schema` enforcing the output structure.**

### JSON Schema for Dimension Scoring

```json
{
  "type": "object",
  "properties": {
    "graph_query_quality": {
      "type": "object",
      "properties": {
        "reasoning": {
          "type": "string",
          "description": "Step-by-step reasoning about graph query quality, citing specific transcript evidence"
        },
        "evidence_refs": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Specific transcript segments or observations supporting the score"
        },
        "level": {
          "type": "integer",
          "minimum": 1,
          "maximum": 5,
          "description": "1=absent/broken, 2=minimal/generic, 3=adequate, 4=good/targeted, 5=excellent/comprehensive"
        }
      },
      "required": ["reasoning", "evidence_refs", "level"]
    },
    "evidence_utilization": {
      "type": "object",
      "properties": {
        "reasoning": { "type": "string" },
        "evidence_refs": {
          "type": "array",
          "items": { "type": "string" }
        },
        "level": { "type": "integer", "minimum": 1, "maximum": 5 }
      },
      "required": ["reasoning", "evidence_refs", "level"]
    },
    "conclusion_grounding": {
      "type": "object",
      "properties": {
        "reasoning": { "type": "string" },
        "evidence_refs": {
          "type": "array",
          "items": { "type": "string" }
        },
        "level": { "type": "integer", "minimum": 1, "maximum": 5 }
      },
      "required": ["reasoning", "evidence_refs", "level"]
    }
  },
  "required": ["graph_query_quality", "evidence_utilization", "conclusion_grounding"]
}
```

### Prompt Template

```
You are an expert evaluator assessing an AI security agent's REASONING QUALITY.
You are NOT judging whether the agent found vulnerabilities. You are judging
HOW it reasoned --- specifically whether it used its knowledge graph effectively,
utilized evidence properly, and grounded its conclusions.

## TRANSCRIPT TO EVALUATE
{transcript}

## EVALUATION RUBRIC

Score each dimension on a 1-5 scale. For each dimension:
1. Quote specific transcript evidence supporting your assessment
2. Explain your reasoning step by step
3. Assign the level

Response length does NOT affect scores. Short, precise reasoning scores higher
than long, unfocused reasoning.

### Dimension 1: graph_query_quality
Did the agent query the BSKG (knowledge graph) effectively?

| Level | Description |
|-------|-------------|
| 1 - Absent | No BSKG queries executed. Agent read code manually without using the graph. |
| 2 - Minimal | 1-2 generic queries (e.g., "list all functions"). No targeted investigation. |
| 3 - Adequate | Queried relevant entities but missed obvious follow-up queries. Used basic query patterns only. |
| 4 - Good | Targeted queries based on hypothesis (e.g., querying specific state variables after identifying a potential reentrancy). Follow-up queries based on initial results. |
| 5 - Excellent | Comprehensive graph exploration: cross-function data flow queries, permission chain traversal, semantic operation ordering checks. Queries directly test vulnerability hypotheses. |

### Dimension 2: evidence_utilization
Did the agent USE query results and tool outputs in its analysis?

| Level | Description |
|-------|-------------|
| 1 - Ignored | Query results returned but agent did not reference them. Analysis appears disconnected from graph data. |
| 2 - Superficial | Mentioned query results but did not integrate them into reasoning. "The graph shows X" without connecting to vulnerability analysis. |
| 3 - Adequate | Referenced specific graph nodes or code locations from queries. Some evidence-claim links present but incomplete. |
| 4 - Good | Systematically cited graph evidence for each claim. Connected tool outputs to specific vulnerability conditions. Evidence chain mostly traceable. |
| 5 - Excellent | Every claim traces to specific graph nodes, code locations, or tool outputs. Cross-referenced multiple evidence sources. Explicitly noted gaps where evidence was insufficient. |

### Dimension 3: conclusion_grounding
Are the agent's conclusions supported by the evidence it gathered?

| Level | Description |
|-------|-------------|
| 1 - Ungrounded | Conclusions stated with no evidence trail. Severity ratings appear arbitrary. Findings cannot be verified from the transcript. |
| 2 - Weakly grounded | Some evidence cited but conclusions go significantly beyond what evidence supports. Severity inflated relative to demonstrated impact. |
| 3 - Adequate | Main conclusions have supporting evidence. Some claims lack full evidence chain. Severity roughly matches demonstrated impact. |
| 4 - Well grounded | Each finding clearly traces to evidence. Severity justified by demonstrated conditions. Limitations acknowledged. |
| 5 - Rigorously grounded | All conclusions explicitly cite evidence. Counter-evidence considered. Confidence levels stated. Severity calibrated to demonstrated economic impact with specific conditions. |
```

### Level-to-Score Mapping

```python
LEVEL_TO_SCORE = {1: 10, 2: 30, 3: 50, 4: 70, 5: 90}
```

This mapping avoids 0 (absence of evaluation) and 100 (perfect, unrealistic), creating 5 stable, well-separated buckets that aggregate cleanly into the existing 0-100 DimensionScore system.

### Integration with Existing ReasoningEvaluator

Replace `_heuristic_dimension_score()` with an LLM call for dimensions matching `graph_query_quality`, `evidence_utilization`, `conclusion_grounding`:

```python
# In ReasoningEvaluator._evaluate_dimensions(), replace heuristic fallback:

# Current (WRONG):
#   heuristic_score = self._heuristic_dimension_score(dim_name, dim_weight, collected_output)

# New:
if self._should_use_llm_scoring(dim_name):
    llm_score = self._llm_dimension_score(dim_name, dim_weight, collected_output)
    scores.append(llm_score)
    continue

# Heuristic fallback only for dimensions without LLM rubrics
heuristic_score = self._heuristic_dimension_score(dim_name, dim_weight, collected_output)
scores.append(heuristic_score)
```

### Calibration Protocol

Before trusting LLM scores in production:

1. **Create 5 calibration transcripts** --- one per level (1-5) for each dimension. These are hand-scored "golden" references.
2. **Run the evaluator 5x per transcript** (n=25 total per dimension, 75 total). Check:
   - Mean score within 1 level of golden reference
   - Standard deviation < 0.8 levels across runs
   - No systematic leniency bias (mean across all transcripts should be ~3.0, not ~4.0)
3. **If leniency detected:** Add "Most agent transcripts score 2-3. A score of 4 or 5 should be rare and requires exceptional evidence." to the rubric preamble.
4. **If high variance detected:** Switch to Option B (separate calls per dimension) or upgrade judge model from Sonnet to Opus.

### Cost and Latency Estimates

| Metric | Estimate | Notes |
|---|---|---|
| Input tokens per eval | ~2,000-4,000 | Rubric (~1,200) + transcript excerpt (~1,000-3,000) |
| Output tokens per eval | ~500-800 | 3 dimensions x (reasoning + evidence + level) |
| Latency (Sonnet) | ~3-6s | Single subprocess call |
| Cost (Sonnet) | ~$0.01-0.03 | Per evaluation; covered by Claude Code subscription |
| Calls per test run | 1 per scenario | Not per dimension |

### Evaluation Contract Schema Update

The `reasoning_dimensions` field in the evaluation contract schema should evolve from bare strings to structured objects:

```json
{
  "reasoning_dimensions": [
    {
      "name": "graph_query_quality",
      "weight": 1.0,
      "grader": "llm",
      "rubric_id": "gqq-v1"
    },
    {
      "name": "evidence_utilization",
      "weight": 1.0,
      "grader": "llm",
      "rubric_id": "eu-v1"
    },
    {
      "name": "conclusion_grounding",
      "weight": 1.0,
      "grader": "llm",
      "rubric_id": "cg-v1"
    }
  ]
}
```

This allows mixing heuristic and LLM-graded dimensions in the same contract.

### Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| LLM scores inconsistent across runs | MEDIUM | LOW (with anchored rubrics) | Calibration protocol; retry on high-variance dimensions |
| Leniency bias inflates all scores | MEDIUM | MEDIUM | Explicit anti-leniency instruction; calibration with known-bad transcripts |
| Transcript too long for context window | LOW | LOW (Sonnet: 200K context) | Truncate to relevant segments; summarize tool calls |
| Subprocess latency slows test suite | LOW | HIGH (expected ~5s/eval) | Acceptable for standard/deep eval; skip for shallow depth |
| Judge model disagrees with human assessment | MEDIUM | MEDIUM | Calibration protocol catches this pre-deployment |

## Sources

### Primary (HIGH confidence)
- G-Eval paper and DeepEval implementation: https://deepeval.com/docs/metrics-llm-evals --- CoT + structured scoring framework, widely adopted
- LLM-Rubric (Hashemi et al., ACL 2024): https://arxiv.org/abs/2501.00274 --- Multidimensional calibrated evaluation with RMS error < 0.5
- RAGAS framework: https://docs.ragas.io --- 4-dimension RAG evaluation (contextual recall/precision, faithfulness, relevancy)
- Langfuse LLM-as-a-Judge guide (2026): https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge

### Secondary (MEDIUM-HIGH confidence)
- GER-Eval / "Learning to Judge" (Siro et al., 2026): https://arxiv.org/html/2602.08672v1 --- LLMs reliably generate and apply evaluation rubrics; scoring reliability degrades in factual settings but holds for quality assessment
- Shi et al., "Judging the Judges" (ACL 2025): https://aclanthology.org/2025.ijcnlp-long.18/ --- Position bias study across 15 LLM judges, 150K+ instances; bias affected by quality gap
- GoDaddy calibration study: https://www.godaddy.com/resources/news/calibrating-scores-of-llm-as-a-judge --- Uncalibrated scores can invert preferences
- Rhesis AI custom metrics guide: https://rhesis.ai/post/llm-judge-metrics --- Best practices for dimension separation, anchoring, CoT + structured output
- ResearchRubrics (2025): https://arxiv.org/html/2511.07685v1 --- 2,500+ expert rubrics; ternary grading outperforms binary
- Chain-of-Rubrics (CoR): https://www.emergentmind.com/topics/chain-of-rubrics-cor-prompting-framework --- Rubric-guided evaluation steps, up to 38.9% improvement
- Arize AI LLM-as-Judge: https://arize.com/llm-as-a-judge/ --- Binary > numeric for stability; structured prompts essential
- Towards Data Science practical guide: https://towardsdatascience.com/llm-as-a-judge-a-practical-guide/ --- 6-question prompt design framework

### Codebase (HIGH confidence)
- `tests/workflow_harness/graders/reasoning_evaluator.py` --- Current heuristic implementation (lines 359-443) confirmed inadequate
- GAP-01 resolution --- `claude -p --json-schema` mechanism confirmed working
