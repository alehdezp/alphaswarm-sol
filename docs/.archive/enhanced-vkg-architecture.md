# Enhanced BSKG Architecture: 12-Tier Design

## Document Purpose

This document consolidates the enhanced BSKG architecture, combining:
- Original Semantic BSKG Implementation Plan (Phases 0-12)
- 12-Tier Enhancement Ideas (Edge Intelligence through MVP Roadmap)
- Multi-Agent Verification System
- Attack Path Synthesis

**Goal:** Create the most powerful, LLM-ready, low false-positive Solidity security analysis system.

---

## Executive Summary

### The Problem
Current static analysis tools suffer from:
- **45%+ false positive rates** (drowns real issues in noise)
- **Name-dependent detection** (breaks on renamed variables)
- **Flat graph structure** (loses semantic relationships)
- **Token-heavy LLM context** (expensive, loses focus)

### The Solution
A multi-tier BSKG that:
- Uses **intelligent edges** with risk scores and pattern tags
- Classifies nodes into **semantic hierarchies** (Guardian, Checkpoint, StateAnchor)
- Extracts **minimal subgraphs** for LLM analysis (10x token reduction)
- Runs **multi-agent verification** for consensus-based findings (<10% FP rate)
- Synthesizes **concrete attack paths** for actionable findings

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           ENHANCED BSKG ARCHITECTURE                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      TIER 0: FOUNDATION LAYER                           │ │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────────────┐│ │
│  │  │   Slither   │──▶│    AST      │──▶│        Base BSKG                 ││ │
│  │  │   Parser    │   │  Traversal  │   │  (Nodes, Properties, Edges)     ││ │
│  │  └─────────────┘   └─────────────┘   └─────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 1: INTELLIGENT EDGE LAYER                         │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Rich Edges with:                                                 │  │ │
│  │  │  • risk_score (0-10)                                              │  │ │
│  │  │  • pattern_tags ["reentrancy", "unchecked_call"]                  │  │ │
│  │  │  • execution_context ("normal", "delegatecall", "staticcall")     │  │ │
│  │  │  • taint_source, taint_confidence                                 │  │ │
│  │  │  • happens_before, happens_after (temporal ordering)              │  │ │
│  │  │  • guards_at_source, guards_bypassed                              │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Meta-Edges:                                                      │  │ │
│  │  │  • SIMILAR_TO (subgraph isomorphism)                              │  │ │
│  │  │  • BUGGY_PATTERN_MATCH (known vulnerability link)                 │  │ │
│  │  │  • REFACTOR_CANDIDATE (optimization opportunity)                  │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 2: SEMANTIC OPERATIONS LAYER                      │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  20 Semantic Operations:                                          │  │ │
│  │  │                                                                   │  │ │
│  │  │  Value Movement:                                                  │  │ │
│  │  │  • TRANSFERS_VALUE_OUT, RECEIVES_VALUE_IN                         │  │ │
│  │  │  • READS_USER_BALANCE, WRITES_USER_BALANCE                        │  │ │
│  │  │                                                                   │  │ │
│  │  │  Access Control:                                                  │  │ │
│  │  │  • CHECKS_PERMISSION, MODIFIES_OWNER, MODIFIES_ROLES              │  │ │
│  │  │                                                                   │  │ │
│  │  │  External Interaction:                                            │  │ │
│  │  │  • CALLS_EXTERNAL, CALLS_UNTRUSTED, READS_EXTERNAL_VALUE          │  │ │
│  │  │                                                                   │  │ │
│  │  │  State Management:                                                │  │ │
│  │  │  • MODIFIES_CRITICAL_STATE, INITIALIZES_STATE, READS_ORACLE       │  │ │
│  │  │                                                                   │  │ │
│  │  │  Control Flow:                                                    │  │ │
│  │  │  • LOOPS_OVER_ARRAY, USES_TIMESTAMP, USES_BLOCK_DATA              │  │ │
│  │  │                                                                   │  │ │
│  │  │  Arithmetic & Validation:                                         │  │ │
│  │  │  • PERFORMS_DIVISION, PERFORMS_MULTIPLICATION                     │  │ │
│  │  │  • VALIDATES_INPUT, EMITS_EVENT                                   │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Operation Sequencing:                                            │  │ │
│  │  │  • CFG traversal for temporal ordering                            │  │ │
│  │  │  • Behavioral signatures: "R:bal→X:out→W:bal" (vulnerable)        │  │ │
│  │  │                          "R:bal→W:bal→X:out" (safe)               │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 3: NODE CLASSIFICATION LAYER                      │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Hierarchical Node Taxonomy:                                      │  │ │
│  │  │                                                                   │  │ │
│  │  │  Function Types:                                                  │  │ │
│  │  │  • Guardian: Access control checks (require, modifier)            │  │ │
│  │  │  • Checkpoint: State-changing functions                           │  │ │
│  │  │  • EscapeHatch: Emergency functions (pause, freeze)               │  │ │
│  │  │  • EntryPoint: Public/external with state effects                 │  │ │
│  │  │                                                                   │  │ │
│  │  │  StateVariable Types:                                             │  │ │
│  │  │  • StateAnchor: Used in access control guards                     │  │ │
│  │  │  • CriticalState: User balances, positions                        │  │ │
│  │  │  • ConfigState: Admin-controlled parameters                       │  │ │
│  │  │                                                                   │  │ │
│  │  │  Code Region Types:                                               │  │ │
│  │  │  • AtomicBlock: CEI regions, transaction boundaries               │  │ │
│  │  │  • GuardRegion: Require/modifier blocks                           │  │ │
│  │  │  • ExternalCallRegion: External interaction zones                 │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 4: VULNERABILITY PATTERN LAYER                    │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Pattern Matching Engine v2:                                      │  │ │
│  │  │                                                                   │  │ │
│  │  │  Operation Matchers:                                              │  │ │
│  │  │  • has_operation: "TRANSFERS_VALUE_OUT"                           │  │ │
│  │  │  • has_all_operations: ["X", "Y", "Z"]                            │  │ │
│  │  │  • sequence_order: {before: "X", after: "Y"}                      │  │ │
│  │  │  • signature_matches: ".*X:out.*W:bal"                            │  │ │
│  │  │                                                                   │  │ │
│  │  │  Aggregation Modes:                                               │  │ │
│  │  │  • tier_a_only: Deterministic only                                │  │ │
│  │  │  • tier_a_required: Tier A must match, B optional                 │  │ │
│  │  │  • voting: minimum_tiers must agree                               │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 5: SUBGRAPH EXTRACTION LAYER                      │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Query-Aware Extraction:                                          │  │ │
│  │  │                                                                   │  │ │
│  │  │  1. Focal Node Identification (what query is about)               │  │ │
│  │  │  2. Ego-Graph Expansion (1-hop neighbors)                         │  │ │
│  │  │  3. Vulnerability Pattern Neighbors                               │  │ │
│  │  │  4. Cross-Contract Dependencies                                   │  │ │
│  │  │  5. Relevance Pruning (keep top-k by risk)                        │  │ │
│  │  │  6. Priority Ordering (risk, depth, centrality)                   │  │ │
│  │  │                                                                   │  │ │
│  │  │  Result: Minimal subgraph (50 nodes vs 5000) for LLM analysis     │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 6: SEMANTIC SCAFFOLDING LAYER                     │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Token-Efficient Compression:                                     │  │ │
│  │  │                                                                   │  │ │
│  │  │  Instead of 500+ tokens of raw code:                              │  │ │
│  │  │                                                                   │  │ │
│  │  │  FUNCTION_SUMMARY {                                               │  │ │
│  │  │    name: "withdraw",                                              │  │ │
│  │  │    role: "Checkpoint",                                            │  │ │
│  │  │    guards: ["require(amount <= balance)"],                        │  │ │
│  │  │    operations: "R:bal→X:out→W:bal",                               │  │ │
│  │  │    threat_surface: "reentrancy via callback",                     │  │ │
│  │  │    dependencies: ["balanceOf"]                                    │  │ │
│  │  │  }                                                                │  │ │
│  │  │                                                                   │  │ │
│  │  │  = 50 tokens with full security context                           │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 7: MULTI-AGENT VERIFICATION                       │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │                                                                   │  │ │
│  │  │  Query: "Is withdraw() vulnerable?"                               │  │ │
│  │  │           │                                                       │  │ │
│  │  │     ┌─────┴─────┐                                                 │  │ │
│  │  │     ▼           ▼                                                 │  │ │
│  │  │  Explorer    Pattern                                              │  │ │
│  │  │   Agent       Agent                                               │  │ │
│  │  │  (BFS)      (matching)                                            │  │ │
│  │  │     │           │                                                 │  │ │
│  │  │     └─────┬─────┘                                                 │  │ │
│  │  │           ▼                                                       │  │ │
│  │  │     Constraint                                                    │  │ │
│  │  │       Agent                                                       │  │ │
│  │  │       (Z3)                                                        │  │ │
│  │  │           │                                                       │  │ │
│  │  │           ▼                                                       │  │ │
│  │  │       Risk                                                        │  │ │
│  │  │       Agent                                                       │  │ │
│  │  │    (scenarios)                                                    │  │ │
│  │  │           │                                                       │  │ │
│  │  │           ▼                                                       │  │ │
│  │  │     ┌─────────────┐                                               │  │ │
│  │  │     │  CONSENSUS  │                                               │  │ │
│  │  │     │   3/4 agree │                                               │  │ │
│  │  │     │   conf: 87% │                                               │  │ │
│  │  │     └─────────────┘                                               │  │ │
│  │  │                                                                   │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 8: ATTACK PATH SYNTHESIS                          │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Generate Concrete Attack Scenarios:                              │  │ │
│  │  │                                                                   │  │ │
│  │  │  ATTACK_PATH {                                                    │  │ │
│  │  │    entry: "withdraw(uint256)",                                    │  │ │
│  │  │    sink: "msg.sender.call{value: amount}",                        │  │ │
│  │  │    path: [check_balance, external_call, update_balance],          │  │ │
│  │  │    required_bypasses: [],                                         │  │ │
│  │  │    difficulty: "easy",                                            │  │ │
│  │  │    impact: "drain_all_funds",                                     │  │ │
│  │  │    exploit_steps: [                                               │  │ │
│  │  │      "1. Deploy malicious contract",                              │  │ │
│  │  │      "2. Call withdraw() from malicious fallback",                │  │ │
│  │  │      "3. Re-enter before balance update"                          │  │ │
│  │  │    ]                                                              │  │ │
│  │  │  }                                                                │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 9: LLM CONTEXT ENHANCEMENT                        │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Build-Time LLM Annotation:                                       │  │ │
│  │  │                                                                   │  │ │
│  │  │  • Function Descriptions (what it does)                           │  │ │
│  │  │  • Business Context (developer intent)                            │  │ │
│  │  │  • Risk Tags (hierarchical taxonomy)                              │  │ │
│  │  │  • Edge Case Warnings                                             │  │ │
│  │  │                                                                   │  │ │
│  │  │  Caching: Annotations cached by content hash                      │  │ │
│  │  │  Determinism: Same code = same annotations                        │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 10: INTERACTIVE REFINEMENT                        │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  User Feedback Loop:                                              │  │ │
│  │  │                                                                   │  │ │
│  │  │  LLM Response ──▶ User Challenge ──▶ Auto-Investigation           │  │ │
│  │  │       │                │                    │                     │  │ │
│  │  │       │         "Is var Z really           │                     │  │ │
│  │  │       │          immutable?"               │                     │  │ │
│  │  │       │                │                    │                     │  │ │
│  │  │       │                ▼                    │                     │  │ │
│  │  │       │         Show all writes            │                     │  │ │
│  │  │       │         to variable Z              │                     │  │ │
│  │  │       │                │                    │                     │  │ │
│  │  │       └────────────────┼────────────────────┘                     │  │ │
│  │  │                        ▼                                          │  │ │
│  │  │              Update graph with correction                         │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                  TIER 11: OUTPUT & REPORTING                            │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │  • Actionable findings with attack scenarios                      │  │ │
│  │  │  • Multi-agent consensus evidence                                 │  │ │
│  │  │  • Risk matrix (likelihood × impact)                              │  │ │
│  │  │  • Remediation suggestions                                        │  │ │
│  │  │  • CI/CD integration                                              │  │ │
│  │  │  • PDF/HTML reports                                               │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Structures

