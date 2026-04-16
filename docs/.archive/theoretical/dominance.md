# Dominance-Based Ordering Reference

**Phase:** 5.9 - LLM Graph Interface Improvements
**Module:** `src/alphaswarm_sol/kg/dominance.py`

This document describes the dominance-based ordering system used for path-qualified
operation sequencing in AlphaSwarm.sol.

## Overview

Traditional CFG-ordered operation sequencing has a critical flaw: **CFG order does not
equal execution order**. A node appearing "before" another in CFG traversal may not
always execute before it due to conditional branches.

Dominance-based ordering fixes this by computing true **path-qualified relationships**:

| Relation | Meaning | CFG Interpretation |
|----------|---------|-------------------|
| `ALWAYS_BEFORE` | A dominates B | A executes before B on ALL paths |
| `SOMETIMES_BEFORE` | A can reach B | A executes before B on SOME paths |
| `NEVER_BEFORE` | No path A→B | A never precedes B |
| `UNKNOWN` | Cannot determine | Analysis incomplete |

## Cooper-Harvey-Kennedy Algorithm

We use the Cooper-Harvey-Kennedy iterative dominance algorithm (2001), which is
simple, fast, and efficient for typical CFG sizes (< 30k nodes).

### Algorithm Overview

```
dom[entry] = {entry}
for all other nodes n: dom[n] = all_nodes
while changes:
    for each node n (except entry):
        dom[n] = {n} ∪ (∩ dom[p] for p in predecessors(n))
```

### Complexity

- Time: O(n^2) worst case, typically O(n) for reducible CFGs
- Space: O(n^2) for dominator sets

### Post-Dominators

Post-dominators are computed using the reverse CFG:
- Swap successors and predecessors
- Use exit node instead of entry node
- Same iterative algorithm

## Dominance Semantics

### Dominator

Node A **dominates** node B if all paths from the entry node to B pass through A.

```
Entry → A → ... → B
          ↘ (any path) ↗
```

If A dominates B, then A **always executes before** B.

### Post-Dominator

Node A **post-dominates** node B if all paths from B to the exit node pass through A.

```
B → ... → A → Exit
    ↘ (any path) ↗
```

If A post-dominates B, then A **always executes after** B (if the function returns normally).

### Immediate Dominator

The **immediate dominator** (idom) of a node B is the unique dominator that doesn't
dominate any other dominator of B (except itself). It's the "closest" dominator.

## Path-Qualified Ordering

### OrderingRelation Enum

```python
class OrderingRelation(Enum):
    ALWAYS_BEFORE = "always_before"      # A dominates B
    SOMETIMES_BEFORE = "sometimes_before" # A precedes B on some path
    NEVER_BEFORE = "never_before"        # A is not before B on any path
    UNKNOWN = "unknown"                  # Cannot determine
```

### Decision Logic

```
compute_ordering(A, B):
    if A dominates B:
        return ALWAYS_BEFORE
    if A can reach B:
        return SOMETIMES_BEFORE
    if B dominates A:
        return NEVER_BEFORE
    if B can reach A:
        return NEVER_BEFORE
    return NEVER_BEFORE  # Parallel branches
```

### PathQualifiedOrdering Result

```python
@dataclass
class PathQualifiedOrdering:
    relation: OrderingRelation
    confidence: float  # 0.0-1.0
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
```

## Unknown Emission Criteria

The analyzer emits `UNKNOWN` when analysis cannot provide a confident answer:

### 1. CFG Has Unreachable Nodes

**Trigger:** Entry node cannot reach all nodes in the CFG.

**Example:**
```solidity
function broken() public {
    if (false) {
        // Unreachable dead code
        balances[msg.sender] -= 1;
    }
    external_call();
}
```

**Reason:** Unreachable code may indicate incomplete CFG or dead code that
could become reachable with different constants.

**Result:**
```python
PathQualifiedOrdering(
    relation=OrderingRelation.UNKNOWN,
    confidence=0.5,
    reason="CFG has unreachable nodes"
)
```

