# [P0-T0c] Context Optimization Layer - Critical Self-Improvement

**Phase**: 0 - Knowledge Foundation (Pre-requisite)
**Task ID**: P0-T0c
**Status**: NOT_STARTED
**Priority**: CRITICAL (Core thesis of BSKG 3.5)
**Estimated Effort**: 4-5 days (iterative improvement cycles)
**Actual Effort**: -
**Depends On**: P0-T0a (Cost Research), P0-T0 (Provider Abstraction)

---

## BRUTAL TRUTH: Why This Task Exists

**VKG's entire value proposition is making LLMs better at understanding Solidity business logic.**

If we feed garbage context → LLMs produce garbage results → BSKG is worthless.

If we feed too much context → LLMs hallucinate → BSKG is dangerous.

If we feed too little context → LLMs miss vulnerabilities → BSKG is useless.

**This task is about finding the GOLDILOCKS ZONE: exactly the right context that maximizes LLM precision for business logic vulnerability detection.**

---

## Critical Assessment: Current BSKG Limitations

### What We Currently Do (Honest Evaluation)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT BSKG LLM FEEDING: BRUTALLY HONEST                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  WHAT WE DO NOW:                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Build a KG with 50+ properties per function                       │   │
│  │ 2. Dump the entire KG subgraph to LLM                                │   │
│  │ 3. Ask LLM to "find vulnerabilities"                                 │   │
│  │ 4. Hope it works                                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  PROBLEMS:                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ✗ NO GUIDANCE: LLM doesn't know what to look for                    │   │
│  │ ✗ CONTEXT POLLUTION: Irrelevant properties dilute signal            │   │
│  │ ✗ NO FRAMING: LLM doesn't understand WHY properties matter          │   │
│  │ ✗ NO HYPOTHESIS: We dump data, not questions                        │   │
│  │ ✗ NO BUSINESS CONTEXT: LLM can't reason about intent                │   │
│  │ ✗ NO COMPARATIVE BASELINE: How do we know if output is good?        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  RESULT:                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ • Inconsistent results across runs                                   │   │
│  │ • High false positive rate (LLM "sees" patterns everywhere)          │   │
│  │ • Missed business logic bugs (LLM focuses on technical patterns)     │   │
│  │ • Expensive per-audit costs                                          │   │
│  │ • No measurable improvement over time                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Core Problem We Must Solve

**LLMs are good at reasoning. BSKG must provide the RIGHT inputs for that reasoning.**

Current approach: "Here's everything about this function. Find problems."

Better approach: "This function claims to be a withdrawal. Here's what safe withdrawals look like. Here's what this function actually does. Does it match?"

**The key insight: LLMs excel at COMPARISON, not DETECTION.**

---

## Research Questions (To Be Answered Through Experiments)

### RQ1: What Context Yields Best Precision?
- Does adding source code improve or hurt precision?
- Does behavioral signature alone outperform raw code?
- What is the minimum context for 90% recall?

### RQ2: How Should We Frame the Problem?
- Comparison framing vs. detection framing
- Hypothesis-driven vs. open-ended
- Step-by-step vs. holistic analysis

### RQ3: What Business Context Matters?
- Does adding spec/invariant context help?
- Does knowing "this is ERC20-like" improve analysis?
- How much domain knowledge should we inject?

### RQ4: How Do We Measure Success?
- Precision/recall on labeled corpus
- Consistency across multiple runs
- Agreement with human auditors
- Cost per true positive

---

## Executive Summary

**Purpose**: Implement the context optimization strategies identified in P0-T0a to achieve 90%+ token reduction while IMPROVING (not just maintaining) detection precision through iterative experimentation.

