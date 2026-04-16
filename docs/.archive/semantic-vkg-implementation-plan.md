# Semantic BSKG Implementation Plan v3

Status: Refined implementation plan incorporating user feedback and research insights.

This document defines the concrete implementation path for a semantic-aware BSKG system
that understands code intent, not just code text.

---

## User Requirements Summary

Based on feedback:

| Requirement | Decision |
|-------------|----------|
| Problem is real | Yes - patterns too dependent on names |
| Layers 3-4 (LLM) needed | Yes - for intent understanding, improper authorization detection |
| Two-tier approach | **Accepted** - Tier A (deterministic), Tier B (heuristic/LLM) |
| Merge Layer 1+2 | **Accepted** - Single unified behavioral layer |
| Confidence weights | **Discarded** - Use boolean logic and voting instead |
| Prompt injection | **Deferred** - Not a priority for now |
| Self-learning | **Deferred** - Focus on static system first |
| Build time | **Not a constraint** - Enterprise use case, accuracy > speed |
| LLM cost | **Acceptable** - LLM is optional premium feature |
| Embeddings | **Deferred** - Future project |
| Testing strategy | **Critical** - Need negative tests, precision validation |
| Tag system | **Critical** - Real-world context, vulnerability hints |

---

## Research Insights

### IRIS: LLM-Assisted Static Analysis (2024)

Key insight: **Neuro-symbolic integration** - LLM infers specifications, static analysis
does whole-repo reasoning.

- LLM discovers taint specifications automatically (no manual annotation)
- Static analysis provides cross-function/cross-file reasoning
- Result: 55 vulnerabilities detected vs CodeQL's 27

**Applicability:** This validates our two-tier approach. LLM for semantic understanding,
deterministic analysis for structural reasoning.

### LLMSA: Compositional Neuro-Symbolic Approach (2024)

Key insight: **Decompose complex analysis into syntactic + semantic sub-problems.**

- Syntactic sub-problems: Resolved by parsing (no hallucinations)
- Semantic sub-problems: Handled by LLM on small code snippets
- Uses "lazy, incremental, parallel prompting"
- Achieved 66% precision, 78% recall

**Applicability:** We should decompose our analysis similarly:
- Tier A handles syntactic/structural analysis (deterministic)
- Tier B handles semantic understanding (LLM)

### SpecRover: Code Intent Extraction (2024)

Key insight: **Iterative specification inference** from code structure and behavior.

- Extracts developer intent, not just code semantics
- Uses reviewer agent for confidence measures
- $0.65 per issue average cost

**Applicability:** This is exactly what we need for the "developer intent" field.

### SCALM: Bad Practices Detection (2024)

Key insight: **Step-Back Prompting + RAG** for smart contract analysis.

- Step-back prompting: Ask LLM to reason about general principles before specific code
- RAG: Ground responses in known vulnerability patterns
- Outperforms existing tools on bad practices detection

**Applicability:** We should use RAG with our pattern library to ground LLM responses.

### OpenSCV: Hierarchical Vulnerability Taxonomy (2024)

Key insight: **Open, hierarchical, community-maintained** vulnerability classification.

Structure:
- Level 1: High-level categories (Access Control, Reentrancy, etc.)
- Level 2: Specific vulnerability types
- Level 3: Variants and edge cases

**Applicability:** We should adopt/extend OpenSCV for our tag system.

---

## Architecture: Two-Tier Semantic VKG

