# Token Efficiency & Cost Optimization Research

**Researched:** 2026-01-21
**Purpose:** Inform Phase 5.2 Multi-Agent SDK Integration with latest techniques

## Executive Summary

This research identifies **12 key optimization strategies** applicable to multi-agent security auditing workflows. Combined properly, these can achieve:

- **90% input token cost reduction** (prompt caching)
- **70% output token reduction** (token-efficient tool use)
- **2-25x cost reduction** (model routing/cascading)
- **46% serving cost reduction** (agentic plan caching)
- **85% latency reduction** (TTFT via caching)

---

## 1. Prompt Caching (CRITICAL)

### Anthropic Claude Implementation

```python
# Cache control marker for stable prefixes
{
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": "<system_prompt>...",
            "cache_control": {"type": "ephemeral"}
        }
    ]
}
```

**Key Parameters:**
- **Minimum prefix:** 1024 tokens
- **Cache TTL:** 5 minutes
- **Cache write cost:** 125% of base (25% premium)
- **Cache read cost:** 10% of base (90% discount)
- **Breakeven:** ~3 requests with same prefix

**Best Practices:**
- Place stable content FIRST (system prompts, tool definitions, VulnDocs)
- Use up to 4 cache breakpoints strategically
- Cache-aware rate limits: cache reads don't count against ITPM

**Multi-Agent Application:**
```
┌─────────────────────────────────────────────────────┐
│ CACHED PREFIX (shared across all agents)            │
│ - VulnDocs knowledge (patterns, examples)           │
│ - Tool definitions (Foundry, Slither, etc.)         │
│ - Audit protocol instructions                       │
│ - Target contract source code                       │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│ DYNAMIC SUFFIX (per-agent, per-bead)                │
│ - Specific bead context                             │
│ - Agent role instructions                           │
│ - Current investigation state                       │
└─────────────────────────────────────────────────────┘
```

### OpenAI Implementation

- **Automatic:** No opt-in required for prompts >1024 tokens
- **Organization-scoped:** Shared across API keys
- **Key use case:** "Agents using tools and structured outputs"

---

## 2. Token-Efficient Tool Use (Anthropic)

### Claude 4 Built-In Efficiency

**Feature:** All Claude 4 models have built-in token-efficient tool use.

```python
# For Claude 3.7 Sonnet (DEPRECATED - remove for Claude 4)
# headers["anthropic-beta"] = "token-efficient-tools-2025-02-19"

# Claude 4+ - no header needed, built-in
```

**Impact:** Up to **70% reduction** in output tokens for tool calls.

**Best Practice:** Migrate to Claude 4 models to automatically benefit.

---

## 3. Model Routing & Cascading

### Strategy: Right-Size Models by Task Complexity

**Research Finding:** Difficulty-Aware Agentic Orchestration (DAAO) achieves highest accuracy while using only **64% of inference costs**.

```
                    ┌─────────────────┐
                    │  Query Router   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
   ┌───────────┐       ┌───────────┐       ┌───────────┐
   │  Haiku    │       │  Sonnet   │       │   Opus    │
   │  (Fast)   │       │ (Balanced)│       │  (Deep)   │
   └───────────┘       └───────────┘       └───────────┘
   - Filtering         - Defender          - Attacker
   - Classification    - Evidence review   - Exploit construction
   - Simple checks     - Test generation   - Verifier reasoning
```

### Cascade Architecture for VKG

| Task | Model | Rationale |
|------|-------|-----------|
| Bead triage/filtering | Haiku | Simple classification |
| Guard detection (Defender) | Sonnet | Fast pattern matching |
| Code analysis | Sonnet | Balanced cost/quality |
| Exploit reasoning (Attacker) | Opus | Deep reasoning required |
| Verification | Opus | Critical accuracy needs |
| Test generation | Sonnet | Code generation strength |
| Summarization | Haiku | Compression task |

### Agreement-Based Cascading (ABC)

**Technique:** Use agreement between ensemble of smaller models to decide when to escalate.

```python
def cascade_decision(query, small_models):
    responses = [model(query) for model in small_models]
    if all_agree(responses):
        return responses[0]  # Cheap inference
    else:
        return large_model(query)  # Escalate
```

**Result:** 2-25x cost reduction with maintained quality.

---

## 4. Agentic Plan Caching (NEW - 2025/2026)

### Technique: Cache and Reuse Plan Templates

**Source:** "Cost-Efficient Serving of LLM Agents via Test-Time Plan Caching" (2025)

**Mechanism:**
1. Extract structured plan templates from successful agent executions
2. Store templates with semantic keys (keyword extraction)
3. On new request, match against cache using semantic similarity
4. Adapt retrieved template to new context using lightweight model

**Implementation for VKG:**

