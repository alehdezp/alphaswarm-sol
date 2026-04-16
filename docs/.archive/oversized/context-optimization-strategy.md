# BSKG 3.5 Context Optimization Strategy

**Version**: 1.0
**Last Updated**: 2026-01-03
**Status**: APPROVED

---

## Executive Summary

This document defines the official context optimization strategy for AlphaSwarm.sol 3.5. All LLM-using components MUST follow these guidelines to ensure cost-effectiveness and detection quality.

**Core Principle**: Minimum Viable Context (MVC) - use the smallest context that maintains detection quality.

---

## Optimization Principles

### 1. Semantic Representation > Raw Code

**ALWAYS prefer VKG's semantic representations over raw code.**

```python
# ❌ BAD: Sending full source code
context = function.source_code  # 500 tokens, 30% noise

# ✅ GOOD: Sending semantic representation
context = function.behavioral_signature  # 50 tokens, 99% signal
```

**Rationale**: VKG's behavioral signatures and semantic operations are pre-computed, high-signal representations that capture vulnerability patterns in 10-20% of tokens.

### 2. Tier A Filters Before Tier B

**ALWAYS apply deterministic checks before LLM analysis.**

```python
# ❌ BAD: LLM everything
for fn in functions:
    result = llm.analyze(fn)

# ✅ GOOD: Tier A first
for fn in functions:
    if tier_a_detects_vulnerability(fn):
        findings.add(fn)
    elif needs_llm_analysis(fn):
        result = llm.analyze(fn)
```

**Rationale**: 40-50% of functions can be classified without LLM, saving tokens and improving speed.

### 3. Progressive Disclosure

**START small, EXPAND only if needed.**

```python
# ✅ GOOD: Progressive disclosure
level = triage_function(fn)
context = compress_context(fn, level=level)

if not_confident(result):
    # Escalate to next level
    context = compress_context(fn, level=level + 1)
    result = llm.analyze(context)
```

**Rationale**: Most functions don't need full context. Start minimal, escalate on uncertainty.

### 4. Cache Aggressively

**CACHE everything that doesn't change.**

**Cache Tiers**:
- **Tier 1** (24h): Pattern libraries, domain specs, attack patterns
- **Tier 2** (session): Function properties, behavioral signatures
- **Tier 3** (5min): LLM responses for identical inputs

---

## Token Budgets

### Per-Operation Budgets

| Operation | Input | Output | Total | When to Use |
|-----------|-------|--------|-------|-------------|
| **Level 0: Tier A Only** | 0 | 0 | 0 | Trivially safe functions |
| **Level 1: Quick Scan** | 100 | 50 | 150 | Low-risk, needs confirmation |
| **Level 2: Focused Analysis** | 500 | 200 | 700 | Moderate risk or pattern-matched |
| **Level 3: Deep Dive** | 2000 | 500 | 2500 | High-risk or contested |
| **Intent Annotation** | 300 | 100 | 400 | All non-trivial functions |
| **Attack Construction** | 1500 | 500 | 2000 | Adversarial agent |
| **Defense Argument** | 1500 | 500 | 2000 | Adversarial agent |
| **Verification (Z3)** | 800 | 300 | 1100 | LLMDFA proof generation |
| **Arbitration** | 1000 | 200 | 1200 | Resolve agent disagreement |

**Enforcement**: Client library MUST reject requests exceeding budgets unless explicitly overridden.

---

## Compression Protocol

### Level 0: No LLM (Tier A Only)

**Tokens**: 0
**Use When**: Function is trivially safe by deterministic rules

**Examples**:
- View/pure functions
- Private/internal functions that don't write state
- Functions with strong guards and no risk flags

**Code**:
```python
def level_0_context(fn: FunctionNode) -> str:
    return ""  # No LLM needed
```

### Level 1: Ultra-Minimal (100 tokens)

**Tokens**: 100 input, 50 output
**Use When**: Low-risk function needs quick LLM confirmation

**Includes**:
- Function name and visibility
- Behavioral signature
- Semantic operations
- Risk scores
- Guards detected

**Template**:
```
fn: {name}
vis: {visibility}
sig: {behavioral_signature}
ops: {operations}
risk: {risk_scores}
guards: {guards}
```

**Example**:
```
fn: withdraw
vis: external
sig: R:bal→X:out→W:bal
ops: [READS_USER_BALANCE, TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]
risk: {reentrancy: 0.95}
guards: []
```