```
┌────────────────────────────────────────────────────────────────────────┐
│                         SEMANTIC BSKG PIPELINE                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  SOLIDITY CODE                                                         │
│       │                                                                │
│       ▼                                                                │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                    TIER A: DETERMINISTIC                        │   │
│  │                    (Fast, Reliable, Always-On)                  │   │
│  │                                                                 │   │
│  │  1. Slither Analysis                                            │   │
│  │       │  • AST, CFG, dataflow                                   │   │
│  │       │  • Existing properties (50+)                            │   │
│  │       ▼                                                         │   │
│  │  2. Unified Behavioral Layer (NEW)                              │   │
│  │       │  • Semantic operations (20+)                            │   │
│  │       │  • Operation sequences with ordering                    │   │
│  │       │  • Behavioral signatures                                │   │
│  │       ▼                                                         │   │
│  │  DETERMINISTIC GRAPH (baseline)                                 │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                              │                                         │
│                              ▼                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                    TIER B: SEMANTIC (Optional)                  │   │
│  │                    (LLM-powered, Audit Mode)                    │   │
│  │                                                                 │   │
│  │  3. LLM Context Enhancement                                     │   │
│  │       │  • Business description                                 │   │
│  │       │  • Developer intent inference                           │   │
│  │       │  • Real-world context                                   │   │
│  │       │  • Vulnerability risk tags                              │   │
│  │       ▼                                                         │   │
│  │  SEMANTIC-ENRICHED GRAPH (premium)                              │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                    PATTERN MATCHING                             │   │
│  │                                                                 │   │
│  │  • Boolean composition: all/any/none                            │   │
│  │  • Voting: minimum_tiers_agree                                  │   │
│  │  • Tier-aware: can require Tier A or Tier A+B                   │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Tier A: Unified Behavioral Layer

### Semantic Operations

Merge fingerprints and operations into a single concept: **Semantic Operations**.

Each function node gets:
```python
function_node.semantic_ops = ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE", ...]
function_node.op_sequence = [
    ("READS_USER_BALANCE", 0),      # order: 0
    ("TRANSFERS_VALUE_OUT", 1),     # order: 1
    ("WRITES_USER_BALANCE", 2),     # order: 2
]
function_node.behavioral_signature = "R:balance→X:transfer→W:balance"
```

### Operation Definitions (20 core operations)

| Operation | Definition | Detection Logic |
|-----------|------------|-----------------|
| **Value Movement** |
| `TRANSFERS_VALUE_OUT` | Sends ETH or tokens | `transfer()`, `send()`, `call{value}`, token transfers |
| `RECEIVES_VALUE_IN` | Receives ETH or tokens | `payable` modifier, token `transferFrom` to self |
| `READS_USER_BALANCE` | Reads user-keyed mapping | `mapping[msg.sender]` or `mapping[address_param]` read |
| `WRITES_USER_BALANCE` | Writes user-keyed mapping | Same mappings, write operation |
| **Access Control** |
| `CHECKS_PERMISSION` | Verifies caller authorization | `msg.sender` comparison, modifier with `require` |
| `MODIFIES_OWNER` | Changes ownership | Writes to `owner`-like state variable |
| `MODIFIES_ROLES` | Changes role assignments | Writes to role mappings |
| **External Interaction** |
| `CALLS_EXTERNAL` | Calls another contract | Any external call |
| `CALLS_UNTRUSTED` | Calls user-controlled address | `delegatecall`, `call` with non-constant target |
| `READS_EXTERNAL_VALUE` | Uses external return value | External call + return value used in computation |
| **State Management** |
| `MODIFIES_CRITICAL_STATE` | Changes privileged state | Writes to: impl slot, paused, fees, treasury |
| `INITIALIZES_STATE` | First-time state setup | Constructor-like patterns, initializer guards |
| `READS_ORACLE` | Reads price/data feed | Calls to oracle contracts, Chainlink patterns |
| **Control Flow** |
| `LOOPS_OVER_ARRAY` | Iterates dynamic array | Loop with `.length` bound |
| `USES_TIMESTAMP` | Uses block.timestamp | `block.timestamp` in conditionals/assignments |
| `USES_BLOCK_DATA` | Uses other block data | `block.number`, `blockhash`, etc. |
| **Arithmetic** |
| `PERFORMS_DIVISION` | Division operation | `/` operator, especially with user input |
| `PERFORMS_MULTIPLICATION` | Multiplication that could overflow | `*` operator on large values |
| **Validation** |
| `VALIDATES_INPUT` | Checks function parameters | `require`/`assert` on parameters |
| `EMITS_EVENT` | Logs state change | `emit` statement |

### Operation Sequence Detection

Track the **order** of operations within a function:

```python
def derive_operation_sequence(function: SlitherFunction) -> List[Tuple[str, int]]:
    """Extract operations with their relative ordering from CFG."""
    operations = []
    order = 0

    for node in function.cfg_traversal():
        ops_at_node = detect_operations_at_node(node)
        for op in ops_at_node:
            operations.append((op, order))
        if ops_at_node:
            order += 1

    return operations