### 1. Rich Edge Schema

```python
@dataclass
class RichEdge:
    """Enhanced edge with intelligence."""

    # Identity
    id: str
    type: str
    source: str
    target: str

    # Risk Assessment
    risk_score: float = 0.0  # 0-10
    pattern_tags: List[str] = field(default_factory=list)
    # e.g., ["reentrancy", "unchecked_external_call", "cef_violation"]

    # Execution Context
    execution_context: Optional[str] = None  # "normal", "delegatecall", "staticcall"

    # Taint Information
    taint_source: Optional[str] = None  # "user_input", "external_call", "storage"
    taint_confidence: float = 1.0

    # Temporal Ordering
    happens_before: List[str] = field(default_factory=list)  # Edge IDs
    happens_after: List[str] = field(default_factory=list)

    # Guard Analysis
    guards_at_source: List[str] = field(default_factory=list)  # Modifier/require names
    guards_bypassed: List[str] = field(default_factory=list)

    # Evidence
    evidence: List[Evidence] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
```

### 2. Hierarchical Node Schema

```python
@dataclass
class EnhancedNode:
    """Enhanced node with semantic classification."""

    # Identity
    id: str
    type: str  # "Function", "StateVariable", "Contract", etc.
    label: str

    # Semantic Classification
    semantic_role: Optional[str] = None  # "Guardian", "Checkpoint", "EscapeHatch", etc.

    # Semantic Operations (for Functions)
    semantic_ops: List[str] = field(default_factory=list)
    op_sequence: List[Dict] = field(default_factory=list)  # [{op, order, line}, ...]
    op_ordering: List[Tuple[str, str]] = field(default_factory=list)  # [(before, after), ...]
    behavioral_signature: str = ""  # "R:bal→X:out→W:bal"

    # Risk Tags (LLM-assigned)
    risk_tags: List[str] = field(default_factory=list)
    # e.g., ["reentrancy:high", "access_control:missing", "oracle:stale"]

    # LLM Context (Tier B)
    llm_description: Optional[str] = None
    llm_intent: Optional[str] = None
    llm_risks: List[str] = field(default_factory=list)

    # Evidence & Properties
    evidence: List[Evidence] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
```