### 2. Entry/Exit Points Cannot Be Determined

**Trigger:** No clear entry or exit node in the CFG.

**Example:** Malformed CFG from parsing errors or inline assembly.

**Result:**
```python
PathQualifiedOrdering(
    relation=OrderingRelation.UNKNOWN,
    confidence=0.0,
    reason="Entry/exit points not found"
)
```

### 3. Modifier Body Not Available (External)

**Trigger:** Modifier is from an external contract or library without source.

**Example:**
```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract Token is ReentrancyGuard {
    function withdraw() external nonReentrant {
        // nonReentrant body not available for analysis
    }
}
```

**Result:** Cross-modifier ordering returns `UNKNOWN` for operations
involving external modifier effects.

### 4. Loop with Unresolvable Iteration Count

**Trigger:** Loop body contains operations and iteration count is unknown.

**Example:**
```solidity
function batch(address[] calldata addrs) public {
    for (uint i = 0; i < addrs.length; i++) {
        external_call(addrs[i]);  // Executes 0..N times
    }
    state_write();  // Does this always happen after ALL calls?
}
```

**Reason:** `external_call` may execute 0, 1, or N times depending on input.
Dominance is clear (loop entry dominates body), but ordering with post-loop
operations is ambiguous.

**Result:** Loop-carried dependencies return reduced confidence.

## Guard Dominance Classification

Guards (modifiers, require statements) are classified by their dominance
relationship to protected sinks:

### GuardDominance Enum

```python
class GuardDominance(Enum):
    PRESENT = "present"       # Guard exists somewhere
    DOMINATING = "dominating" # Guard dominates all paths to sink
    BYPASSABLE = "bypassable" # Guard exists but can be bypassed
    UNKNOWN = "unknown"       # Dominance cannot be proven
```

### Classification Logic

```python
def classify_guard_dominance(guard_node, sink_node, analyzer):
    if guard_node not in analyzer.nodes:
        return GuardDominance.UNKNOWN
    if sink_node not in analyzer.nodes:
        return GuardDominance.UNKNOWN
    if analyzer.dominates(guard_node, sink_node):
        return GuardDominance.DOMINATING
    if analyzer.can_reach(guard_node, sink_node):
        return GuardDominance.BYPASSABLE
    return GuardDominance.PRESENT
```

### Guard Types

| Guard Type | Example | Detection |
|------------|---------|-----------|
| Modifier guard | `nonReentrant`, `onlyOwner` | Modifier in function definition |
| Inherited modifier | `whenNotPaused` from parent | Inherited modifier usage |
| Early return | `if (!valid) return;` | Conditional return node |
| Revert guard | `require(condition)` | Require/assert node |

## Multi-Modifier Chains

For a function with modifiers `A`, `B`, `C` applied in declaration order:

```solidity
function foo() external A B C { ... }
```

Execution order:
1. A's entry code (before `_`)
2. B's entry code (before `_`)
3. C's entry code (before `_`)
4. Function body
5. C's exit code (after `_`)
6. B's exit code (after `_`)
7. A's exit code (after `_`)

### Dominance in Modifier Chains

- A's entry dominates B's entry dominates C's entry dominates function body
- Function body dominates C's exit dominates B's exit dominates A's exit

### ModifierChainSummary

```python
@dataclass
class ModifierChainSummary:
    modifiers: List[ModifierSummary]
    combined_entry_ops: FrozenSet[str]
    combined_exit_ops: FrozenSet[str]
    any_external: bool
    dominance_chain_intact: bool
```

## Interprocedural Ordering

### Internal Calls

For internal function calls, we use **function summaries** to avoid re-analyzing
the entire callee CFG:

```python
@dataclass
class InternalCallSummary:
    function_name: str
    entry_ops: FrozenSet[str]  # Ops at function start
    exit_ops: FrozenSet[str]   # Ops at function end
    has_external_call: bool
    summary_available: bool
```

### Summary Usage