```

### Behavioral Signature

A compact, canonical representation of function behavior:

```python
def compute_behavioral_signature(op_sequence: List[Tuple[str, int]]) -> str:
    """Create canonical signature from operation sequence."""
    # Map operations to short codes
    OP_CODES = {
        "READS_USER_BALANCE": "R:bal",
        "WRITES_USER_BALANCE": "W:bal",
        "TRANSFERS_VALUE_OUT": "X:out",
        "CHECKS_PERMISSION": "C:auth",
        # ...
    }

    parts = []
    for op, _ in sorted(op_sequence, key=lambda x: x[1]):
        if op in OP_CODES:
            parts.append(OP_CODES[op])

    return "→".join(parts)
```

Example signatures:
- Vulnerable withdrawal: `R:bal→X:out→W:bal` (read, external, write = reentrancy risk)
- Safe withdrawal: `R:bal→W:bal→X:out` (read, write, external = CEI compliant)
- Unprotected admin: `W:critical` (no `C:auth` prefix)

---

## Tier B: LLM Context Enhancement

### Node Annotations Schema

For each Function node, LLM adds:

```yaml
llm_context:
  # What the code does in business terms
  business_description: "Allows users to withdraw their deposited ETH balance"

  # What the developer intended (may differ from what code does!)
  developer_intent: "Safely transfer user funds with protection against reentrancy"

  # Real-world context
  real_world_context:
    domain: "DeFi lending"
    actors: ["depositor", "protocol"]
    assets: ["ETH deposits"]

  # Vulnerability risk assessment
  risk_tags:
    - tag: "reentrancy"
      confidence: high
      reason: "External call before state update"
    - tag: "access_control"
      confidence: low
      reason: "Uses require(msg.sender == depositor) check"

  # What assumptions the code makes
  assumptions:
    - "Caller is the depositor (verified by mapping key)"
    - "Contract has sufficient balance"

  # Model metadata
  model_info:
    model: "claude-opus-4-5-20250101"
    timestamp: "2025-01-15T10:30:00Z"
```

### LLM Prompting Strategy

Based on SCALM research, use **Step-Back Prompting + RAG**:

```python
async def annotate_function(function: FunctionNode, context: ProjectContext) -> LLMContext:
    """Annotate function with LLM-derived context."""

    # Step 1: Step-Back Prompting - understand general principles
    step_back_prompt = f"""
    Before analyzing this specific function, consider:
    1. What are common patterns in {context.domain} applications?
    2. What security concerns typically arise in functions that {describe_function_behavior(function)}?
    3. What would a security auditor look for in this type of function?
    """

    # Step 2: RAG - ground in known patterns
    relevant_patterns = retrieve_similar_patterns(function, pattern_library)

    # Step 3: Specific analysis
    analysis_prompt = f"""
    Given the function:
    ```solidity
    {function.source_code}
    ```

    Contract context:
    {context.contract_summary}

    Similar known patterns:
    {format_patterns(relevant_patterns)}

    Provide:
    1. Business description (1-2 sentences)
    2. Developer intent (what they meant to achieve)
    3. Real-world context (domain, actors, assets)
    4. Vulnerability risk tags with confidence and reasoning
    5. Implicit assumptions the code makes
    """

    return await llm.analyze(step_back_prompt + analysis_prompt)
```

### Risk Tags Taxonomy

Based on OpenSCV + custom extensions:

```yaml
# Level 1: Categories (lenses)
categories:
  access_control:
    tags:
      - missing_auth
      - weak_auth
      - tx_origin
      - centralization_risk
      - privilege_escalation

  reentrancy:
    tags:
      - classic_reentrancy
      - cross_function
      - cross_contract
      - read_only_reentrancy

  value_movement:
    tags:
      - unchecked_transfer
      - arbitrary_transfer
      - flash_loan_risk
      - price_manipulation

  oracle:
    tags:
      - stale_price
      - single_source
      - manipulation_risk
      - missing_validation

  arithmetic:
    tags:
      - overflow
      - underflow
      - precision_loss
      - division_by_zero

  dos:
    tags:
      - unbounded_loop
      - gas_griefing
      - block_stuffing
      - external_dependency

  upgrade:
    tags:
      - unprotected_upgrade
      - storage_collision
      - initializer_risk
      - selfdestruct_risk

  logic:
    tags:
      - incorrect_comparison
      - missing_validation
      - state_inconsistency
      - front_running

  # NEW: Business logic tags (LLM-derived)
  business:
    tags:
      - user_funds_at_risk
      - admin_can_rug
      - economic_attack
      - governance_manipulation