### 3. Subgraph Structure

```python
@dataclass
class SubGraph:
    """Extracted minimal subgraph for analysis."""

    nodes: Dict[str, EnhancedNode]
    edges: Dict[str, RichEdge]

    # Extraction metadata
    focal_nodes: List[str]  # Entry points for extraction
    extraction_reason: str  # Why this subgraph was extracted
    max_depth: int

    # Prioritization
    node_priority: Dict[str, float]  # Node ID -> priority score

    def to_scaffold(self) -> str:
        """Generate semantic scaffold for LLM."""
        ...
```

### 4. Agent Result Structure

```python
@dataclass
class AgentResult:
    """Result from a single verification agent."""

    agent_name: str
    matched: bool
    confidence: float

    findings: List[Finding]
    evidence: List[Evidence]

    # For explanation
    reasoning: str
    conditions_checked: List[str]
    conditions_passed: List[str]
    conditions_failed: List[str]

@dataclass
class ConsensusResult:
    """Aggregated result from all agents."""

    verdict: str  # "HIGH_RISK", "MEDIUM_RISK", "LOW_RISK", "LIKELY_SAFE"
    confidence: float

    agents_agreed: List[str]
    agents_disagreed: List[str]

    attack_paths: List[AttackPath]
    remediation: List[str]

    # Full breakdown
    agent_results: Dict[str, AgentResult]
```