```python
class AgenticPlanCache:
    """Cache vulnerability investigation plans"""

    def __init__(self):
        self.plans = {}  # vuln_class -> plan_template

    def cache_successful_plan(self, bead, verdict, plan_steps):
        """Store successful investigation as template"""
        key = self.extract_semantic_key(bead)
        self.plans[key] = {
            "vuln_class": bead.vuln_class,
            "steps": self.templatize(plan_steps),
            "success_rate": 1.0
        }

    def get_plan_template(self, new_bead):
        """Retrieve and adapt plan for new bead"""
        key = self.extract_semantic_key(new_bead)
        if similar_plan := self.find_similar(key):
            return self.adapt_template(similar_plan, new_bead)
        return None  # No cache hit, agent plans from scratch
```

**Result:** 46.62% cost reduction while maintaining 96.67% performance.

---

## 5. Context Compression

### For Long-Horizon Agent Workflows

**Problem:** Context grows unboundedly in multi-turn agent interactions.

**Solution: Acon (Agent Context Optimization)**

- **Memory reduction:** 26-54%
- **Method:** Compress environment observations + interaction history
- **Distillation:** Large compressor → small model (95% accuracy retained)

### Summarization Checkpoints

```python
def summarization_checkpoint(history, interval=5):
    """Compress history every N turns"""
    if len(history) % interval == 0:
        summary = summarize_interactions(history[-interval:])
        return history[:-interval] + [{"type": "summary", "content": summary}]
    return history
```

**Best Practice:** Preserve decisions/constraints, discard conversational residue.

### Context-Aware Sentence Encoding (CPC)

- **10.93x faster inference** vs token-level compression
- Assigns relevance scores to sentences based on current task
- Better for shorter length constraints

---

## 6. Speculative Decoding

### For Latency-Critical Operations

**Technique:** Use small "draft" model to predict tokens, large model verifies.

**Results:**
- **EAGLE-3 + vLLM:** Up to 2.5x inference speedup
- **Llama4 Maverick:** ~4ms per token on H100 cluster
- **BanditSpec:** Adaptive hyperparameter selection during generation

**When to Use:**
- Real-time agent responses needed
- Low request rate scenarios (memory-bound)
- Interactive debugging sessions

**Limitation:** Currently 2048 context length cap for most speculative models.

---

## 7. Extended Thinking Efficiency (Anthropic)

### Auto-Stripping for Token Efficiency

**Feature:** API automatically strips previous thinking blocks from context window calculation.

```python
# Turn 1: Agent thinks (10K tokens) + responds
# Turn 2: Thinking block stripped, only response preserved
#         → Context preserved for actual content
```

**Implication:** Use extended thinking freely for complex reasoning without context bloat.

### Effort Parameter (Claude Opus 4.5 Beta)

```python
# Control token budget for responses
headers["anthropic-beta"] = "effort-2025-11-24"

# Lower effort = fewer tool calls, more direct action
# Higher effort = more thorough, more tokens
```

**Use Case:** Tune effort based on bead complexity/priority.

---

## 8. Programmatic Tool Calling (Anthropic Beta)

### Feature: Tool Results Don't Consume Context

```python
headers["anthropic-beta"] = "advanced-tool-use-2025-11-20"
```

**Mechanism:**
- Claude writes code to call tools
- Intermediate results processed in code (filtering, aggregation)
- Only final output added to context

**Savings:** Dramatic for multi-tool workflows (Slither + Foundry + custom checks).

---

## 9. Parallel Execution Optimization

### LAMaS (Latency-Aware Multi-Agent System)

**Insight:** Optimize for Critical Execution Path, not total tokens.

```
Sequential:      A → B → C → D     (latency = sum)
Parallel:        A ─┬─ B           (latency = max(path))
                    └─ C → D
```

**Key Technique:** Layer-wise parallel execution by removing unnecessary intra-layer dependencies.

### Cost Trade-offs

**Finding:** Parallel execution costs 25-35% more tokens but can be 36%+ faster.

**Recommendation:** Use parallelism for:
- Independent bead analysis
- Tool execution (Slither, Aderyn in parallel)
- Multi-agent debate rounds

Avoid parallelism for:
- Sequential reasoning chains
- Dependent evidence gathering

---

## 10. Hallucination Reduction (Grounding)

### Critical for Security Auditing

**Techniques:**

1. **Hybrid Retrieval (RAG)**
   - Combine BM25 (sparse) + semantic search (dense)
   - Reciprocal Rank Fusion for result merging
   - **Result:** Lowest hallucination rate

2. **CRAG (Corrective RAG)**
   - Lightweight retrieval evaluator assesses document quality
   - Triggers web search when static corpus insufficient
   - Confidence-based action selection

3. **VulnDocs Integration**
   - Always retrieve relevant VulnDocs for vulnerability class
   - Ground agent claims in documented patterns
   - Evidence-linked findings reduce hallucination