```

---

## Pattern Matching: Boolean Logic + Voting

### Pattern Schema v2

```yaml
id: reentrancy-classic-v2
name: Classic Reentrancy
description: External call before state update in withdrawal-like function
scope: Function
lens:
  - Reentrancy
severity: critical

# Boolean matching (replaces weighted confidence)
match:
  # Tier A conditions (deterministic)
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_operation: TRANSFERS_VALUE_OUT
      - has_operation: WRITES_USER_BALANCE
    any:
      - sequence_order:
          before: TRANSFERS_VALUE_OUT
          after: WRITES_USER_BALANCE
      - sequence_order:
          before: CALLS_EXTERNAL
          after: WRITES_USER_BALANCE
    none:
      - property: has_reentrancy_guard
        value: true

  # Tier B conditions (LLM-enhanced, optional)
  tier_b:
    any:
      - has_risk_tag: reentrancy
        min_confidence: medium
      - has_risk_tag: classic_reentrancy

# How to combine tiers
aggregation:
  mode: tier_a_required  # Options: tier_a_only, tier_a_required, voting
  # tier_a_only: Only use Tier A (default/fast mode)
  # tier_a_required: Tier A must match, Tier B provides extra signal
  # voting: Match if either tier matches (high recall)
```

### Voting Mode

For patterns where we want maximum recall:

```yaml
aggregation:
  mode: voting
  minimum_tiers: 1  # Match if at least 1 tier matches

# Example: Detect potentially unprotected admin functions
# Tier A might miss if naming is non-standard
# Tier B catches via LLM understanding
```

### Tier-Aware Execution

```python
def evaluate_pattern(pattern: Pattern, node: Node, tier_b_available: bool) -> Match:
    """Evaluate pattern with tier-aware logic."""

    tier_a_match = evaluate_tier_a(pattern.match.tier_a, node)

    if pattern.aggregation.mode == "tier_a_only":
        return tier_a_match

    if not tier_b_available:
        # Fall back to Tier A only
        return tier_a_match

    tier_b_match = evaluate_tier_b(pattern.match.tier_b, node)

    if pattern.aggregation.mode == "tier_a_required":
        if not tier_a_match.matched:
            return NoMatch()
        # Tier B enhances confidence but doesn't change match
        return tier_a_match.with_tier_b_context(tier_b_match)

    if pattern.aggregation.mode == "voting":
        if tier_a_match.matched or tier_b_match.matched:
            return Match(
                tiers_matched=["A"] if tier_a_match.matched else [] +
                             ["B"] if tier_b_match.matched else [],
                evidence=combine_evidence(tier_a_match, tier_b_match)
            )
        return NoMatch()
```

---

## Testing Strategy

### Problem: Current Tests Are Too Lax

Current tests only verify positive matches. A pattern could match EVERY function
and still pass tests. We need:

1. **Positive tests**: Pattern matches vulnerable code ✓
2. **Negative tests**: Pattern does NOT match safe code ✓
3. **Precision tests**: Pattern doesn't over-match

### Test Contract Structure

```
tests/contracts/
├── reentrancy/
│   ├── ReentrancyVulnerable.sol      # Should match
│   ├── ReentrancySafe.sol            # Should NOT match
│   ├── ReentrancyGuarded.sol         # Should NOT match
│   └── ReentrancyEdgeCase.sol        # Edge cases
├── access_control/
│   ├── MissingAuthVulnerable.sol
│   ├── MissingAuthSafe.sol
│   └── ...
└── ...
```

### Test Pattern Template

```python
class PatternTestCase:
    """Template for pattern tests."""

    pattern_id: str

    # Functions that MUST match
    must_match: List[str] = [
        "ReentrancyVulnerable.withdraw",
        "ReentrancyVulnerable.withdrawAll",
    ]

    # Functions that MUST NOT match
    must_not_match: List[str] = [
        "ReentrancySafe.withdraw",           # CEI compliant
        "ReentrancyGuarded.withdraw",        # Has guard
        "ReentrancySafe.internalHelper",     # Internal function
    ]

    # Maximum acceptable false positive rate on safe contracts
    max_false_positive_rate: float = 0.05  # 5%