---

## Pattern Schema v2

```yaml
# Enhanced pattern with operation-based matching
id: reentrancy-classic-v2
name: Classic Reentrancy (CEI Violation)
description: External call before state update allows reentrancy

scope: Function
lens: [Reentrancy, ValueMovement]
severity: critical

# Tier A: Deterministic matching (REQUIRED)
match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_all_operations:
          - TRANSFERS_VALUE_OUT
          - WRITES_USER_BALANCE
      - sequence_order:
          before: TRANSFERS_VALUE_OUT
          after: WRITES_USER_BALANCE
    none:
      - property: has_reentrancy_guard
        value: true

  # Tier B: Semantic matching (OPTIONAL, boosts confidence)
  tier_b:
    any:
      - has_risk_tag: "reentrancy:*"
      - llm_context_contains: "balance update"

# Aggregation mode
aggregation:
  mode: tier_a_required  # Tier A must match, Tier B adds confidence

# Attack path template
attack_path:
  description: "Attacker re-enters function before balance is updated"
  steps:
    - "Deploy contract with malicious fallback/receive"
    - "Call target function with attacker contract"
    - "In fallback, re-call target function"
    - "Drain funds by repeated withdrawal"
  impact: "Complete fund drainage"
  difficulty: easy

# Remediation
remediation:
  - "Use Checks-Effects-Interactions pattern"
  - "Add ReentrancyGuard modifier"
  - "Use pull payment pattern"
```