**Key Deliverables**:
1. Semantic Compression Engine - Converts code/KG to token-efficient format
2. Hierarchical Triage System - Routes functions to appropriate analysis levels
3. Context Slicing API - Extracts minimal context for each analysis level
4. Prompt Templates - Optimized templates for each triage level
5. **Experiment Framework** - A/B testing infrastructure for context strategies
6. **Precision Metrics** - Rigorous evaluation against labeled corpus

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTEXT OPTIMIZATION ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUT                                                                       │
│  ┌───────────────┐                                                          │
│  │ Function Node │                                                          │
│  │ + Properties  │                                                          │
│  │ + Source Code │                                                          │
│  │ + KG Subgraph │                                                          │
│  └───────┬───────┘                                                          │
│          │                                                                   │
│          ▼                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     TRIAGE CLASSIFIER                                  │  │
│  │                                                                        │  │
│  │  Rules (Tier A deterministic):                                         │  │
│  │  ├── Level 0: trivially_safe() → NO LLM                               │  │
│  │  ├── Level 1: needs_quick_scan() → 100 tokens                         │  │
│  │  ├── Level 2: needs_focused_analysis() → 500 tokens                   │  │
│  │  └── Level 3: needs_deep_analysis() → 2000 tokens                     │  │
│  │                                                                        │  │
│  └───────┬───────────┬───────────┬───────────┬───────────────────────────┘  │
│          │           │           │           │                              │
│     Level 0     Level 1     Level 2     Level 3                             │
│          │           │           │           │                              │
│          ▼           ▼           ▼           ▼                              │
│      No LLM      ┌───────────────────────────────────────────────────┐     │
│      (skip)      │           SEMANTIC COMPRESSOR                      │     │
│                  │                                                    │     │
│                  │  compress(fn, budget) → CompressedContext          │     │
│                  │                                                    │     │
│                  │  ├── Properties only (50 tokens)                   │     │
│                  │  ├── + Behavioral signature (75 tokens)            │     │
│                  │  ├── + Pattern matches (150 tokens)                │     │
│                  │  ├── + Critical code lines (300 tokens)            │     │
│                  │  └── + Full context (2000+ tokens)                 │     │
│                  │                                                    │     │
│                  └───────────────────────────────────────────────────┘     │
│                                    │                                        │
│                                    ▼                                        │
│                  ┌───────────────────────────────────────────────────┐     │
│                  │           CONTEXT SLICER                           │     │
│                  │                                                    │     │
│                  │  slice(fn, level) → ContextSlice                   │     │
│                  │                                                    │     │
│                  │  ├── Focal nodes (always included)                 │     │
│                  │  ├── Immediate neighbors (Level 1+)                │     │
│                  │  ├── Pattern context (Level 2+)                    │     │
│                  │  └── Full subgraph (Level 3 only)                  │     │
│                  │                                                    │     │
│                  └───────────────────────────────────────────────────┘     │
│                                    │                                        │
│                                    ▼                                        │
│  OUTPUT                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ OptimizedContext                                                       │  │
│  │ ├── level: int                                                        │  │
│  │ ├── compressed_repr: str                                              │  │
│  │ ├── token_count: int                                                  │  │
│  │ ├── prompt_template: str                                              │  │
│  │ └── metadata: TriageMetadata                                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Triage Classifier

### Purpose
Deterministically classify functions into analysis levels WITHOUT using LLM.

### Implementation

```python
# src/true_vkg/llm/triage.py

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

class TriageLevel(IntEnum):
    """Analysis depth levels with token budgets."""
    LEVEL_0_SKIP = 0       # No LLM needed (trivially safe)
    LEVEL_1_QUICK = 1      # Quick scan (100 tokens)
    LEVEL_2_FOCUSED = 2    # Focused analysis (500 tokens)
    LEVEL_3_DEEP = 3       # Deep adversarial (2000 tokens)

@dataclass
class TriageResult:
    """Result of triage classification."""
    level: TriageLevel
    reason: str
    token_budget: int
    confidence: float  # How confident we are in this classification

    @property
    def requires_llm(self) -> bool:
        return self.level > TriageLevel.LEVEL_0_SKIP


class TriageClassifier:
    """Deterministic function triage based on Tier A properties."""

    # Token budgets per level
    BUDGETS = {
        TriageLevel.LEVEL_0_SKIP: 0,
        TriageLevel.LEVEL_1_QUICK: 100,
        TriageLevel.LEVEL_2_FOCUSED: 500,
        TriageLevel.LEVEL_3_DEEP: 2000,
    }

    def classify(self, fn_node: dict) -> TriageResult:
        """Classify function into analysis level."""
        props = fn_node.get("properties", {})

        # Level 0: Trivially safe - no LLM needed
        if self._is_trivially_safe(props):
            return TriageResult(
                level=TriageLevel.LEVEL_0_SKIP,
                reason="Trivially safe: no external calls, no state writes, or fully guarded",
                token_budget=0,
                confidence=0.95
            )

        # Level 3: High-risk patterns - needs deep analysis
        if self._needs_deep_analysis(props):
            return TriageResult(
                level=TriageLevel.LEVEL_3_DEEP,
                reason="High-risk pattern: potential reentrancy, oracle manipulation, or access control issue",
                token_budget=2000,
                confidence=0.90
            )

        # Level 2: Pattern-matched - needs focused analysis
        if self._needs_focused_analysis(props):
            return TriageResult(
                level=TriageLevel.LEVEL_2_FOCUSED,
                reason="Pattern match: suspicious property combination",
                token_budget=500,
                confidence=0.85
            )

        # Level 1: Has potential issues - quick scan
        return TriageResult(
            level=TriageLevel.LEVEL_1_QUICK,
            reason="Potential issues: needs quick LLM verification",
            token_budget=100,
            confidence=0.80
        )

    def _is_trivially_safe(self, props: dict) -> bool:
        """Check if function is trivially safe (Level 0)."""
        # View/pure functions
        if props.get("state_mutability") in ("view", "pure"):
            return True

        # Internal/private with no external calls
        if props.get("visibility") in ("internal", "private"):
            if not props.get("has_external_calls"):
                return True

        # Fully guarded state modifications
        if props.get("has_access_gate") and props.get("has_reentrancy_guard"):
            if not props.get("has_dangerous_patterns"):
                return True

        return False

    def _needs_deep_analysis(self, props: dict) -> bool:
        """Check if function needs deep adversarial analysis (Level 3)."""
        # Reentrancy risk
        if props.get("state_write_after_external_call"):
            if not props.get("has_reentrancy_guard"):
                return True

        # Access control risk
        if props.get("writes_privileged_state"):
            if not props.get("has_access_gate"):
                return True

        # Oracle manipulation risk
        if props.get("reads_oracle_price"):
            if not props.get("has_staleness_check"):
                return True

        # MEV risk
        if props.get("swap_like"):
            if props.get("risk_missing_slippage_parameter"):
                return True

        return False

    def _needs_focused_analysis(self, props: dict) -> bool:
        """Check if function needs focused analysis (Level 2)."""
        # External calls with value
        if props.get("has_external_calls") and props.get("transfers_value"):
            return True

        # State modifications in public functions
        if props.get("visibility") in ("public", "external"):
            if props.get("writes_state") and not props.get("has_access_gate"):
                return True

        # Loop with external calls
        if props.get("external_calls_in_loop"):
            return True

        return False
```