```

### Precision Validation

```python
def validate_pattern_precision(pattern_id: str, test_corpus: List[Contract]):
    """Validate pattern doesn't over-match."""

    results = run_pattern(pattern_id, test_corpus)

    # Count matches on explicitly-safe functions
    safe_functions = [f for f in test_corpus.functions if f.is_marked_safe]
    false_positives = [f for f in safe_functions if f in results.matches]

    fp_rate = len(false_positives) / len(safe_functions)

    assert fp_rate <= pattern.max_false_positive_rate, (
        f"Pattern {pattern_id} has {fp_rate:.1%} false positive rate, "
        f"exceeds maximum {pattern.max_false_positive_rate:.1%}"
    )
```

### Renamed Contract Tests

To validate name-agnostic detection:

```python
def test_pattern_with_renamed_contracts():
    """Test that patterns work even with non-standard naming."""

    # Original contract with standard names
    original = load_contract("ReentrancyVulnerable.sol")

    # Same contract with renamed functions/variables
    renamed = rename_identifiers(original, {
        "withdraw": "removeFunds",
        "balances": "userDeposits",
        "owner": "administrator",
    })

    # Pattern should match both
    assert pattern_matches(original.withdraw)
    assert pattern_matches(renamed.removeFunds), (
        "Pattern failed on renamed contract - too dependent on names!"
    )
```

---

## Implementation Phases

### Phase 1: Unified Behavioral Layer (3-4 weeks)

**Goal:** Add semantic operations to Tier A analysis.

Tasks:
1. Define 20 core semantic operations in `builder.py`
2. Implement operation detection from Slither IR
3. Implement operation sequence extraction
4. Implement behavioral signature computation
5. Add operations to Function node schema
6. Update pattern engine to support operation matching

Deliverables:
- `function_node.semantic_ops: List[str]`
- `function_node.op_sequence: List[Tuple[str, int]]`
- `function_node.behavioral_signature: str`
- Pattern syntax: `has_operation`, `sequence_order`

### Phase 2: Testing Infrastructure (2 weeks, parallel)

**Goal:** Create robust test framework with negative tests.

Tasks:
1. Reorganize test contracts by vulnerability type
2. Create "safe" versions of each vulnerable contract
3. Implement `PatternTestCase` template
4. Add precision validation to CI
5. Create renamed contract test suite

Deliverables:
- Reorganized `tests/contracts/` structure
- `tests/pattern_test_template.py`
- CI job for precision validation

### Phase 3: Pattern Migration (2 weeks)

**Goal:** Migrate patterns to use operations instead of names.

Tasks:
1. Audit all patterns for name dependencies
2. Rewrite patterns using `has_operation` and `sequence_order`
3. Validate patterns against renamed test contracts
4. Document pattern authoring guidelines

Deliverables:
- Updated patterns in `patterns/`
- Pattern authoring guide
- Validation report

### Phase 4: LLM Context Enhancement (4-5 weeks)

**Goal:** Implement Tier B LLM annotation.

Tasks:
1. Design LLM prompt templates (step-back + RAG)
2. Implement annotation pipeline in `builder.py`
3. Add LLM context to node schema
4. Implement tag taxonomy
5. Add `--semantic` flag to CLI
6. Implement caching for LLM responses

Deliverables:
- `function_node.llm_context` schema
- `alphaswarm build-kg --semantic` option
- Tag taxonomy in `patterns/tags/`
- Cached annotations for incremental builds

### Phase 5: Tier B Pattern Integration (2 weeks)

**Goal:** Enable patterns to use LLM context.

Tasks:
1. Extend pattern schema for `tier_b` conditions
2. Implement `has_risk_tag` matcher
3. Implement aggregation modes (tier_a_required, voting)
4. Create Tier B-enhanced pattern variants

Deliverables:
- Pattern schema v2
- Aggregation mode support
- Example Tier B patterns

---

## CLI Interface

```bash
# Default: Tier A only (fast, deterministic)
uv run alphaswarm build-kg project/

# With LLM enhancement (slower, more accurate)
uv run alphaswarm build-kg project/ --semantic

# With specific model
uv run alphaswarm build-kg project/ --semantic --model claude-opus-4-5-20250101