---

## Multi-Agent System

### Agent Types

| Agent | Purpose | Method | Confidence |
|-------|---------|--------|------------|
| **Explorer** | Trace execution paths | BFS/DFS graph traversal | High for path existence |
| **Pattern** | Match known patterns | Rule-based matching | High for known vulns |
| **Constraint** | Formal verification | Z3 constraint solving | Very high (formal) |
| **Risk** | Assess exploitability | Scenario generation | Medium (heuristic) |
| **Context** | Understand intent | LLM analysis | Medium (semantic) |

### Consensus Algorithm

```python
def compute_consensus(agent_results: List[AgentResult]) -> ConsensusResult:
    """Compute multi-agent consensus."""

    # Count agreements
    positive_agents = [r for r in agent_results if r.matched]
    negative_agents = [r for r in agent_results if not r.matched]

    total = len(agent_results)
    positive_count = len(positive_agents)

    # Weighted confidence (formal agents count more)
    weights = {
        "constraint": 2.0,  # Formal verification
        "pattern": 1.5,     # Known patterns
        "explorer": 1.0,    # Path analysis
        "risk": 0.8,        # Heuristic
        "context": 0.7,     # LLM-based
    }

    weighted_sum = sum(
        r.confidence * weights.get(r.agent_name, 1.0)
        for r in positive_agents
    )
    weight_total = sum(weights.get(r.agent_name, 1.0) for r in agent_results)

    weighted_confidence = weighted_sum / weight_total if weight_total > 0 else 0

    # Determine verdict
    if positive_count >= total * 0.75 and weighted_confidence > 0.7:
        verdict = "HIGH_RISK"
    elif positive_count >= total * 0.5 and weighted_confidence > 0.5:
        verdict = "MEDIUM_RISK"
    elif positive_count >= 1:
        verdict = "LOW_RISK"
    else:
        verdict = "LIKELY_SAFE"

    return ConsensusResult(
        verdict=verdict,
        confidence=weighted_confidence,
        agents_agreed=[r.agent_name for r in positive_agents],
        agents_disagreed=[r.agent_name for r in negative_agents],
        ...
    )
```

---

## Competitive Advantages