### Triage Rules Table

| Level | Condition | Token Budget | LLM? | Example |
|-------|-----------|--------------|------|---------|
| 0 | view/pure functions | 0 | No | `function getBalance() view` |
| 0 | Internal + no external calls | 0 | No | `function _helper() internal` |
| 0 | Fully guarded | 0 | No | `function withdraw() onlyOwner nonReentrant` |
| 1 | Public state writes | 100 | Quick | `function update(x)` (no obvious guards) |
| 1 | External calls (no value) | 100 | Quick | `function sync()` |
| 2 | External calls + value | 500 | Focused | `function buy() payable` |
| 2 | Unguarded state writes | 500 | Focused | `function setFee()` |
| 2 | Loop + external | 500 | Focused | `function batchTransfer()` |
| 3 | State after external | 2000 | Deep | CEI violation |
| 3 | Unguarded privileged write | 2000 | Deep | `owner =` without gate |
| 3 | Oracle without staleness | 2000 | Deep | Price manipulation risk |
| 3 | Swap without slippage | 2000 | Deep | MEV sandwich risk |

---

## Component 2: Semantic Compressor

### Purpose
Convert function data to minimal token-efficient representation.

### Compression Format

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SEMANTIC COMPRESSION FORMAT                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TIER 1: Properties Only (~50 tokens)                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ fn:withdraw|vis:external|mut:nonpayable|                              │   │
│  │ gates:[none]|guards:[none]|                                           │   │
│  │ writes:[balances]|reads:[balances]|                                   │   │
│  │ calls:[external]|value:true                                           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  TIER 2: + Behavioral Signature (~75 tokens)                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ [TIER 1] +                                                            │   │
│  │ sig:R:bal→X:out→W:bal|                                                │   │
│  │ ops:[READS_BAL,XFER_OUT,WRITES_BAL]|                                  │   │
│  │ cei:false|reentrancy_risk:0.95                                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  TIER 3: + Pattern Matches (~150 tokens)                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ [TIER 2] +                                                            │   │
│  │ patterns:[reentrancy-classic(0.95),no-access-gate(0.7)]|              │   │
│  │ cross_graph:[ERC20.transfer:MUST_CHECK_RETURN]|                       │   │
│  │ similar_vulns:[CVE-2016-XXXXX,Parity-Wallet-Hack]                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  TIER 4: + Critical Lines (~300 tokens)                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ [TIER 3] +                                                            │   │
│  │ lines:[                                                               │   │
│  │   L45: "(bool s,) = msg.sender.call{value: amt}("")",                │   │
│  │   L46: "balances[msg.sender] -= amt"                                  │   │
│  │ ]|                                                                    │   │
│  │ annotations:[L45:external_call,L46:state_write_after_call]            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  TIER 5: Full Context (~2000+ tokens)                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ [TIER 4] +                                                            │   │
│  │ full_source: "function withdraw..."                                   │   │
│  │ subgraph: [related nodes and edges]                                   │   │
│  │ spec_context: [relevant specifications]                               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# src/true_vkg/llm/compressor.py

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional

class CompressionTier(IntEnum):
    """Compression tiers with increasing detail."""
    PROPERTIES = 1      # ~50 tokens
    BEHAVIORAL = 2      # ~75 tokens
    PATTERNS = 3        # ~150 tokens
    CRITICAL_LINES = 4  # ~300 tokens
    FULL = 5            # ~2000+ tokens