# Query with tier awareness
uv run alphaswarm query "pattern:reentrancy-classic" --tier-b  # Use LLM tags if available
```

---

## Success Criteria

### Phase 1 Success
- [ ] 20 semantic operations implemented and tested
- [ ] Operation sequences correctly capture temporal ordering
- [ ] Behavioral signatures are canonical (same behavior = same signature)

### Phase 2 Success
- [ ] Every pattern has at least 3 positive and 3 negative test cases
- [ ] CI fails if pattern precision drops below threshold
- [ ] Renamed contract tests pass for all non-name-dependent patterns

### Phase 3 Success
- [ ] 80%+ patterns migrated to operation-based matching
- [ ] Name-dependent patterns clearly documented
- [ ] Detection rate on renamed contracts improved by >30%

### Phase 4 Success
- [ ] LLM annotations provide meaningful business context
- [ ] Risk tags align with manual auditor assessments (validated on 10+ contracts)
- [ ] Annotation caching reduces rebuild time by >50%

### Phase 5 Success
- [ ] Tier B patterns catch vulnerabilities that Tier A misses
- [ ] False positive rate remains below 10%
- [ ] Voting mode provides high recall for audit use cases

---

## Novel Ideas: Beyond Existing Research

The following ideas are original contributions that extend beyond published research.
These are experimental concepts for future exploration.

### Idea 1: Adversarial Scenario Generation

**Concept:** Instead of just detecting patterns, have the LLM generate attack scenarios,
then use the BSKG to validate if they're actually exploitable.

```
┌─────────────────────────────────────────────────────────────────┐
│                  ADVERSARIAL SCENARIO PIPELINE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. LLM analyzes function and generates attack hypotheses:      │
│     "An attacker could call withdraw() recursively during       │
│      the ETH transfer to drain the contract"                    │
│                                                                 │
│  2. BSKG validates hypothesis against graph structure:           │
│     - Is there an external call before state update? ✓          │
│     - Can the caller re-enter the function? ✓                   │
│     - Is there a reentrancy guard? ✗                            │
│     → HYPOTHESIS VALIDATED                                      │
│                                                                 │
│  3. Output: Attack scenario + structural evidence               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

This inverts the traditional approach: instead of "does code match pattern?", we ask
"can this attack scenario actually work on this code?"

**Why it's novel:** Existing tools match patterns. We generate and validate attacks.

### Idea 2: Economic Model Understanding

**Concept:** Extract the economic model of the protocol and detect attacks that
are economically rational but not structurally obvious.

```yaml
# LLM extracts economic model
economic_model:
  protocol_type: "lending"
  assets:
    - name: "collateral"
      operations: [deposit, withdraw]
    - name: "borrowed"
      operations: [borrow, repay]
  invariants:
    - "collateral_value >= borrowed_value * collateralization_ratio"
    - "interest accrues over time"
  economic_actors:
    - depositors: "provide liquidity, earn interest"
    - borrowers: "pay interest, risk liquidation"
    - liquidators: "profit from undercollateralized positions"

# BSKG detects economic attacks
economic_attacks:
  - type: "oracle manipulation"
    scenario: "Manipulate price oracle to make positions appear undercollateralized"
    profitable_if: "manipulation cost < liquidation profit"

  - type: "flash loan attack"
    scenario: "Borrow assets, manipulate price, liquidate, repay"
    requires: "price oracle can be moved within single tx"
```

**Why it's novel:** Current tools detect code patterns. We understand economic
incentives and detect attacks that are economically rational.

### Idea 3: Intent Deviation Detection

**Concept:** Compare what developers INTENDED (from comments, docs, naming) with
what the code ACTUALLY DOES. Deviations are potential bugs.

```yaml
function_analysis:
  declared_intent:
    source: "NatSpec comment"
    text: "Safely withdraws user funds with reentrancy protection"

  actual_behavior:
    operations: [READS_BALANCE, TRANSFERS_VALUE, WRITES_BALANCE]
    has_reentrancy_guard: false

  deviation_detected:
    type: "intent_behavior_mismatch"
    severity: high
    explanation: |
      Developer claims "reentrancy protection" but no guard is present.
      Either the comment is misleading or the implementation is incomplete.
```

**Why it's novel:** We don't just find vulnerabilities - we find places where
the code doesn't match developer expectations.

### Idea 4: Cross-Contract Intent Propagation

**Concept:** Track semantic intent across contract boundaries. If Contract A calls
Contract B with certain expectations, verify B honors them.