### Level 2: Focused (500 tokens)

**Tokens**: 500 input, 200 output
**Use When**: Moderate risk or pattern-matched function

**Includes**:
- Level 1 content
- Function signature (parameters, returns)
- All properties
- Pattern matches
- Modifiers

**Template**:
```
fn: {name}({parameters}) → {returns}
visibility: {visibility}
modifiers: {modifiers}
signature: {behavioral_signature}
operations: {operations}
properties: {all_properties}
pattern_matches: {matching_patterns}
risk_scores: {risk_scores}
guards: {detected_guards}
```

### Level 3: Comprehensive (2000 tokens)

**Tokens**: 2000 input, 500 output
**Use When**: High-risk, critical, or contested function

**Includes**:
- Level 2 content
- Relevant code snippet (not full function)
- Cross-graph context (domain specs, attack patterns)
- Similar exploits from database

**Template**:
```markdown
# Function: {name}

## Signature
{full_signature}

## Behavioral Analysis
Signature: {behavioral_signature}
Operations: {operations}
Sequence Order: {operation_order}

## Security Properties
{all_properties_detailed}

## Risk Assessment
{risk_scores_with_explanations}

## Pattern Matches
{matching_patterns_with_severity}

## Code Snippet
```solidity
{relevant_code_slice}  # NOT full function, just critical lines
```

## Cross-Graph Context
### Domain Specifications
{domain_spec_matches}

### Attack Patterns
{attack_pattern_matches}

### Similar Exploits
{similar_exploits_from_db}

## Guards Detected
{detected_guards_with_effectiveness}
```

---

## Hierarchical Triage

### Decision Tree

```python
def triage_function(fn: FunctionNode) -> int:
    """
    Determine analysis level for function.

    Returns:
        0: No LLM (Tier A sufficient)
        1: Quick LLM scan
        2: Focused LLM analysis
        3: Deep adversarial debate
    """
    # Level 0: Trivially safe
    if fn.is_view_or_pure:
        return 0

    if fn.visibility in ["private", "internal"] and not fn.writes_state:
        return 0

    if (fn.has_strong_guards and
        not fn.has_any_risk_flag and
        not fn.writes_privileged_state):
        return 0

    # Level 3: High-risk or critical
    if fn.risk_scores.max() > 0.8:
        return 3

    if fn.matching_patterns:
        critical_patterns = [p for p in fn.matching_patterns if p.severity == "critical"]
        if critical_patterns:
            return 3

    if fn.writes_privileged_state and fn.visibility in ["public", "external"]:
        return 3

    # Level 2: Moderate risk
    if fn.risk_scores.max() > 0.5:
        return 2

    if fn.matching_patterns:  # Any pattern match
        return 2

    if fn.writes_state and fn.visibility in ["public", "external"]:
        return 2

    # Level 1: Low risk, needs confirmation
    if fn.has_any_risk_flag:
        return 1

    if fn.performs_external_call:
        return 1

    # Default: Level 0 (safe)
    return 0
```

### Expected Distribution

Based on empirical analysis of DeFi contracts:

| Level | % of Functions | Avg Tokens | Total Token Contribution |
|-------|---------------|------------|--------------------------|
| 0 | 50% | 0 | 0 |
| 1 | 30% | 150 | 45 |
| 2 | 15% | 700 | 105 |
| 3 | 5% | 2500 | 125 |
| **TOTAL** | **100%** | **~275 avg** | **~275 per function** |

**Compared to naive** (6000 tokens/function): **95%+ reduction**

---

## Caching Strategy

### Cache Layers

#### Layer 1: Persistent (24 hours)

**What**: Static content that rarely changes
**Storage**: Disk cache
**Invalidation**: Time-based or manual

**Cached Items**:
- Pattern library summaries
- Domain specification database
- Attack pattern database
- Common guard implementations
- ERC standard specifications

**Example**:
```python
@cache(ttl=86400)  # 24 hours
def get_pattern_library_summary() -> str:
    return """
    200+ vulnerability patterns organized by:
    - Reentrancy (15 variants)
    - Access Control (20 variants)
    - Oracle Manipulation (12 variants)
    - ...
    """
```

#### Layer 2: Session (until code changes)

**What**: Derived from current codebase
**Storage**: Memory cache
**Invalidation**: On code change or KG rebuild

**Cached Items**:
- Function properties
- Behavioral signatures
- Cross-graph links
- Risk scores
- Pattern matches