@dataclass
class CompressedContext:
    """Token-efficient function representation."""
    tier: CompressionTier
    compressed: str
    token_estimate: int
    original_tokens: int

    @property
    def compression_ratio(self) -> float:
        return self.original_tokens / max(self.token_estimate, 1)


class SemanticCompressor:
    """Compress function context to token-efficient representation."""

    def compress(
        self,
        fn_node: dict,
        budget: int,
        kg: Optional[object] = None
    ) -> CompressedContext:
        """Compress function to fit within token budget."""

        # Estimate original token count
        original = self._estimate_full_tokens(fn_node)

        # Build progressively until budget
        tier = CompressionTier.PROPERTIES
        compressed = self._tier_1_properties(fn_node)
        tokens = self._count_tokens(compressed)

        if budget >= 75 and tokens < budget:
            tier = CompressionTier.BEHAVIORAL
            compressed = self._add_tier_2_behavioral(compressed, fn_node)
            tokens = self._count_tokens(compressed)

        if budget >= 150 and tokens < budget:
            tier = CompressionTier.PATTERNS
            compressed = self._add_tier_3_patterns(compressed, fn_node, kg)
            tokens = self._count_tokens(compressed)

        if budget >= 300 and tokens < budget:
            tier = CompressionTier.CRITICAL_LINES
            compressed = self._add_tier_4_lines(compressed, fn_node)
            tokens = self._count_tokens(compressed)

        if budget >= 1000 and tokens < budget:
            tier = CompressionTier.FULL
            compressed = self._add_tier_5_full(compressed, fn_node, kg)
            tokens = self._count_tokens(compressed)

        return CompressedContext(
            tier=tier,
            compressed=compressed,
            token_estimate=tokens,
            original_tokens=original
        )

    def _tier_1_properties(self, fn_node: dict) -> str:
        """Core properties only."""
        p = fn_node.get("properties", {})
        parts = [
            f"fn:{fn_node.get('name', 'unknown')}",
            f"vis:{p.get('visibility', '?')}",
            f"mut:{p.get('state_mutability', '?')}",
            f"gates:[{','.join(p.get('modifiers', [])) or 'none'}]",
            f"writes:[{','.join(p.get('state_vars_written', [])) or 'none'}]",
            f"reads:[{','.join(p.get('state_vars_read', [])) or 'none'}]",
            f"calls:[{'external' if p.get('has_external_calls') else 'none'}]",
            f"value:{str(p.get('transfers_value', False)).lower()}"
        ]
        return "|".join(parts)

    def _add_tier_2_behavioral(self, base: str, fn_node: dict) -> str:
        """Add behavioral signature."""
        p = fn_node.get("properties", {})
        sig = p.get("behavioral_signature", "unknown")
        ops = p.get("operations", [])
        cei = p.get("follows_cei_pattern", False)
        risk = p.get("reentrancy_risk_score", 0)

        additions = [
            f"sig:{sig}",
            f"ops:[{','.join(ops)}]",
            f"cei:{str(cei).lower()}",
            f"reent_risk:{risk:.2f}"
        ]
        return base + "|" + "|".join(additions)

    def _add_tier_3_patterns(
        self, base: str, fn_node: dict, kg: Optional[object]
    ) -> str:
        """Add pattern matches."""
        patterns = fn_node.get("matched_patterns", [])
        pattern_strs = [f"{p['id']}({p.get('score', 0):.2f})" for p in patterns[:3]]

        cross_graph = fn_node.get("cross_graph_links", [])
        cross_strs = [f"{c['spec']}:{c['requirement']}" for c in cross_graph[:2]]

        similar = fn_node.get("similar_vulns", [])[:2]

        additions = [
            f"patterns:[{','.join(pattern_strs) or 'none'}]",
            f"specs:[{','.join(cross_strs) or 'none'}]",
            f"similar:[{','.join(similar) or 'none'}]"
        ]
        return base + "|" + "|".join(additions)

    def _add_tier_4_lines(self, base: str, fn_node: dict) -> str:
        """Add critical code lines."""
        critical = fn_node.get("critical_lines", [])
        line_strs = [f"L{l['line']}:{l['code'][:50]}" for l in critical[:5]]

        return base + "|lines:[" + ",".join(line_strs) + "]"

    def _add_tier_5_full(
        self, base: str, fn_node: dict, kg: Optional[object]
    ) -> str:
        """Add full source and subgraph."""
        source = fn_node.get("source_code", "")

        # Truncate if needed
        if len(source) > 3000:
            source = source[:3000] + "...[truncated]"

        return base + f"|source:{source}"

    def _count_tokens(self, text: str) -> int:
        """Estimate token count (rough heuristic)."""
        # Approximation: ~4 chars per token for code
        return len(text) // 4

    def _estimate_full_tokens(self, fn_node: dict) -> int:
        """Estimate tokens for full context."""
        source = fn_node.get("source_code", "")
        props = str(fn_node.get("properties", {}))
        return (len(source) + len(props)) // 4