When computing ordering across a call:
1. Replace call node with summary
2. Call's entry ops dominate call's exit ops
3. If summary unavailable, emit `UNKNOWN`

## Integration with Sequencing

The `sequencing.py` module provides a wrapper that uses dominance:

```python
def compute_path_qualified_ordering(
    op_a: OperationOccurrence,
    op_b: OperationOccurrence,
    fn: Any,
    modifier_summaries: Optional[ModifierChainSummary] = None,
) -> PathQualifiedOrdering:
    """Compute path-qualified ordering using dominance analysis."""
```

### Backward Compatibility

The old `compute_ordering_pairs()` function remains for backward compatibility
but now returns boolean pairs (true = SOMETIMES_BEFORE or ALWAYS_BEFORE).

New code should use `compute_path_qualified_ordering()` for full semantics.

## Examples

### Example 1: Vulnerable vs Safe CEI

```solidity
// VULNERABLE: external call before state write
function withdrawVuln() public {
    uint bal = balances[msg.sender];  // Node 0
    msg.sender.call{value: bal}("");  // Node 1
    balances[msg.sender] = 0;         // Node 2
}

// Dominance: 0 dominates 1, 1 dominates 2
// Ordering: ALWAYS_BEFORE(call, write) = TRUE -> VULNERABLE

// SAFE: state write before external call (CEI)
function withdrawSafe() public {
    uint bal = balances[msg.sender];  // Node 0
    balances[msg.sender] = 0;         // Node 1
    msg.sender.call{value: bal}("");  // Node 2
}

// Dominance: 0 dominates 1, 1 dominates 2
// Ordering: ALWAYS_BEFORE(write, call) = TRUE -> SAFE
```

### Example 2: CFG Order vs Dominance Order

```solidity
function conditional() public {
    if (condition) {
        state_write();    // Node 2 (inside branch)
    }
    external_call();      // Node 3 (after branch)
}
```

**CFG order says:** state_write (2) before external_call (3) -- **WRONG**

**Dominance says:**
- Node 1 (if) dominates Node 2 (write) and Node 3 (call)
- Node 2 does NOT dominate Node 3 (path exists: false branch skips write)

**Result:** `SOMETIMES_BEFORE` (write is before call only when condition is true)

### Example 3: Bypassable Guard

```solidity
function riskyWithdraw() public {
    if (msg.sender == owner) {
        require(withdrawEnabled);  // Guard at Node 2
    }
    // Path exists: msg.sender != owner -> skip guard
    balances[msg.sender] -= amount;  // Node 3
    transfer(msg.sender, amount);    // Node 4
}
```

**Guard dominance:** `BYPASSABLE` (guard exists but doesn't dominate sink)

## API Reference

### DominanceAnalyzer

```python
class DominanceAnalyzer:
    def __init__(self, nodes, entry_id=None, exit_id=None)
    def compute_dominators() -> Dict[int, Set[int]]
    def compute_post_dominators() -> Dict[int, Set[int]]
    def dominates(a, b) -> bool
    def post_dominates(a, b) -> bool
    def immediate_dominator(node_id) -> Optional[int]
    def compute_ordering(a, b) -> PathQualifiedOrdering
```

### Helper Functions

```python
def extract_cfg_nodes(fn) -> Tuple[List[CFGNodeInfo], int, int]
def create_analyzer_for_function(fn) -> Optional[DominanceAnalyzer]
def compute_modifier_chain_dominance(modifiers) -> ModifierChainSummary
def compute_internal_call_summary(callee_fn) -> InternalCallSummary
```

## References

1. Cooper, Harvey, Kennedy. "A Simple, Fast Dominance Algorithm."
   Software Practice and Experience, 2001.

2. Appel. "Modern Compiler Implementation." Chapter 19: Dominators.

3. Cytron et al. "Efficiently Computing Static Single Assignment Form
   and the Control Dependence Graph." TOPLAS, 1991.

---

*Document Version: 1.0*
*Phase: 05.9-llm-graph-interface-improvements*
*Module: src/alphaswarm_sol/kg/dominance.py*
