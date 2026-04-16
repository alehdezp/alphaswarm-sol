# [P0-T0a] LLM Cost Analysis & Context Optimization Research

**Phase**: 0 - Knowledge Foundation (Pre-requisite)
**Task ID**: P0-T0a
**Status**: NOT_STARTED
**Priority**: CRITICAL (Informs all LLM usage)
**Estimated Effort**: 2-3 days
**Actual Effort**: -

---

## Executive Summary

**The Problem**: Naive LLM usage in BSKG 3.5 could cost $15-100 per audit and DEGRADE precision due to context overload. Research shows LLMs hallucinate more with irrelevant context ("Lost in the Middle" phenomenon).

**This Task**: Research context optimization techniques, analyze VKG-specific requirements, establish baselines, and design the efficiency strategy that all LLM-using tasks will follow.

**Key Insight**: More context ≠ better results. Our goal is **Minimum Viable Context (MVC)** - the smallest context that maintains detection quality.

---

## The Cost Problem Quantified

### Naive Approach (What We're Avoiding)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NAIVE LLM USAGE - COST EXPLOSION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Per Function Analysis:                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Full source code:           ~500 tokens                               │   │
│  │ Full KG subgraph:           ~2000 tokens                              │   │
│  │ All matching patterns:      ~1000 tokens                              │   │
│  │ Cross-graph context:        ~500 tokens                               │   │
│  │ System prompt:              ~2000 tokens                              │   │
│  │ ─────────────────────────────────────────                            │   │
│  │ TOTAL PER FUNCTION:         ~6000 tokens                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Multi-Agent Pipeline (per function):                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Attacker Agent:   6000 tokens input + 1000 output = 7000              │   │
│  │ Defender Agent:   7000 tokens input + 1000 output = 8000              │   │
│  │ Verifier Agent:   8000 tokens input + 1000 output = 9000              │   │
│  │ Arbiter:          5000 tokens input + 500 output  = 5500              │   │
│  │ ─────────────────────────────────────────                            │   │
│  │ TOTAL PER FUNCTION:  ~30,000 tokens                                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Project Scale:                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Small project (50 functions):    1.5M tokens = $0.22 - $2.25          │   │
│  │ Medium project (200 functions):  6M tokens = $0.90 - $9.00            │   │
│  │ Large project (500 functions):   15M tokens = $2.25 - $22.50          │   │
│  │                                                                       │   │
│  │ With iterative reasoning (3 rounds): MULTIPLY BY 3                   │   │
│  │ With retries/hallucinations: ADD 20-50%                               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  WORST CASE: Large project = $50-100 per audit                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Quality Problem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTEXT LENGTH VS PRECISION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Research Findings:                                                          │
│                                                                              │
│  "Lost in the Middle" (Liu et al., 2023):                                   │
│  - LLMs struggle to retrieve info from middle of long contexts              │
│  - Performance drops 20-40% for mid-context information                     │
│  - Most relevant info should be at START or END                             │
│                                                                              │
│  "Needle in a Haystack" Tests:                                              │
│  - At 32K tokens: ~95% retrieval accuracy                                   │
│  - At 64K tokens: ~85% retrieval accuracy                                   │
│  - At 128K tokens: ~70% retrieval accuracy                                  │
│  - Accuracy degrades non-linearly with context length                       │
│                                                                              │
│  Implication for VKG:                                                        │
│  - Sending FULL context may actually REDUCE detection quality               │
│  - Irrelevant code/patterns dilute the signal                               │
│  - LLM attention spreads thin across unnecessary context                    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                                                                     │     │
│  │  Precision                                                          │     │
│  │     ▲                                                               │     │
│  │ 95% │    ●●●                                                        │     │
│  │ 90% │        ●●●                                                    │     │
│  │ 85% │            ●●●                                                │     │
│  │ 80% │                ●●●                                            │     │
│  │ 75% │                    ●●●                                        │     │
│  │ 70% │                        ●●●●●●                                 │     │
│  │     └─────────────────────────────────────────────▶ Context Size   │     │
│  │       1K   5K   10K   25K   50K   100K+                            │     │
│  │                                                                     │     │
│  │  SWEET SPOT: 5K-15K tokens with high-signal context                │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Research Areas

### 1. Minimum Viable Context (MVC) Analysis

**Question**: What is the MINIMUM context needed for accurate vulnerability detection?

**Hypothesis**: VKG's semantic representations (behavioral signatures, properties, operations) capture 90%+ of the signal in 10% of the tokens.

**Research Method**:
```python
# Experiment Design
def compare_context_strategies():
    test_corpus = load_vulnerable_contracts()  # Known vulns

    strategies = {
        "full_code": lambda fn: fn.source_code,  # Baseline
        "properties_only": lambda fn: fn.properties,  # 50 tokens
        "signature_props": lambda fn: f"{fn.signature}\n{fn.properties}",  # 100 tokens
        "compressed": lambda fn: semantic_compress(fn),  # 200 tokens
        "smart_slice": lambda fn: context_slice(fn, budget=500),  # 500 tokens
    }

    for strategy_name, strategy_fn in strategies.items():
        precision, recall, tokens, cost = evaluate(strategy_fn, test_corpus)
        log_results(strategy_name, precision, recall, tokens, cost)
```