```

---

## Component 3: Context Slicer

### Purpose
Extract relevant KG subgraph for each analysis level.

### Implementation

```python
# src/true_vkg/llm/slicer.py

from dataclasses import dataclass
from typing import List, Set, Optional
from .triage import TriageLevel


@dataclass
class ContextSlice:
    """Extracted subgraph for analysis."""
    focal_node: str
    included_nodes: List[str]
    included_edges: List[tuple]
    depth: int
    token_estimate: int


class ContextSlicer:
    """Extract minimal KG context for each analysis level."""

    # Depth per level
    DEPTH = {
        TriageLevel.LEVEL_0_SKIP: 0,
        TriageLevel.LEVEL_1_QUICK: 0,      # Focal only
        TriageLevel.LEVEL_2_FOCUSED: 1,    # + immediate neighbors
        TriageLevel.LEVEL_3_DEEP: 2,       # + 2-hop neighborhood
    }

    def slice(
        self,
        kg: object,
        focal_node_id: str,
        level: TriageLevel
    ) -> ContextSlice:
        """Extract context slice for given level."""
        depth = self.DEPTH[level]

        if depth == 0:
            # Focal node only
            return ContextSlice(
                focal_node=focal_node_id,
                included_nodes=[focal_node_id],
                included_edges=[],
                depth=0,
                token_estimate=50
            )

        # BFS to collect neighborhood
        nodes: Set[str] = {focal_node_id}
        edges: List[tuple] = []
        frontier = {focal_node_id}

        for d in range(depth):
            new_frontier = set()
            for node_id in frontier:
                neighbors = self._get_neighbors(kg, node_id)
                for neighbor_id, edge_data in neighbors:
                    if neighbor_id not in nodes:
                        new_frontier.add(neighbor_id)
                        nodes.add(neighbor_id)
                        edges.append((node_id, neighbor_id, edge_data))
            frontier = new_frontier

        # Estimate tokens
        token_est = len(nodes) * 50 + len(edges) * 20

        return ContextSlice(
            focal_node=focal_node_id,
            included_nodes=list(nodes),
            included_edges=edges,
            depth=depth,
            token_estimate=token_est
        )

    def _get_neighbors(
        self, kg: object, node_id: str
    ) -> List[tuple]:
        """Get neighbors of a node."""
        # Implementation depends on KG structure
        neighbors = []
        for edge in kg.get("edges", []):
            if edge.get("source") == node_id:
                neighbors.append((edge.get("target"), edge))
            elif edge.get("target") == node_id:
                neighbors.append((edge.get("source"), edge))
        return neighbors
```

---

## Component 4: Prompt Templates

### Level-Specific Templates

```python
# src/true_vkg/llm/templates.py

TEMPLATES = {
    1: """QUICK SECURITY SCAN

Function: {compressed_context}

Question: Does this function have any obvious security issues?

Reply with:
- SAFE: No issues found
- SUSPICIOUS: [one-line reason] (escalate to Level 2)
- VULNERABLE: [one-line reason] (escalate to Level 3)

Answer:""",

    2: """FOCUSED SECURITY ANALYSIS

Function: {compressed_context}

Pattern Matches: {patterns}
Spec Requirements: {specs}

Analyze:
1. Are the pattern matches true positives?
2. Are spec requirements satisfied?
3. Is there a plausible attack vector?

Reply as JSON:
{
  "verdict": "safe|suspicious|vulnerable",
  "patterns_confirmed": ["pattern_id", ...],
  "patterns_rejected": [{"id": "...", "reason": "..."}],
  "attack_vector": "description or null",
  "confidence": 0.0-1.0
}

Analysis:""",

    3: """DEEP ADVERSARIAL SECURITY ANALYSIS

Function: {compressed_context}

Source Code:
```solidity
{source_code}
```

Related Functions:
{related_functions}

Cross-Graph Context:
- Specifications: {specs}
- Known Vulnerabilities: {known_vulns}
- Attack Patterns: {attack_patterns}

You are a security auditor. Analyze this function thoroughly.

Consider:
1. Reentrancy risks (CEI pattern?)
2. Access control (who can call this?)
3. Input validation (untrusted inputs?)
4. State consistency (invariants maintained?)
5. External interactions (can they be manipulated?)

Reply as JSON:
{
  "verdict": "safe|vulnerable",
  "vulnerabilities": [
    {
      "type": "reentrancy|access_control|...",
      "severity": "critical|high|medium|low",
      "description": "...",
      "evidence": ["line:code", ...],
      "attack_scenario": "...",
      "fix_recommendation": "..."
    }
  ],
  "safe_patterns": ["description of safety measures"],
  "confidence": 0.0-1.0,
  "needs_human_review": true|false,
  "reasoning": "brief explanation"
}

Analysis:"""
}
```

---

## Integration API

```python
# src/true_vkg/llm/optimizer.py