| Feature | Slither | Mythril | Semgrep | **AlphaSwarm.sol** |
|---------|---------|---------|---------|--------------|
| Analysis Granularity | Function | Path | Pattern | **Statement-level semantic** |
| Name Independence | No | No | No | **Yes (operations)** |
| Temporal Ordering | Limited | Yes | No | **Full CFG** |
| Multi-Agent Verify | No | No | No | **Yes (4+ agents)** |
| LLM Integration | No | No | No | **Native** |
| Attack Scenarios | No | Yes | No | **Yes (synthesized)** |
| FP Rate | ~30% | ~40% | ~25% | **<10% target** |
| Token Efficiency | N/A | N/A | N/A | **10x reduction** |

---

## Implementation Phases

### Phase 0-4: Foundation (Existing Plan)
- Baseline assessment
- Semantic operations (20 ops)
- Operation sequencing
- Pattern engine v2
- Testing infrastructure

### Phase 5: Edge Intelligence (NEW)
- Rich edge schema implementation
- Risk score computation
- Meta-edge generation
- Edge-based pattern matching

### Phase 6: Node Classification (NEW)
- Semantic role classification
- Guardian/Checkpoint/EscapeHatch detection
- StateAnchor identification
- AtomicBlock extraction

### Phase 7: Subgraph Extraction (NEW)
- Query-aware extraction
- Focal node identification
- Relevance pruning
- Semantic scaffolding

### Phase 8: Multi-Agent Verification (NEW)
- Agent base class
- Explorer agent
- Pattern agent
- Constraint agent (Z3 integration)
- Risk agent
- Consensus computation

### Phase 9: Attack Path Synthesis (NEW)
- Path enumeration
- Guard bypass analysis
- Scenario generation
- Exploit step synthesis

### Phase 10-12: Integration & Polish (Existing + Enhanced)
- LLM context enhancement
- Interactive refinement
- Performance optimization
- Enterprise features
- Documentation

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Detection on renamed | ~60% | >95% | Renamed contract suite |
| Precision | ~70% | >90% | Safe contract FP rate |
| Recall | ~80% | >85% | Vulnerable contract FN rate |
| FP Rate | ~30% | <10% | Multi-agent validation |
| Token efficiency | 1x | 10x | Scaffold vs raw |
| Build time (Tier A) | baseline | <2x | Benchmark suite |
| Attack path quality | N/A | >80% | Manual validation |

---

## File Structure

```
src/true_vkg/
├── kg/
│   ├── schema.py          # Enhanced Node, RichEdge
│   ├── builder.py         # BSKG construction
│   ├── operations.py      # 20 semantic operations
│   ├── sequencing.py      # CFG traversal, ordering
│   ├── signature.py       # Behavioral signatures
│   ├── classifier.py      # Node semantic classification
│   └── edges/
│       ├── risk.py        # Edge risk scoring
│       └── meta.py        # Meta-edge generation
├── queries/
│   ├── patterns.py        # Pattern engine v2
│   ├── aggregation.py     # Tier aggregation
│   └── subgraph.py        # Subgraph extraction
├── agents/
│   ├── base.py            # Agent base class
│   ├── explorer.py        # Path exploration
│   ├── pattern.py         # Pattern matching
│   ├── constraint.py      # Z3 verification
│   ├── risk.py            # Exploitability
│   └── consensus.py       # Multi-agent consensus
├── synthesis/
│   ├── attack_path.py     # Attack path generation
│   └── scaffold.py        # Semantic scaffolding
└── llm/
    ├── annotate.py        # Build-time annotation
    ├── cache.py           # Annotation caching
    └── prompts.py         # LLM prompts
```

---

## Next Steps

1. **Implement Edge Intelligence** (Phase 5) - Start with rich edge schema
2. **Implement Node Classification** (Phase 6) - Semantic role detection
3. **Build Subgraph Extractor** (Phase 7) - Query-aware extraction
4. **Develop Multi-Agent System** (Phase 8) - Explorer + Pattern agents first
5. **Add Attack Path Synthesis** (Phase 9) - Actionable findings

---

*Document Version: 2.0*
*Last Updated: 2025-12-30*
*Status: Active Development*
