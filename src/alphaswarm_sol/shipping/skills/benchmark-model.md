---
name: vrs-benchmark-model
description: |
  Model comparison benchmark skill. Runs corpus against multiple models
  to compare accuracy per task type and update rankings.

  Invoke when user wants to:
  - Compare models: "benchmark models", "compare Claude vs DeepSeek", "/vrs-benchmark-model"
  - Update rankings: "recalculate rankings", "model evaluation"
  - Evaluate new model: "test new model", "benchmark Gemini"

  This skill runs model comparison benchmarks:
  1. Load corpus and ground truth
  2. Run each model on task corpus
  3. Calculate accuracy metrics per task type
  4. Update EMA-based rankings
  5. Generate cost-accuracy curves

slash_command: vrs:benchmark-model
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(uv run*)
  - Bash(alphaswarm*)
---

# VRS Benchmark Model - Model Comparison

You are the **VRS Benchmark Model** skill, responsible for running model comparison benchmarks on the test corpus. This skill evaluates multiple models on accuracy, task-type suitability, and cost efficiency.

## Philosophy

From Test Forge Context:
- **Accuracy is paramount** - Quality > cost optimization
- **Task-type specific** - Models excel at different tasks
- **EMA-based ranking** - Smooth updates, no sudden swings
- **95% threshold** - Model must achieve >= 95% of Opus accuracy to be eligible

**Comparison Dimensions (Weighted):**
1. **Quality/Accuracy (60%)** - Precision, recall, F1 per task type
2. **Task-Type Suitability (30%)** - Which model excels at which task
3. **Cost-Accuracy Curves (10%)** - Cost per percentage point of accuracy

## How to Invoke

```bash
/vrs-benchmark-model
/vrs-benchmark-model --models "opus,sonnet,deepseek"
/vrs-benchmark-model --task-type detect
/vrs-benchmark-model --corpus recent-audits
```

---

## Model Pool

### Claude Baseline (Quality Standard)

| Model | Purpose | Cost (per 1M tokens) |
|-------|---------|---------------------|
| Claude Opus 4.5 | Maximum quality reference | $15 input / $75 output |
| Claude Sonnet 4.5 | Balanced baseline | $3 input / $15 output |
| Claude Haiku 4.5 | Speed/cost baseline | $0.80 input / $4 output |

### OpenCode SDK (Via OpenRouter)

| Model | Cost | Context | Primary Use |
|-------|------|---------|-------------|
| Gemini 3 Pro | $2/M in | 1M+ | Complex reasoning |
| Gemini 3 Flash | $0.50/M in | 1M | Agentic workflows |
| DeepSeek V3.2 | $0.25/M in | 164K | Reasoning |
| Grok Code Fast 1 | **FREE** | 256K | Agentic coding |
| GLM-4.7 Z.AI | $6/mo | 128K | Non-critical |
| MiniMax M2.1 | **FREE** | 204K | Verification |
| Big Pickle | **FREE** | 200K | Validation |

---

## Task Types

| Task Type | Description | Quality Threshold |
|-----------|-------------|-------------------|
| `detect` | Vulnerability detection from patterns | 95% of Opus |
| `analyze` | Deep code analysis | 95% of Opus |
| `verify` | Evidence cross-checking | 95% of Opus |
| `summarize` | Context summarization | 90% of Opus |
| `generate_test` | Test case generation | 90% of Opus |
| `mutation` | Contract mutation | 85% of Opus |

---

## Execution Flow

```
LOAD CORPUS -> RUN MODELS -> CALCULATE METRICS -> UPDATE RANKINGS -> REPORT
```

### Phase 1: Load Corpus
```bash
# Load test corpus from database
# Select contracts based on corpus segment
# Load ground truth labels
```

### Phase 2: Run Models on Corpus
```python
# For each model in benchmark:
for model_id in models:
    for task in corpus.tasks:
        response = run_model(model_id, task.prompt)
        results[model_id].append(evaluate(response, task.ground_truth))
```

### Phase 3: Calculate Metrics
```python
# Per model, per task type:
metrics = {
    "precision": tp / (tp + fp),
    "recall": tp / (tp + fn),
    "f1_score": harmonic_mean(precision, recall),
    "cost_per_1000": model.cost * tokens_used / 1000,
    "vs_opus_accuracy": f1 / opus_f1 * 100
}
```

### Phase 4: Update Rankings
```yaml
# EMA-based update to .vrs/rankings/rankings.yaml
# alpha = 0.3 (30% new data, 70% history)
new_score = alpha * benchmark_score + (1 - alpha) * current_score
```