from dataclasses import dataclass
from typing import Optional

from .triage import TriageClassifier, TriageResult
from .compressor import SemanticCompressor, CompressedContext
from .slicer import ContextSlicer, ContextSlice
from .templates import TEMPLATES


@dataclass
class OptimizedContext:
    """Complete optimized context for LLM analysis."""
    triage: TriageResult
    compressed: CompressedContext
    slice: ContextSlice
    prompt: str
    total_tokens: int


class ContextOptimizer:
    """Main entry point for context optimization."""

    def __init__(self, kg: Optional[object] = None):
        self.kg = kg
        self.triage = TriageClassifier()
        self.compressor = SemanticCompressor()
        self.slicer = ContextSlicer()

    def optimize(self, fn_node: dict) -> OptimizedContext:
        """Optimize context for a function."""

        # Step 1: Triage
        triage_result = self.triage.classify(fn_node)

        if not triage_result.requires_llm:
            return OptimizedContext(
                triage=triage_result,
                compressed=None,
                slice=None,
                prompt=None,
                total_tokens=0
            )

        # Step 2: Compress
        compressed = self.compressor.compress(
            fn_node,
            budget=triage_result.token_budget,
            kg=self.kg
        )

        # Step 3: Slice
        slice_result = self.slicer.slice(
            self.kg,
            fn_node.get("id", "unknown"),
            triage_result.level
        )

        # Step 4: Build prompt
        template = TEMPLATES.get(triage_result.level.value, TEMPLATES[2])
        prompt = template.format(
            compressed_context=compressed.compressed,
            patterns=fn_node.get("matched_patterns", []),
            specs=fn_node.get("cross_graph_links", []),
            source_code=fn_node.get("source_code", ""),
            related_functions="",  # From slice
            known_vulns=[],
            attack_patterns=[]
        )

        total_tokens = compressed.token_estimate + slice_result.token_estimate

        return OptimizedContext(
            triage=triage_result,
            compressed=compressed,
            slice=slice_result,
            prompt=prompt,
            total_tokens=total_tokens
        )

    def batch_optimize(self, fn_nodes: list) -> dict:
        """Optimize a batch of functions and return statistics."""
        results = []
        stats = {
            "level_0": 0,
            "level_1": 0,
            "level_2": 0,
            "level_3": 0,
            "total_tokens": 0,
            "saved_tokens": 0,
        }

        naive_tokens_per_fn = 6000  # Estimated naive approach

        for fn in fn_nodes:
            opt = self.optimize(fn)
            results.append(opt)

            level_key = f"level_{opt.triage.level.value}"
            stats[level_key] += 1
            stats["total_tokens"] += opt.total_tokens
            stats["saved_tokens"] += naive_tokens_per_fn - opt.total_tokens

        stats["functions_analyzed"] = len(fn_nodes)
        stats["token_reduction_pct"] = (
            stats["saved_tokens"] / (naive_tokens_per_fn * len(fn_nodes)) * 100
        )

        return {"results": results, "stats": stats}
```

---

## Success Criteria

- [ ] Triage classifier correctly categorizes 95%+ of test functions
- [ ] Level 0 correctly identifies 40%+ of trivially safe functions
- [ ] Token reduction >= 80% vs naive approach
- [ ] Precision maintained or improved vs full context
- [ ] Compression format parseable and LLM-friendly
- [ ] Prompt templates produce consistent LLM responses
- [ ] Integration API works with existing BSKG pipeline

---

## Testing Plan

### Unit Tests
```python
def test_triage_view_functions():
    """View functions should be Level 0."""
    fn = {"properties": {"state_mutability": "view"}}
    result = classifier.classify(fn)
    assert result.level == TriageLevel.LEVEL_0_SKIP

def test_triage_reentrancy_risk():
    """State write after external call should be Level 3."""
    fn = {"properties": {
        "state_write_after_external_call": True,
        "has_reentrancy_guard": False
    }}
    result = classifier.classify(fn)
    assert result.level == TriageLevel.LEVEL_3_DEEP

def test_compression_ratio():
    """Compression should achieve 5x+ ratio."""
    fn = {"source_code": "..." * 1000, "properties": {...}}
    compressed = compressor.compress(fn, budget=200)
    assert compressed.compression_ratio >= 5.0

def test_slice_depth():
    """Level 2 should include 1-hop neighbors."""
    slice_result = slicer.slice(kg, "fn_1", TriageLevel.LEVEL_2_FOCUSED)
    assert slice_result.depth == 1
    assert len(slice_result.included_nodes) > 1