4. **Graph-Retrieved Adaptive Decoding (GRAD)**
   - Fuse corpus-derived evidence with model logits at decode time
   - Favors continuations supported by high evidence
   - Plug-and-play, no retraining

---

## 11. Session Memory (OpenAI Agents SDK)

### For Multi-Turn Agent Workflows

**Feature:** Automatic conversation history management

**Streaming Optimization:**
- Disable auto-compaction for low-latency streaming
- Call `runCompaction()` manually between turns or during idle

**Tool Caching:**
```python
# Cache tool list to avoid repeated fetches
mcp_connection = create_mcp_connection(
    server,
    cacheToolsList=True  # Fetch once, reuse
)
```

---

## 12. Cost-Aware Orchestration

### Framework Design Principles

1. **Cost-Sensitive Reward Function:**
   ```
   reward = success_bonus × success - cost_penalty × cost
   ```

2. **Budget Constraints:**
   - Set per-bead token budgets
   - Escalate to human if budget exceeded without resolution

3. **Usage Tracking:**
   ```python
   @dataclass
   class UsageMetrics:
       input_tokens: int
       output_tokens: int
       cache_read_tokens: int
       cache_write_tokens: int
       model: str
       cost_usd: float
   ```

---

## Implementation Recommendations for Phase 5.2

### Priority 1: Quick Wins (Implement First)

| Technique | Expected Savings | Implementation Effort |
|-----------|------------------|----------------------|
| Prompt caching | 90% input tokens | Low |
| Model routing by role | 50%+ cost | Medium |
| Token-efficient tool use | 70% output | Built-in (Claude 4) |

### Priority 2: Medium-Term Optimizations

| Technique | Expected Savings | Implementation Effort |
|-----------|------------------|----------------------|
| Context compression | 26-54% memory | Medium |
| Summarization checkpoints | Variable | Low |
| Agentic plan caching | 46% cost | High |

### Priority 3: Advanced Optimizations

| Technique | Expected Savings | Implementation Effort |
|-----------|------------------|----------------------|
| Speculative decoding | 2x latency | High (infrastructure) |
| LAMaS parallel optimization | 36% latency | High |
| Programmatic tool calling | Variable | Medium (beta) |

---

## Architecture: Token-Efficient Multi-Agent Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     CACHED LAYER (Shared)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  VulnDocs   │  │    Tools    │  │  Target Contract Code   │  │
│  │  Patterns   │  │ Definitions │  │  (once per audit)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ROUTER (Haiku - Cheap)                       │
│  - Bead complexity estimation                                   │
│  - Model selection: Haiku / Sonnet / Opus                       │
│  - Plan cache lookup                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   ATTACKER      │ │   DEFENDER      │ │   VERIFIER      │
│   (Opus)        │ │   (Sonnet)      │ │   (Opus)        │
│                 │ │                 │ │                 │
│ Extended think  │ │ Fast guards     │ │ Evidence check  │
│ Plan cache hit  │ │ Pattern match   │ │ Cross-validate  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  INTEGRATOR (Sonnet)                            │
│  - Merge verdicts                                               │
│  - Summarization checkpoint (compress history)                  │
│  - Update plan cache with successful investigations             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TEST BUILDER (Sonnet)                          │
│  - Generate Foundry tests from bead evidence                    │
│  - Grounded in VulnDocs (hallucination reduction)               │
│  - Programmatic tool calling for test execution                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cost Projection

### Baseline (No Optimization)
- 10 beads × 50K tokens/bead = 500K tokens
- At $15/M input, $75/M output (Opus): ~$50/audit

### With Full Optimization Stack
- Prompt caching: 90% input reduction → $5 input
- Model routing: 60% on Sonnet → ~$15 total
- Plan cache hits: 46% reduction → ~$8 total

**Projected savings: 84% cost reduction**

---

## References

1. Anthropic. "Prompt caching." platform.claude.com/docs
2. "Token-saving updates on the Anthropic API." March 2025.
3. "Cost-Efficient Serving of LLM Agents via Test-Time Plan Caching." arXiv 2506.14852
4. "LAMaS: Latency-Aware Multi-Agent System." arXiv 2601.10560 (Jan 2026)
5. "Acon: Optimizing Context Compression for Long-horizon LLM Agents." arXiv 2510.00615
6. "DAAO: Difficulty-Aware Agent Orchestration." arXiv 2509.11079
7. "Agents At Work: The 2026 Playbook." promptengineering.org
8. "BanditSpec: Adaptive Speculative Decoding." arXiv 2505.15141
9. "Hybrid Retrieval for Hallucination Mitigation." arXiv 2504.05324

---

*Research compiled: 2026-01-21*
*For: Phase 5.2 Multi-Agent SDK Integration*