**Expected Findings**:
| Strategy | Tokens/fn | Precision | Recall | Cost/100fn |
|----------|-----------|-----------|--------|------------|
| full_code | 2000 | 85% | 90% | $3.00 |
| properties_only | 50 | 70% | 60% | $0.08 |
| signature_props | 100 | 80% | 75% | $0.15 |
| compressed | 200 | 88% | 85% | $0.30 |
| smart_slice | 500 | 92% | 90% | $0.75 |

**Hypothesis**: `smart_slice` at 500 tokens achieves BETTER precision than full_code at 2000 tokens due to reduced noise.

---

### 2. Semantic Compression Protocol

**The BSKG Advantage**: We already have token-efficient representations!

**Compression Examples**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SEMANTIC COMPRESSION EXAMPLES                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EXAMPLE 1: Reentrancy-Vulnerable Function                                   │
│                                                                              │
│  BEFORE (Full Code - 150 tokens):                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ function withdraw(uint256 amount) external {                          │   │
│  │     require(balances[msg.sender] >= amount, "Insufficient balance");  │   │
│  │     (bool success, ) = msg.sender.call{value: amount}("");           │   │
│  │     require(success, "Transfer failed");                              │   │
│  │     balances[msg.sender] -= amount;                                   │   │
│  │ }                                                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  AFTER (Semantic Compression - 25 tokens):                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ fn:withdraw|vis:external|sig:R:bal→X:out→W:bal|                       │   │
│  │ ops:[READS_BAL,XFER_OUT,WRITES_BAL]|guards:[]|                       │   │
│  │ risk:reentrancy(0.95)|cei:false                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  COMPRESSION RATIO: 6x                                                       │
│  INFORMATION LOSS: ~0% for vulnerability detection                          │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  EXAMPLE 2: Safe Function (No Issues)                                        │
│                                                                              │
│  BEFORE (Full Code - 200 tokens):                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ function safeWithdraw(uint256 amount) external nonReentrant {         │   │
│  │     require(balances[msg.sender] >= amount, "Insufficient");          │   │
│  │     balances[msg.sender] -= amount;                                   │   │
│  │     (bool success, ) = msg.sender.call{value: amount}("");           │   │
│  │     require(success, "Transfer failed");                              │   │
│  │ }                                                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  AFTER (Semantic Compression - 30 tokens):                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ fn:safeWithdraw|vis:external|sig:R:bal→W:bal→X:out|                   │   │
│  │ ops:[READS_BAL,WRITES_BAL,XFER_OUT]|guards:[nonReentrant]|           │   │
│  │ risk:none|cei:true                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  KEY INSIGHT: The semantic representation makes safety OBVIOUS              │
│  - sig shows CEI pattern (W before X)                                        │
│  - guards show nonReentrant                                                  │
│  - LLM doesn't need to "discover" this - it's pre-computed                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3. Hierarchical Triage Strategy

**Concept**: Not all functions need LLM analysis. Tier A (deterministic) filters first.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HIERARCHICAL TRIAGE PYRAMID                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         ┌───────────┐                                        │
│                         │  LEVEL 3  │  Full adversarial debate               │
│                         │  10-15%   │  Only contested findings               │
│                         │ 2000 tok  │  Attacker + Defender + Arbiter        │
│                         └─────┬─────┘                                        │
│                               │                                              │
│                     ┌─────────┴─────────┐                                    │
│                     │      LEVEL 2      │  Focused analysis                  │
│                     │      20-30%       │  Pattern-matched functions         │
│                     │     500 tokens    │  Single-agent classification       │
│                     └─────────┬─────────┘                                    │
│                               │                                              │
│               ┌───────────────┴───────────────┐                              │
│               │           LEVEL 1             │  Quick LLM scan              │
│               │           30-40%              │  Property-flagged functions  │
│               │          100 tokens           │  "Needs deeper look?"        │
│               └───────────────┬───────────────┘                              │
│                               │                                              │
│       ┌───────────────────────┴───────────────────────┐                      │
│       │                   LEVEL 0                     │  NO LLM              │
│       │                   40-50%                      │  Tier A only         │
│       │                  0 tokens                     │  Trivially safe      │
│       └───────────────────────────────────────────────┘                      │
│                                                                              │
│  EXPECTED TOKEN SAVINGS:                                                     │
│  ────────────────────────────────────────────────────────────────────────   │
│  Naive: 100 functions × 2000 tokens = 200,000 tokens                        │
│  Triage: (50×0) + (35×100) + (10×500) + (5×2000) = 18,500 tokens           │
│                                                                              │
│  SAVINGS: 90%+ token reduction                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 4. Provider-Specific Research

**Using Exa Search** for current best practices:

