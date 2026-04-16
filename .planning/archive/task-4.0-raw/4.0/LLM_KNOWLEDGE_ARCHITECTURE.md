# LLM Knowledge Architecture for AlphaSwarm.sol

**Version:** 1.0
**Date:** 2026-01-08
**Status:** Architecture Design

---

## Executive Summary

This document describes the enhanced LLM knowledge architecture for AlphaSwarm.sol, addressing three key requirements:

1. **Prompt Caching for LLM Agents** - Efficient caching of static vulnerability knowledge
2. **Granular Vulnerability Knowledge Docs** - Per-category knowledge grimoires
3. **LLM-Only Investigation Patterns** - Reasoning-based patterns using LSP, Graph, and PPR

The architecture enables LLM agents to perform intelligent security analysis with rich context while minimizing token costs through effective caching.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LLM KNOWLEDGE ARCHITECTURE                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    LAYER 1: KNOWLEDGE BASE                               ││
│  │                    (Cacheable Static Knowledge)                          ││
│  │                                                                          ││
│  │  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────┐  ││
│  │  │ Vulnerability      │  │ Token/Library      │  │ Protocol          │  ││
│  │  │ Category Grimoires │  │ Pitfall Guides     │  │ Primitive Docs    │  ││
│  │  │                    │  │                    │  │                   │  ││
│  │  │ 10 categories:     │  │ - ERC20 variants   │  │ - AMM mechanics   │  ││
│  │  │ - Reentrancy       │  │ - ERC721/1155      │  │ - Lending pools   │  ││
│  │  │ - Access Control   │  │ - OpenZeppelin     │  │ - Staking         │  ││
│  │  │ - Oracle           │  │ - Uniswap V2/V3    │  │ - Governance      │  ││
│  │  │ - DoS              │  │ - AAVE/Compound    │  │ - Bridges         │  ││
│  │  │ - MEV              │  │ - Fee-on-transfer  │  │ - Vaults          │  ││
│  │  │ - Upgrade          │  │ - Rebasing tokens  │  │                   │  ││
│  │  │ - Flash Loan       │  │                    │  │                   │  ││
│  │  │ - Token            │  │                    │  │                   │  ││
│  │  │ - Governance       │  │                    │  │                   │  ││
│  │  │ - Cryptographic    │  │                    │  │                   │  ││
│  │  └────────────────────┘  └────────────────────┘  └───────────────────┘  ││
│  │                                                                          ││
│  │  Token Cost: ~10,000-15,000 tokens (ONE-TIME per session via caching)   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    LAYER 2: PATTERN CONTEXT                              ││
│  │                    (Per-Finding Dynamic Context)                         ││
│  │                                                                          ││
│  │  ┌───────────────────────────────────────────────────────────────────┐  ││
│  │  │ Pattern-Specific Knowledge Block                                   │  ││
│  │  │                                                                    │  ││
│  │  │ - All attack scenarios for this pattern                           │  ││
│  │  │ - False positive indicators (when NOT vulnerable)                 │  ││
│  │  │ - Edge cases that change severity                                 │  ││
│  │  │ - Historical exploits (The DAO, Cream, Curve, etc.)              │  ││
│  │  │ - Code examples (vulnerable vs safe)                              │  ││
│  │  │ - Verification checklist                                          │  ││
│  │  └───────────────────────────────────────────────────────────────────┘  ││
│  │                                                                          ││
│  │  Token Cost: ~1,000-2,000 tokens per finding                            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    LAYER 3: CODE CONTEXT                                 ││
│  │                    (Graph-Sliced Code Evidence)                          ││
│  │                                                                          ││
│  │  ┌───────────────────────────────────────────────────────────────────┐  ││
│  │  │ PPR-Optimized Code Context                                         │  ││
│  │  │                                                                    │  ││
│  │  │ - Function source code                                             │  ││
│  │  │ - Category-relevant graph properties only                          │  ││
│  │  │ - Caller/callee context (PPR-expanded)                            │  ││
│  │  │ - State variable definitions                                       │  ││
│  │  │ - Relevant modifiers and guards                                    │  ││
│  │  └───────────────────────────────────────────────────────────────────┘  ││
│  │                                                                          ││
│  │  Token Cost: ~500-1,500 tokens per finding (via PPR slicing)            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  TOTAL PER-FINDING COST: ~1,500-3,500 tokens (vs ~15,000 without caching)   │
│  ESTIMATED SAVINGS: 70-85% token reduction                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Prompt Caching System (Task 11.16)