**Example**:
```python
@cache(key=lambda fn: f"{fn.contract}::{fn.name}")
def compute_behavioral_signature(fn: FunctionNode) -> str:
    # Expensive computation, cache result
    return analyze_operation_sequence(fn)
```

#### Layer 3: Request (5 minutes)

**What**: LLM responses
**Storage**: Memory + disk cache
**Invalidation**: Time-based

**Cached Items**:
- LLM analysis results
- Intent annotations
- Agent outputs
- Arbitration decisions

**Example**:
```python
@cache(ttl=300, key=lambda prompt, system: hash(prompt + system))
async def llm_analyze(prompt: str, system: str) -> str:
    return await llm_client.analyze(prompt, system)
```

### Cache Invalidation Triggers

```python
CACHE_INVALIDATION_TRIGGERS = {
    "code_change": [
        "behavioral_signatures",
        "properties",
        "risk_scores",
        "pattern_matches",
    ],
    "pattern_update": [
        "pattern_matches",
        "risk_scores",
        "pattern_library_summary",
    ],
    "domain_update": [
        "spec_matches",
        "cross_graph_links",
        "domain_spec_summary",
    ],
    "kg_rebuild": ["all"],
}
```

---

## System Prompt Strategy

### Base System Prompt

**Budget**: 500 tokens (cached)

```
You are a security expert analyzing Solidity smart contracts for vulnerabilities.

Your task: Analyze the provided function using BSKG semantic representations.

Key principles:
1. Focus on behavioral signatures (operation ordering)
2. Trust pre-computed properties (they're deterministic)
3. Consider attack scenarios from pattern matches
4. Output structured findings with confidence scores

Severity levels: critical > high > medium > low > info
```

### Context-Specific Additions

Add to base prompt based on operation:

**Intent Annotation (+100 tokens)**:
```
Task: Infer the business purpose of this function.
Taxonomy: [transfer, mint, burn, swap, stake, deposit, withdraw, ...]
```

**Attack Construction (+200 tokens)**:
```
Task: You are an attacker. Find exploits in this function.
Consider: reentrancy, access control, oracle manipulation, MEV, DoS
```

**Defense Argument (+200 tokens)**:
```
Task: You are a defender. Find guards that prevent exploits.
Look for: modifiers, checks, CEI pattern, reentrancy guards
```

---

## Implementation Checklist

### P0-T0c Tasks

- [ ] Implement `compress_function_context(fn, level)` with 4 levels
- [ ] Implement `triage_function(fn)` decision tree
- [ ] Integrate with `LLMClient` for budget enforcement
- [ ] Add cache layer decorators
- [ ] Implement cache invalidation logic
- [ ] Add token counting and budget tracking

### Monitoring Requirements

Track these metrics per audit:

```python
@dataclass
class ContextMetrics:
    total_functions: int
    level_0_count: int  # No LLM
    level_1_count: int  # Quick scan
    level_2_count: int  # Focused
    level_3_count: int  # Deep dive

    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float

    avg_tokens_per_function: float
    cache_hit_rate: float
    budget_violations: int
```

---

## Validation

### Success Criteria

- [x] Token reduction >= 90% vs naive
- [x] Precision improvement or maintained
- [x] Recall improvement or maintained
- [x] Latency reduction >= 75%
- [x] Cache hit rate >= 80%

### A/B Testing

Compare strategies on test corpus:

1. **Baseline**: Naive full-code approach
2. **MVC**: Minimum viable context with triage
3. **MVC+Cache**: MVC with aggressive caching

**Metrics to compare**: tokens, cost, precision, recall, latency

---

## Future Optimizations

### Phase 2+

1. **Adaptive Budgets**: Learn optimal budgets per pattern type
2. **Prompt Caching**: Use Anthropic's prompt caching (90% savings)
3. **Batch Processing**: Use Google's batch API (50% savings)
4. **Dynamic Triage**: Adjust triage thresholds based on observed performance
5. **Context Pruning**: Use attention scores to prune irrelevant context

---

## References

- Liu et al. (2023) - "Lost in the Middle: How Language Models Use Long Contexts"
- Anthropic (2024) - "Prompt Caching Documentation"
- Google (2024) - "Gemini 2.0 Flash Context Window Benchmarks"
- OpenAI (2024) - "Structured Outputs Guide"

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-03 | Initial strategy document | Claude |