```
Contract A (Vault):
  - Expects: "Only I can withdraw from Strategy"
  - Calls: Strategy.withdraw(amount)

Contract B (Strategy):
  - Declared: "Only vault can call withdraw"
  - Actual: No access control on withdraw()

Intent Propagation:
  A.withdraw() → expects_exclusive_access(B.withdraw)
  B.withdraw() → has_access_control: false

CROSS-CONTRACT VULNERABILITY:
  A expects exclusive access to B.withdraw()
  B does not enforce this expectation
  Any address can drain B directly
```

**Why it's novel:** Single-contract analysis misses this. We track intent across
the call graph.

### Idea 5: Temporal Vulnerability Windows

**Concept:** Some vulnerabilities only exist in specific temporal windows. Model
time-dependent state transitions.

```yaml
temporal_analysis:
  function: "claimRewards"

  state_transitions:
    t0: "lastClaim = block.timestamp"
    t1: "rewards accumulate over time"
    t2: "claim() transfers accumulated rewards"

  temporal_vulnerability:
    type: "front-running window"
    window: "between t1 and t2"
    attack: |
      Attacker sees pending claim transaction, front-runs with
      large deposit to dilute rewards, then withdraws after claim.

  temporal_invariant_violation:
    expected: "rewards proportional to time staked"
    actual: "rewards proportional to balance at claim time"
    exploitable: true
```

**Why it's novel:** Most tools analyze static code. We model temporal dynamics.

### Idea 6: Protocol Semantic Layer

**Concept:** Understand standard protocols (ERC20, ERC721, Uniswap, etc.) at a
semantic level, then detect deviations and misuse.

```yaml
protocol_knowledge:
  ERC20:
    semantics:
      transfer: "moves tokens, emits Transfer event, returns bool"
      approve: "sets allowance, emits Approval event"
      transferFrom: "uses allowance, decrements it"
    invariants:
      - "sum of balances == totalSupply"
      - "transferFrom requires allowance >= amount"
    common_bugs:
      - "missing return value check"
      - "approve race condition"

  detected_in_code:
    function: "swapTokens"
    protocol_interaction:
      calls: ERC20.transfer
      missing: return_value_check
    finding:
      type: "protocol_misuse"
      description: "ERC20 transfer return value not checked"
```

**Why it's novel:** We encode protocol semantics as first-class knowledge, not
just patterns to match.

### Idea 7: Compositional Vulnerability Chains

**Concept:** Small issues that are individually low-severity can combine into
critical vulnerabilities. Model and detect these chains.

```yaml
vulnerability_chain:
  components:
    - id: "unchecked-return-value"
      severity: low
      location: "swapTokens:L45"

    - id: "state-update-on-failure"
      severity: low
      location: "swapTokens:L48"

    - id: "no-slippage-check"
      severity: medium
      location: "swapTokens:L42"

  chain_analysis:
    combined_severity: critical
    attack_scenario: |
      1. Attacker manipulates pool price
      2. Victim's swap fails silently (unchecked return)
      3. State updates as if swap succeeded
      4. Victim loses funds without receiving tokens

  individual_flags_would_miss: true
  chain_detection_required: true
```

**Why it's novel:** Tools find individual issues. We find how issues combine
into exploits.

### Idea 8: Behavioral Regression Detection

**Concept:** Compare behavioral signatures across contract versions. Detect when
"safe" behavior regresses to "unsafe" patterns.

```yaml
version_comparison:
  v1:
    function: "withdraw"
    signature: "C:auth→R:bal→W:bal→X:out"  # Safe: check, read, write, external
    status: safe

  v2:
    function: "withdraw"
    signature: "C:auth→R:bal→X:out→W:bal"  # Unsafe: check, read, external, write
    status: vulnerable

  regression_detected:
    type: "reentrancy_regression"
    change: "external call moved before state update"
    severity: critical
    recommendation: "Revert to v1 pattern or add reentrancy guard"
```

**Why it's novel:** We don't just analyze code - we analyze how code changes
over time and detect security regressions.

### Idea 9: Fuzzy Intent Matching

**Concept:** When developer names don't match expected patterns, use fuzzy
semantic matching to infer intent.

```python
# Traditional: exact regex match
pattern = r".*[Oo]wner.*"  # Fails on "administrator", "admin", "controller"

# Fuzzy intent matching
def infer_intent(identifier: str, context: CodeContext) -> List[Intent]:
    """Use semantic similarity to infer intent from identifier."""

    # Embed the identifier + its usage context
    embedding = embed(identifier, context.usage_patterns)

    # Compare to known intent embeddings
    similarities = {
        "ownership": cosine_sim(embedding, OWNERSHIP_INTENT),
        "balance": cosine_sim(embedding, BALANCE_INTENT),
        "access_control": cosine_sim(embedding, ACCESS_CONTROL_INTENT),
    }

    # Return intents above threshold
    return [intent for intent, sim in similarities.items() if sim > 0.7]
```