**Purpose:** Cache stable knowledge blocks to reduce repeated token costs.

**Caching Strategy:**
```python
# Anthropic API format with cache control
{
    "system": [
        {
            "type": "text",
            "text": VULNERABILITY_KNOWLEDGE_BLOCK,  # ~10k tokens
            "cache_control": {"type": "ephemeral"}   # CACHED
        }
    ],
    "messages": [
        {
            "role": "user",
            "content": PATTERN_CONTEXT + CODE_CONTEXT  # ~2-3k tokens
        }
    ]
}
```

**Cost Analysis:**
| Scenario | Tokens | Cost @$3/1M |
|----------|--------|-------------|
| No caching (10 findings) | 150,000 | $0.45 |
| With caching (10 findings) | 40,000 | $0.12 + $0.03 cache = $0.15 |
| **Savings** | 110,000 | **$0.30 (67%)** |

### 2. Vulnerability Knowledge Grimoires (Task 11.16)

**Purpose:** Per-category expert knowledge documents for LLM context.

**Location:** `knowledge/grimoires/`

**Structure per Grimoire:**
```markdown
# [Category] Vulnerability Knowledge Grimoire

## Overview
Brief description and why it matters.

## Business Impact
- Historical losses
- Target protocols
- Severity range

## Attack Scenarios
### Scenario 1: [Name]
- Conditions
- Mechanism
- Example code
- Real-world instance

## False Positive Indicators
When code LOOKS vulnerable but ISN'T.

## Edge Cases
Special situations that change severity.

## Library/Token-Specific Pitfalls
- OpenZeppelin quirks
- Uniswap integration issues
- Token standard edge cases

## Safe Patterns
Correct implementation examples.

## Verification Checklist
Step-by-step verification process.
```

**Categories Covered:**
1. Reentrancy
2. Access Control
3. Oracle Manipulation
4. Flash Loan
5. MEV
6. DoS
7. Upgrade Safety
8. Token Integration
9. Cryptographic
10. Governance

### 3. LLM Investigation Patterns (Task 13.11)

**Purpose:** Patterns designed for LLM reasoning, not deterministic matching.

**Key Difference from Tier A Patterns:**
| Tier A Patterns | LLM Investigation Patterns |
|-----------------|---------------------------|
| Deterministic | Reasoning-based |
| Property checks | Tool-assisted exploration |
| Same code = same result | LLM interprets findings |
| Fast execution | Multi-step investigation |

**Investigation Actions:**
| Action | Tool | Purpose |
|--------|------|---------|
| `explore_graph` | Graph Query Engine | Find related functions |
| `lsp_references` | LSP findReferences | Find all usages |
| `lsp_call_hierarchy` | LSP incomingCalls | Trace call paths |
| `ppr_expand` | PPR Algorithm | Expand context |
| `read_code` | Read Tool | Get source code |
| `reason` | LLM Provider | Logical reasoning |

