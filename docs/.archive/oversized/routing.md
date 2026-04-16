# Model Routing Reference

**Purpose:** Complete documentation of model routing rules, thresholds, and cost optimization.
**Last Updated:** 2026-01-22

---

## Table of Contents

1. [Routing Architecture](#routing-architecture)
2. [Task Types](#task-types)
3. [Runtime Selection Rules](#runtime-selection-rules)
4. [Model Selection by Task Type](#model-selection-by-task-type)
5. [Context Size Thresholds](#context-size-thresholds)
6. [Cost Optimization](#cost-optimization)
7. [Ranking System](#ranking-system)
8. [Loop Prevention](#loop-prevention)

---

## Routing Architecture

```
Task Request
    |
    v
+-----------------+
|   TaskRouter    |  Policy-based routing decisions
+--------+--------+
         |
         v
+---------------------------------------------------------+
|                  Runtime Selection                       |
+--------------+--------------+--------------+-------------+
|  OpenCode    |  Claude Code |  Codex CLI   | Anthropic |
|  (Default)   |  (Critical)  |  (Reviews)   | (Direct)  |
+--------------+--------------+--------------+-------------+
         |
         v
+-----------------+
|  ModelSelector  |  EMA-ranked model selection
+--------+--------+
         |
         v
+---------------------------------------------------------+
|                   Model Execution                        |
+--------------+--------------+--------------+-------------+
| Free Models  | Budget       | Quality      | Premium   |
| (MiniMax M2) | (DeepSeek)   | (Claude)     | (Opus)    |
+--------------+--------------+--------------+-------------+
```

---

## Task Types

**Location:** `src/alphaswarm_sol/agents/runtime/types.py`

### TaskType Enum (10 categories)

| TaskType | Description | Typical Model Tier |
|----------|-------------|-------------------|
| `CODE` | Code generation, Foundry tests | Budget/Quality |
| `REVIEW` | Code review, guard detection | Budget |
| `CRITICAL` | Exploit construction, verification | Premium |
| `REASONING` | Multi-step logical analysis | Quality |
| `SUMMARIZE` | Condensing information | Free |
| `VERIFY` | Fact-checking, validation | Free |
| `HEAVY` | Large context processing | Specialized |
| `FAST` | Low-latency requirements | Budget |
| `EXPLORATORY` | Open-ended research | Quality |
| `INTEGRATION` | Verdict merging, synthesis | Budget |

### Role-to-TaskType Mapping

```python
ROLE_TO_TASK_TYPE: Dict[AgentRole, TaskType] = {
    AgentRole.ATTACKER: TaskType.CRITICAL,
    AgentRole.DEFENDER: TaskType.REVIEW,
    AgentRole.VERIFIER: TaskType.CRITICAL,
    AgentRole.TEST_BUILDER: TaskType.CODE,
    AgentRole.SUPERVISOR: TaskType.INTEGRATION,
    AgentRole.INTEGRATOR: TaskType.SUMMARIZE,
}
```

---

## Runtime Selection Rules

**Location:** `src/alphaswarm_sol/agents/runtime/router.py`

### TaskRouter._determine_runtime()

Returns: `Tuple[RuntimeType, Optional[str]]` (runtime type, model hint)

### Decision Tree

```
1. Is accuracy_critical AND (ATTACKER or VERIFIER)?
   +-- YES -> Claude Code (quality guarantee)

2. Is task_type == REVIEW?
   +-- YES -> Codex CLI (model diversity)

3. Is context_size > HEAVY_CONTEXT_THRESHOLD (500K)?
   +-- YES -> OpenCode with Gemini 3 Ultra hint

4. Is context_size > LARGE_CONTEXT_THRESHOLD (200K)?
   +-- YES -> OpenCode with Gemini 3 Flash hint

5. Default
   +-- OpenCode (cost optimization)
```

### RoutingPolicy Dataclass

```python
@dataclass
class RoutingPolicy:
    task_type: TaskType
    role: Optional[AgentRole] = None
    accuracy_critical: bool = False
    context_size: int = 0
    max_cost_usd: Optional[float] = None
    latency_sensitive: bool = False
```

### Routing Statistics

```python
# TaskRouter tracks route counts
router.get_statistics()
# Returns: {"opencode": 45, "claude_code": 12, "codex": 8}
```

---

## Model Selection by Task Type

**Location:** `src/alphaswarm_sol/agents/runtime/opencode.py`

### OpenCodeRuntime Model Routing

| TaskType | Primary Model | Rationale |
|----------|---------------|-----------|
| `CRITICAL` | Claude Opus 4 | Deep exploit reasoning |
| `REASONING` | DeepSeek V3.2 | 671B MoE, $0.27/M in |
| `CODE` | Claude Sonnet 4 | Code generation quality |
| `REVIEW` | GPT-4.1 | Alternative perspective |
| `SUMMARIZE` | MiniMax M2 | **FREE** via OpenRouter |
| `VERIFY` | BigPickle M1 | **FREE** via OpenRouter |
| `HEAVY` | Gemini 3 Flash | 1M context window |
| `FAST` | Gemini 3 Flash | Low latency |
| `EXPLORATORY` | Claude Sonnet 4 | Balanced quality/cost |
| `INTEGRATION` | Claude Haiku 4 | Fast, cheap |

### Free Model Details

| Model | Provider | Context | Use Case |
|-------|----------|---------|----------|
| MiniMax M2 | OpenRouter | 128K | Summarization |
| BigPickle M1 | OpenRouter | 64K | Verification |

### Premium Model Details

| Model | Provider | Context | Cost (per 1M tokens) |
|-------|----------|---------|---------------------|
| Claude Opus 4 | Anthropic | 200K | $15 in / $75 out |
| Claude Sonnet 4 | Anthropic | 200K | $3 in / $15 out |
| Claude Haiku 4 | Anthropic | 200K | $0.25 in / $1.25 out |
| DeepSeek V3.2 | OpenRouter | 128K | $0.27 in / $1.10 out |
| Gemini 3 Flash | Google | 1M | $0.075 in / $0.30 out |

---

## Context Size Thresholds

### Defined Thresholds

| Constant | Value | Action |
|----------|-------|--------|
| `LARGE_CONTEXT_THRESHOLD` | 200,000 tokens | Route to Gemini Flash |
| `HEAVY_CONTEXT_THRESHOLD` | 500,000 tokens | Route to Gemini Ultra |
| `TOKEN_CEILING` | 100,000 tokens | Loop prevention trigger |

### Context Estimation

```python
def estimate_context_tokens(messages: List[Dict]) -> int:
    """Rough estimation: 4 characters per token."""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return total_chars // 4
```

### Model Context Limits

| Model | Max Context |
|-------|-------------|
| Claude Opus 4 | 200,000 |
| Claude Sonnet 4 | 200,000 |
| Claude Haiku 4 | 200,000 |
| GPT-4.1 | 128,000 |
| DeepSeek V3.2 | 128,000 |
| Gemini 3 Flash | 1,000,000 |
| Gemini 3 Ultra | 2,000,000 |

---

## Cost Optimization

### Target Savings

| Metric | Target | Achieved |
|--------|--------|----------|
| Monthly cost reduction | 75-95% | ~85% estimated |
| API billing baseline | $500+/mo | Reference |
| Optimized target | $31-116/mo | Goal |

### Cost Reduction Strategies

1. **Free Models for Low-Stakes Tasks**
   - SUMMARIZE -> MiniMax M2 (free)
   - VERIFY -> BigPickle M1 (free)
   - Savings: 100% on these task types

2. **Budget Models for Medium Tasks**
   - REASONING -> DeepSeek V3.2 ($0.27/M in)
   - CODE/REVIEW -> Claude Haiku ($0.25/M in)
   - Savings: 80-90% vs Opus

3. **Prompt Caching (Anthropic)**
   - Cache control on system prompt and tools
   - 90% cost reduction on cached reads
   - Breakeven: ~3 requests with same prefix

4. **Context-Aware Routing**
   - Large contexts -> Gemini (cheaper per token at scale)
   - Small contexts -> Claude (better quality/token)

### Cost Tracking

```python
# PropulsionEngine tracks costs
engine.get_cost_summary()
# Returns: CostSummary(
#     total_cost_usd=0.45,
#     execution_count=12,
#     by_model={"claude-opus-4": 0.30, "minimax-m2": 0.00, ...},
#     by_task_type={"CRITICAL": 0.30, "SUMMARIZE": 0.00, ...}
# )
```

---

## Ranking System

**Location:** `src/alphaswarm_sol/agents/ranking/`

### EMA-Based Updates

```python
# Exponential Moving Average for ranking updates
EMA_DECAY = 0.95  # Recent feedback contributes 5%

new_value = (EMA_DECAY * old_value) + ((1 - EMA_DECAY) * observation)
```

### Ranking Metrics

| Metric | Description | Impact |
|--------|-------------|--------|
| `success_rate` | Completion without errors | Filter threshold |
| `avg_quality` | Output quality score (0-1) | Sort for accuracy_critical |
| `avg_latency_ms` | Response time | Sort for latency_sensitive |
| `avg_cost_usd` | Cost per execution | Sort for default |

### Selection Algorithm

```python
def select_model(profile: TaskProfile, rankings: Dict[str, ModelRanking]) -> str:
    # 1. Filter by context capability
    candidates = filter_by_capability(models, profile.context_size)

    # 2. Filter by accuracy thresholds (if accuracy_critical)
    if profile.accuracy_critical:
        candidates = filter_by_accuracy(candidates, rankings,
            min_success_rate=0.85,
            min_quality=0.80)

    # 3. Sort by priority
    if profile.latency_sensitive:
        return sort_by_latency(candidates, rankings)[0]
    elif profile.accuracy_critical:
        return sort_by_quality(candidates, rankings)[0]
    else:
        return sort_by_cost(candidates, rankings)[0]
```

### Accuracy Thresholds

| Threshold | Value | Applied When |
|-----------|-------|--------------|
| `min_success_rate` | 0.85 | accuracy_critical=True |
| `min_quality` | 0.80 | accuracy_critical=True |

### Rankings Storage

```yaml
# .vrs/rankings/rankings.yaml
schema_version: "1.0"
rankings:
  claude-opus-4:
    success_rate: 0.95
    avg_quality: 0.92
    avg_latency_ms: 3500
    avg_cost_usd: 0.045
    sample_count: 127
    last_updated: "2026-01-22T10:30:00Z"
  minimax-m2:
    success_rate: 0.88
    avg_quality: 0.75
    avg_latency_ms: 1200
    avg_cost_usd: 0.000
    sample_count: 45
```

### Feedback Collection

```python
feedback = TaskFeedback(
    model="claude-opus-4",
    task_type=TaskType.CRITICAL,
    success=True,
    quality_score=0.95,
    latency_ms=3200,
    cost_usd=0.042,
    error=None
)
collector.record(feedback)
```

---

## Loop Prevention

**Location:** `src/alphaswarm_sol/agents/runtime/opencode.py`

### Prevention Mechanisms

| Mechanism | Threshold | Action |
|-----------|-----------|--------|
| Max iterations | 10 | Stop execution |
| Repeated outputs | 3 consecutive | Stop execution |
| Token ceiling | 100,000 tokens | Stop execution |

### Implementation

```python
class OpenCodeRuntime:
    MAX_ITERATIONS = 10
    MAX_REPEATED_OUTPUTS = 3
    TOKEN_CEILING = 100_000

    def _check_loop_prevention(
        self,
        iteration: int,
        outputs: List[str],
        total_tokens: int
    ) -> Optional[str]:
        """Returns stop reason if loop detected, None otherwise."""

        if iteration >= self.MAX_ITERATIONS:
            return "max_iterations_reached"

        if len(outputs) >= self.MAX_REPEATED_OUTPUTS:
            recent = outputs[-self.MAX_REPEATED_OUTPUTS:]
            if len(set(recent)) == 1:
                return "repeated_output_detected"

        if total_tokens >= self.TOKEN_CEILING:
            return "token_ceiling_exceeded"

        return None
```

### Output Deduplication

```python
def _deduplicate_output(self, output: str, previous: List[str]) -> str:
    """Remove repeated content from output."""
    # Compares with previous 3 outputs
    # Returns only novel content
```

---

## Configuration Reference

### RuntimeConfig

```python
@dataclass
class RuntimeConfig:
    preferred_sdk: str = "opencode"  # opencode, anthropic, openai
    enable_prompt_caching: bool = True
    timeout_seconds: int = 120
    max_retries: int = 3
    retry_base_seconds: float = 2.0
    enable_rankings: bool = True
    rankings_path: Path = Path(".vrs/rankings/rankings.yaml")
```

### PropulsionConfig

```python
@dataclass
class PropulsionConfig:
    enable_fallback: bool = True
    fallback_runtime: str = "claude_code"
    cost_tracking: bool = True
    loop_prevention: bool = True
    max_parallel_agents: int = 5
```

---

## Error Handling

### Retry Policy

| Error Type | Action | Max Retries |
|------------|--------|-------------|
| Rate limit (429) | Retry with backoff | 3 |
| Connection error | Retry with backoff | 3 |
| Timeout | Retry with backoff | 3 |
| Server error (5xx) | Retry with backoff | 3 |
| Auth error (401/403) | Fail fast | 0 |
| Bad request (4xx) | Fail fast | 0 |

### Backoff Calculation

```python
backoff_seconds = retry_base_seconds * (2 ** attempt)
# Example: 2.0, 4.0, 8.0 seconds
```

### Fallback Behavior

```python
# If primary runtime fails, fallback to Claude Code
if response.error and config.enable_fallback:
    response = await claude_code_runtime.execute(config, messages)
    response.metadata["fallback"] = True
```

---

## Quick Reference Card

### Runtime Selection

```
ATTACKER + accuracy_critical -> Claude Code
VERIFIER + accuracy_critical -> Claude Code
REVIEW -> Codex CLI
context > 500K -> OpenCode (Gemini Ultra)
context > 200K -> OpenCode (Gemini Flash)
Default -> OpenCode (cost-optimized)
```

### Model Selection (OpenCode)

```
CRITICAL -> Claude Opus 4
REASONING -> DeepSeek V3.2
CODE -> Claude Sonnet 4
SUMMARIZE -> MiniMax M2 (FREE)
VERIFY -> BigPickle M1 (FREE)
HEAVY -> Gemini 3 Flash
```

### Cost Tiers

```
FREE: MiniMax M2, BigPickle M1
BUDGET: DeepSeek V3.2, Claude Haiku 4, Gemini Flash
QUALITY: Claude Sonnet 4, GPT-4.1
PREMIUM: Claude Opus 4
```

---

*Reference: routing.md*
*Last Updated: 2026-01-22*