```

### Integration Tests
```python
def test_batch_optimization_savings():
    """Batch optimization should achieve 80%+ savings."""
    functions = load_test_functions()  # 100 functions
    result = optimizer.batch_optimize(functions)
    assert result["stats"]["token_reduction_pct"] >= 80

def test_precision_maintained():
    """Compressed context should not reduce precision."""
    # Compare detection results: full context vs compressed
    full_results = analyze_with_full_context(test_corpus)
    compressed_results = analyze_with_compression(test_corpus)
    assert compressed_results.precision >= full_results.precision * 0.95
```

---

## Iterative Improvement Loop (CRITICAL)

**This is not a one-and-done task. It's a continuous improvement cycle.**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CRITICAL IMPROVEMENT CYCLE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                      │    │
│  │      ┌──────────┐     ┌──────────┐     ┌──────────┐                 │    │
│  │      │ BASELINE │────▶│   TEST   │────▶│ MEASURE  │                 │    │
│  │      │ Strategy │     │  Corpus  │     │ Results  │                 │    │
│  │      └──────────┘     └──────────┘     └────┬─────┘                 │    │
│  │                                              │                       │    │
│  │                                              ▼                       │    │
│  │      ┌──────────┐     ┌──────────┐     ┌──────────┐                 │    │
│  │      │  DEPLOY  │◀────│  ACCEPT  │◀────│ COMPARE  │                 │    │
│  │      │  if ✓    │     │  if ▲    │     │ vs Base  │                 │    │
│  │      └──────────┘     └──────────┘     └────┬─────┘                 │    │
│  │           │                                  │                       │    │
│  │           │                                  ▼                       │    │
│  │           │           ┌──────────┐     ┌──────────┐                 │    │
│  │           │           │ ANALYZE  │◀────│  REJECT  │                 │    │
│  │           │           │  WHY?    │     │  if ▼    │                 │    │
│  │           │           └────┬─────┘     └──────────┘                 │    │
│  │           │                │                                         │    │
│  │           │                ▼                                         │    │
│  │           │           ┌──────────┐                                   │    │
│  │           └──────────▶│   NEW    │                                   │    │
│  │                       │HYPOTHESIS│─────────────────────────▶ REPEAT │    │
│  │                       └──────────┘                                   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  MINIMUM 5 IMPROVEMENT CYCLES before declaring "good enough"                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Improvement Experiments to Run

| Cycle | Hypothesis | Test | Accept If |
|-------|-----------|------|-----------|
| 1 | Behavioral signature > raw code | Compare precision on same corpus | P(sig) > P(code) |
| 2 | Comparison framing > detection framing | A/B test prompts | P(compare) > P(detect) |
| 3 | Focused context > full context | Test at different token budgets | P(500tok) >= P(2000tok) |
| 4 | Domain hints improve business logic detection | Add ERC type hints | BL recall improves |
| 5 | Hierarchical triage maintains quality | Compare Level 1-3 escalation | No missed vulns |

### Experiment Infrastructure

```python
# src/true_vkg/llm/experiments.py

from dataclasses import dataclass
from typing import Callable, List, Dict
import json
from datetime import datetime

@dataclass
class ExperimentResult:
    """Result of a context strategy experiment."""
    experiment_id: str
    strategy_name: str
    corpus_size: int
    true_positives: int
    false_positives: int
    false_negatives: int
    total_tokens: int
    total_cost_usd: float
    run_time_seconds: float

    @property
    def precision(self) -> float:
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    @property
    def cost_per_true_positive(self) -> float:
        if self.true_positives == 0:
            return float('inf')
        return self.total_cost_usd / self.true_positives


class ExperimentRunner:
    """Run A/B experiments on context strategies."""

    def __init__(self, labeled_corpus: List[dict]):
        self.corpus = labeled_corpus
        self.results: List[ExperimentResult] = []

    def run_experiment(
        self,
        name: str,
        context_strategy: Callable,
        prompt_template: str,
        llm_client: object
    ) -> ExperimentResult:
        """Run single experiment with given strategy."""
        # Implementation
        pass

    def compare(
        self,
        baseline: str,
        candidate: str,
        significance_threshold: float = 0.05
    ) -> Dict:
        """Compare two experiments with statistical significance."""
        base_result = self._get_result(baseline)
        cand_result = self._get_result(candidate)

        return {
            "precision_diff": cand_result.precision - base_result.precision,
            "recall_diff": cand_result.recall - base_result.recall,
            "cost_diff": cand_result.cost_per_true_positive - base_result.cost_per_true_positive,
            "recommendation": "ACCEPT" if self._is_improvement(base_result, cand_result) else "REJECT",
            "reasoning": self._explain_comparison(base_result, cand_result)
        }

    def _is_improvement(self, base: ExperimentResult, cand: ExperimentResult) -> bool:
        """Candidate is better if: better F1 OR (same F1 AND lower cost)."""
        if cand.f1 > base.f1 * 1.02:  # 2% improvement threshold
            return True
        if abs(cand.f1 - base.f1) < 0.02 and cand.cost_per_true_positive < base.cost_per_true_positive * 0.9:
            return True
        return False