**Example Investigation Pattern:**
```yaml
id: inv-bl-001
name: Accounting Invariant Violation
type: investigation
category: business-logic

trigger:
  graph_signals:
    - property: writes_user_balance
    - property: writes_critical_state

investigation:
  hypothesis: "Balance tracking may not match actual holdings"

  steps:
    - id: 1
      action: explore_graph
      description: "Find all balance-modifying functions"
      graph_query: "FIND functions WHERE modifies balance"

    - id: 2
      action: lsp_references
      target: "balances"
      description: "Find all balance reads"

    - id: 3
      action: reason
      prompt: |
        Analyzing invariant: sum(balances) == totalSupply
        Step 1 results: {step_1_results}
        Step 2 results: {step_2_results}
        Is invariant preserved in all paths?

  verdict_criteria:
    vulnerable: "Clear path to break invariant"
    safe: "Invariant preserved in all paths"
```

---

## Integration Points

### Phase 9 Integration (Context Optimization)
- PPR algorithm expands code context
- Category-aware graph slicing (8-12 properties vs 50+)
- Property sets defined per vulnerability category

### Phase 11 Integration (LLM Integration)
- Knowledge blocks cached in system prompt
- Multi-provider support (Anthropic, OpenAI, etc.)
- Cost tracking per finding

### Phase 12 Integration (Agent SDK)
- Subagents receive knowledge-enriched Beads
- Parallel investigation execution
- SDK-based tool invocation

### Phase 13 Integration (Grimoires)
- Grimoires use knowledge blocks
- Investigation patterns as grimoire steps
- Skills invoke investigation patterns

---

## Implementation Roadmap

### Phase 1: Knowledge Foundation (11.16)
1. Create KnowledgeManager class
2. Define knowledge grimoire markdown schema
3. Implement 10 vulnerability category grimoires
4. Build CachedPromptBuilder

### Phase 2: Investigation Patterns (13.11)
1. Define investigation pattern YAML schema
2. Implement InvestigationExecutor
3. Create 6 initial investigation patterns:
   - INV-BL-001: Accounting Invariant
   - INV-BL-002: State Machine Violation
   - INV-CC-001: Privilege Escalation
   - INV-CC-002: Cross-Contract Reentrancy
   - INV-ECON-001: Price Manipulation
   - INV-CFG-001: Dangerous Configuration
4. Integrate with LSP, Graph, PPR

### Phase 3: Integration & Validation
1. Integrate with Tier B workflow
2. Measure token savings
3. Validate accuracy improvement
4. Document lessons learned

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Token Cost Reduction | >= 70% | Compare with/without caching |
| Knowledge Coverage | 10 categories | Count of grimoire files |
| Investigation Accuracy | >= 80% | Test on labeled findings |
| Cache Hit Rate | >= 80% | Track cache usage |
| LLM False Positive Reduction | >= 30% | Compare Tier A vs Tier A+B+Investigation |

---

## Files to Create

### Task 11.16: Prompt Caching & Knowledge System
| File | Description |
|------|-------------|
| `src/true_vkg/llm/knowledge.py` | Knowledge manager |
| `src/true_vkg/llm/cached_prompt.py` | Cached prompt builder |
| `knowledge/grimoires/*.md` | 10 knowledge grimoires |
| `tests/test_knowledge_manager.py` | Tests |

### Task 13.11: LLM Investigation Patterns
| File | Description |
|------|-------------|
| `src/true_vkg/investigation/executor.py` | Pattern executor |
| `src/true_vkg/investigation/actions.py` | Action implementations |
| `patterns/investigation/*.yaml` | Investigation patterns |
| `tests/test_investigation_executor.py` | Tests |

---

## References

- Task 11.16: `task/4.0/phases/phase-11/tasks/11.16-prompt-caching-knowledge-system.md`
- Task 13.11: `task/4.0/phases/phase-13/tasks/13.11-llm-investigation-patterns.md`
- Phase 9 (PPR): `task/4.0/phases/phase-9/TRACKER.md`
- Phase 11 (LLM): `task/4.0/phases/phase-11/TRACKER.md`
- Phase 13 (Grimoires): `task/4.0/phases/phase-13/TRACKER.md`

---

*LLM Knowledge Architecture | Version 1.0 | 2026-01-08*