### Phase 5: Generate Report
```bash
# Output:
# - Model scores per task type
# - Cost-accuracy curves
# - Ranking updates
# - Eligibility status
```

---

## Usage Examples

### Basic Model Comparison
```bash
/vrs-benchmark-model --models "opus,sonnet"

# Output:
# Model Benchmark Results
# =======================
#
# Task Type: detect
# | Model | Precision | Recall | F1 | vs Opus |
# |-------|-----------|--------|-----|---------|
# | opus-4.5 | 89.2% | 94.1% | 0.916 | 100% |
# | sonnet-4.5 | 87.5% | 92.3% | 0.898 | 98.0% |
#
# Rankings Updated: sonnet-4.5 eligible for detect tasks
```

### Specific Task Type
```bash
/vrs-benchmark-model --models "opus,deepseek,gemini" --task-type verify

# Compares models only on verification tasks
```

### Full Model Pool
```bash
/vrs-benchmark-model --all-models --task-type detect

# Benchmarks all available models
```

### With Cost Analysis
```bash
/vrs-benchmark-model --models "opus,sonnet,haiku" --include-cost

# Includes cost-accuracy curves in output
```

---

## Output Format

### Benchmark Report
```markdown
# Model Benchmark Report

**Run Date:** 2026-01-22
**Corpus:** recent-audits (25 contracts)
**Task Type:** detect

## Model Scores

| Model | Precision | Recall | F1 | vs Opus | Eligible |
|-------|-----------|--------|-----|---------|----------|
| opus-4.5 | 89.2% | 94.1% | 0.916 | 100.0% | BASELINE |
| sonnet-4.5 | 87.5% | 92.3% | 0.898 | 98.0% | YES |
| haiku-4.5 | 82.1% | 88.7% | 0.853 | 93.1% | NO |
| deepseek-v3.2 | 85.3% | 90.1% | 0.876 | 95.6% | YES |
| gemini-3-pro | 86.1% | 91.2% | 0.886 | 96.7% | YES |

## Cost-Accuracy Curves

| Model | Cost/1K | F1 | Cost/Accuracy Point |
|-------|---------|-----|---------------------|
| opus-4.5 | $15.00 | 0.916 | $16.38 |
| sonnet-4.5 | $3.00 | 0.898 | $3.34 |
| deepseek-v3.2 | $0.25 | 0.876 | $0.29 |

## Optimal Selection

**Best Quality:** opus-4.5 (F1: 0.916)
**Best Value:** deepseek-v3.2 (F1: 0.876 @ $0.25/1K)
**Recommended:** sonnet-4.5 (98% of Opus at 1/5 cost)

## Rankings Updated

```yaml
# .vrs/rankings/rankings.yaml
detect:
  - model: opus-4.5
    score: 0.916
    eligible: true
  - model: sonnet-4.5
    score: 0.898
    eligible: true
  - model: deepseek-v3.2
    score: 0.876
    eligible: true
```
```

---

## Ranking Integration

### Rankings File Format
```yaml
# .vrs/rankings/rankings.yaml
task_types:
  detect:
    models:
      - id: opus-4.5
        score: 0.916
        cost_per_1k: 15.00
        eligible: true
        last_updated: 2026-01-22
      - id: sonnet-4.5
        score: 0.898
        cost_per_1k: 3.00
        eligible: true
        last_updated: 2026-01-22
  verify:
    models:
      - id: opus-4.5
        score: 0.932
        eligible: true
        last_updated: 2026-01-22
```

### EMA Update Formula
```python
# Exponential Moving Average for stable rankings
alpha = 0.3  # Weight for new data
new_score = alpha * benchmark_score + (1 - alpha) * current_score

# Prevents:
# - Single bad run tanking a model
# - Single good run over-promoting a model
```

---

## Eligibility Rules

### Quality Threshold
- Model must achieve >= 95% of Opus F1 for task type
- Security tasks (detect, verify, analyze) default to Claude

### Free Models
- Evaluated for research purposes
- Not used in production without explicit approval
- Useful for non-critical tasks (mutation, summarize)

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-test-full` | Complete test orchestration |
| `/vrs-test-component` | Single agent component test |
| `/vrs-track-gap` | Record testing gaps |

---

## Write Boundaries

This skill is restricted to writing in:
- `.vrs/rankings/` - Model rankings updates
- `.vrs/testing/benchmark-results/` - Benchmark result files

All other directories are read-only.

---

## Notes

- Benchmarks should run on consistent corpus for fair comparison
- EMA updates prevent ranking volatility
- Cost tracking is informational, not a quality gate
- Free models are evaluated but require approval for production
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