```python
# Research queries to execute
research_queries = [
    "Anthropic Claude prompt caching implementation 2024",
    "LLM context window optimization techniques",
    "GPT-4 vs Claude context length performance comparison",
    "Gemini 2.0 Flash context handling benchmarks",
    "RAG chunking strategies for code analysis",
    "Lost in the middle LLM phenomenon mitigation",
]

# Provider-specific questions
provider_research = {
    "anthropic": [
        "Claude prompt caching discount rates",
        "Claude 3.5 Haiku vs Sonnet accuracy tradeoff",
        "Anthropic beta features context caching",
    ],
    "google": [
        "Gemini 2.0 Flash context window limits",
        "Gemini long context accuracy degradation",
        "Vertex AI batch prediction pricing",
    ],
    "openai": [
        "GPT-4o-mini vs GPT-4o accuracy comparison",
        "OpenAI batch API pricing discount",
        "OpenAI token counting optimization",
    ],
}
```

---

## Deliverables

### 1. Context Optimization Strategy Document

```markdown
# BSKG 3.5 Context Optimization Strategy

## Principles
1. Semantic representation > raw code
2. Tier A filters before Tier B
3. Progressive disclosure (start small, expand if needed)
4. Cache aggressively

## Token Budgets
| Operation | Budget | Justification |
|-----------|--------|---------------|
| Triage (Level 0) | 0 | Pure Tier A |
| Quick scan (Level 1) | 100 | Properties + signature |
| Focused analysis (Level 2) | 500 | + pattern context |
| Deep dive (Level 3) | 2000 | + full adversarial |

## Compression Protocol
[Detailed specification of how to compress context]

## Caching Strategy
[What to cache, TTL, invalidation rules]
```

### 2. Baseline Metrics

```json
{
  "baseline_date": "2026-01-XX",
  "test_corpus": "50 contracts, 200 functions",
  "measurements": {
    "naive_approach": {
      "tokens_per_function": 6000,
      "cost_per_100_functions_usd": 15.00,
      "latency_per_function_ms": 3500,
      "precision": 0.82,
      "recall": 0.78
    },
    "optimized_approach": {
      "tokens_per_function": 450,
      "cost_per_100_functions_usd": 1.20,
      "latency_per_function_ms": 800,
      "precision": 0.91,
      "recall": 0.85
    }
  },
  "improvement": {
    "token_reduction": "92%",
    "cost_reduction": "92%",
    "latency_reduction": "77%",
    "precision_improvement": "+9%"
  }
}
```

### 3. Research Findings Summary

Document key findings from:
- Academic papers on context optimization
- Provider documentation
- Empirical experiments
- Community best practices

---

## Success Criteria

- [ ] Established baseline token usage per operation
- [ ] Documented cost projections for different project sizes
- [ ] Identified optimal context strategies for VKG
- [ ] Created compression protocol specification
- [ ] Researched provider-specific optimizations
- [ ] Defined token budgets per analysis level
- [ ] Validated hypothesis: compressed > full for precision

---

## Implementation Plan

### Day 1: Research & Literature Review
1. Use Exa Search to gather current best practices
2. Review academic papers on context optimization
3. Document provider-specific features (caching, batching)
4. Create research summary

### Day 2: Baseline Measurement
1. Create test corpus (mix of safe/vulnerable contracts)
2. Measure naive approach: tokens, cost, precision
3. Implement basic compression
4. Compare compressed vs full context

### Day 3: Strategy Design
1. Design hierarchical triage levels
2. Define token budgets per level
3. Specify compression protocol
4. Create optimization strategy document
5. Update P0-T0b with efficiency requirements

---

## Integration with Other Tasks

**Outputs used by:**
- **P0-T0** (Provider Abstraction): Token budgets, caching strategy
- **P0-T0c** (Context Optimization): Compression protocol, triage levels
- **P0-T0d** (Efficiency Metrics): Baseline measurements, targets
- **P2-T1** (Agent Router): Context slicing strategy
- **All LLM tasks**: Token budget constraints

---

## Self-Improvement Loop

This task establishes the FEEDBACK MECHANISM for continuous optimization:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SELF-IMPROVEMENT LOOP                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│     ┌──────────────┐                                                         │
│     │   Analyze    │ ◄───────────────────────────────────────┐              │
│     │  (This Task) │                                          │              │
│     └──────┬───────┘                                          │              │
│            │                                                   │              │
│            ▼                                                   │              │
│     ┌──────────────┐                                          │              │
│     │  Implement   │  Apply strategies to LLM tasks           │              │
│     │   (P0-T0c)   │                                          │              │
│     └──────┬───────┘                                          │              │
│            │                                                   │              │
│            ▼                                                   │              │
│     ┌──────────────┐                                          │              │
│     │   Measure    │  Collect: tokens, cost, precision        │              │
│     │   (P0-T0d)   │                                          │              │
│     └──────┬───────┘                                          │              │
│            │                                                   │              │
│            ▼                                                   │              │
│     ┌──────────────┐                                          │              │
│     │    Adjust    │  Tune: budgets, thresholds, strategies   │              │
│     │  (Feedback)  │ ─────────────────────────────────────────┘              │
│     └──────────────┘                                                         │
│                                                                              │
│  Frequency: After each audit, aggregate weekly                              │
│  Metrics tracked: tokens/fn, cost/fn, precision, recall, latency            │
│  Adjustment triggers: >20% deviation from targets                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-03 | Created research task | Claude |