```

---

## Labeled Test Corpus (REQUIRED)

**We cannot improve what we cannot measure.**

### Corpus Requirements

| Category | Minimum | Purpose |
|----------|---------|---------|
| Known Vulnerabilities | 50 | True positive validation |
| Safe Contracts | 50 | False positive detection |
| Edge Cases | 20 | Robustness testing |
| Business Logic Bugs | 30 | BL detection validation |
| Renamed/Obfuscated | 20 | Name-agnostic validation |

### Corpus Sources

1. **Solodit Real Audits**: Extract vulnerable functions from real audit findings
2. **DeFi Hacks Database**: Known exploited contracts
3. **Safe Contracts**: OpenZeppelin, audited protocols
4. **Synthetic Edge Cases**: Manually crafted corner cases

### Label Schema

```json
{
  "function_id": "vault::withdraw",
  "contract_file": "tests/corpus/reentrancy_001.sol",
  "labels": {
    "vulnerable": true,
    "vuln_type": "reentrancy",
    "severity": "critical",
    "business_logic_bug": false,
    "source": "DeFi-Hack-Database",
    "reference": "https://rekt.news/..."
  },
  "expected_detection": {
    "should_detect": true,
    "minimum_confidence": 0.8,
    "key_evidence": ["state_write_after_external_call", "no_reentrancy_guard"]
  }
}
```

---

## Quality Gates (Hard Requirements)

### Cycle Gate: Must Pass Before Next Cycle

| Metric | Minimum | Target |
|--------|---------|--------|
| Precision | 70% | 90% |
| Recall | 60% | 85% |
| Consistency (3 runs) | 80% agreement | 95% agreement |
| Cost per TP | < $0.50 | < $0.10 |

### Release Gate: Must Pass Before Deployment

| Metric | Requirement |
|--------|-------------|
| Precision on vuln corpus | >= 85% |
| Recall on vuln corpus | >= 80% |
| False positive rate on safe corpus | <= 5% |
| Business logic detection | >= 50% |
| Token efficiency | >= 80% reduction vs naive |
| Consistency (5 runs) | >= 90% agreement |

---

## Failure Analysis Protocol

**When experiments fail, we must understand WHY.**

### Classification of Failures

| Failure Type | Symptoms | Investigation |
|--------------|----------|---------------|
| False Positive | Safe function flagged | What context triggered FP? |
| False Negative | Vuln function missed | What context was missing? |
| Inconsistency | Different results per run | What varies between runs? |
| Cost Explosion | Tokens >> budget | Why did triage fail? |

### Root Cause Analysis Template

```markdown
## Failure Analysis: [EXP-ID]

### Failure Description
- Type: [FP/FN/Inconsistent/Cost]
- Function: [function_id]
- Expected: [expected output]
- Actual: [actual output]

### Context Provided
[What context was fed to LLM]

### LLM Response
[Full LLM output]

### Root Cause Hypothesis
[Why did this fail?]

### Proposed Fix
[How to prevent this failure type]

### Experiment to Validate
[How to test the fix]
```

---

## Implementation Phases

### Phase 1: Baseline (Day 1)
1. Create labeled test corpus (minimum viable: 50 functions)
2. Implement naive approach (full context dump)
3. Measure baseline metrics
4. Document baseline cost and quality

### Phase 2: Semantic Compression (Day 2)
1. Implement compression engine
2. Run Experiment 1: Signature vs Code
3. Analyze results, document learnings
4. Update strategy if improvement found

### Phase 3: Triage + Framing (Day 3)
1. Implement triage classifier
2. Implement prompt templates with comparison framing
3. Run Experiment 2: Comparison vs Detection
4. Run Experiment 3: Focused vs Full context

### Phase 4: Business Context (Day 4)
1. Add domain/spec context injection
2. Run Experiment 4: Domain hints
3. Test on business logic corpus
4. Document BL detection improvements

### Phase 5: Integration + Quality Gate (Day 5)
1. Run Experiment 5: Full hierarchical triage
2. Run all quality gate checks
3. Document final strategy
4. Create deployment recommendation

---

## Success Criteria (Revised)

- [ ] Labeled test corpus created (150+ functions)
- [ ] Baseline metrics documented
- [ ] 5+ improvement experiments run
- [ ] Each experiment has documented analysis
- [ ] Final strategy achieves quality gate
- [ ] Token reduction >= 80%
- [ ] Precision >= 85% on vuln corpus
- [ ] False positive rate <= 5% on safe corpus
- [ ] Business logic detection >= 50%
- [ ] Consistency >= 90% across runs

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-03 | Created task | Claude |
| 2026-01-03 | Added critical evaluation and improvement loop | Claude |