**Why it's novel:** We move from string matching to intent understanding.

### Idea 10: Self-Improving Pattern Library

**Concept:** When LLM finds a new vulnerability pattern, automatically propose
a new deterministic pattern for Tier A.

```
┌─────────────────────────────────────────────────────────────────┐
│                  PATTERN EVOLUTION PIPELINE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. LLM (Tier B) identifies vulnerability not caught by Tier A │
│                                                                 │
│  2. System analyzes: what operations/properties are present?    │
│     - Operations: [READS_ORACLE, USES_IN_CALCULATION]           │
│     - Missing: [VALIDATES_FRESHNESS]                            │
│     - Sequence: oracle_read → calculation (no check between)    │
│                                                                 │
│  3. Auto-generate candidate Tier A pattern:                     │
│     ```yaml                                                     │
│     match:                                                      │
│       tier_a:                                                   │
│         all:                                                    │
│           - has_operation: READS_ORACLE                         │
│           - has_operation: USES_IN_CALCULATION                  │
│         none:                                                   │
│           - has_operation: VALIDATES_FRESHNESS                  │
│     ```                                                         │
│                                                                 │
│  4. Human reviews and approves → pattern added to library       │
│                                                                 │
│  5. Future runs: Tier A catches this pattern (faster, cheaper)  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Why it's novel:** The system proposes its own improvements. Human reviews
ensure quality. Over time, Tier A becomes more comprehensive.

---

## Open Questions for Future Consideration

1. **Should we integrate other analysis tools (Mythril, Echidna)?**
   - User indicated interest
   - Would provide truly independent signals
   - Significant integration effort

2. **How do we handle cross-contract vulnerabilities?**
   - Current system is mostly single-contract
   - LLM could help identify cross-contract risks

3. **Should we support custom operation definitions per project?**
   - Some projects have domain-specific operations
   - Could be defined in project config

4. **How do we evolve the tag taxonomy over time?**
   - New vulnerability classes emerge
   - Need versioning strategy

---

## Appendix: Sample Patterns

### Example 1: Reentrancy (Tier A + Tier B)

```yaml
id: reentrancy-classic-v2
name: Classic Reentrancy
scope: Function
lens: [Reentrancy]
severity: critical

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_operation: CALLS_EXTERNAL
      - has_operation: WRITES_USER_BALANCE
      - sequence_order:
          before: CALLS_EXTERNAL
          after: WRITES_USER_BALANCE
    none:
      - property: has_reentrancy_guard
        value: true

  tier_b:
    any:
      - has_risk_tag: reentrancy
      - has_risk_tag: classic_reentrancy

aggregation:
  mode: tier_a_required
```

### Example 2: Unprotected Admin (High Recall)

```yaml
id: unprotected-admin-function
name: Unprotected Admin Function
scope: Function
lens: [Authority]
severity: high

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_operation: MODIFIES_CRITICAL_STATE
    none:
      - has_operation: CHECKS_PERMISSION
      - property: has_access_gate
        value: true

  tier_b:
    any:
      - has_risk_tag: missing_auth
      - has_risk_tag: admin_can_rug
      - llm_context.developer_intent:
          contains: ["admin", "owner", "privileged"]

aggregation:
  mode: voting  # High recall - catch even if Tier A misses due to naming
  minimum_tiers: 1
```

### Example 3: Business Logic Risk (Tier B Primary)

```yaml
id: economic-attack-risk
name: Economic Attack Risk
scope: Function
lens: [Logic, Value_Movement]
severity: medium

match:
  tier_a:
    all:
      - has_operation: READS_EXTERNAL_VALUE
      - has_operation: TRANSFERS_VALUE_OUT

  tier_b:
    all:
      - has_risk_tag: economic_attack
        min_confidence: medium
    any:
      - has_risk_tag: price_manipulation
      - has_risk_tag: flash_loan_risk
      - llm_context.real_world_context.domain:
          in: ["DeFi", "lending", "exchange"]

aggregation:
  mode: tier_a_required  # Tier A provides grounding, Tier B adds context
```
