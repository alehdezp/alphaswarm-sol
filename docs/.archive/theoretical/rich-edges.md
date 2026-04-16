# Rich Edge Intelligence

**Edge Metadata, Risk Scoring, and Meta-Edges**

---

## Overview

Traditional graph edges are binary: they exist or they don't. **Rich Edges** in AlphaSwarm.sol carry extensive metadata that enables sophisticated vulnerability detection:

- **Risk scores** (0-10) based on context
- **Pattern tags** for vulnerability classification
- **Execution context** (normal, delegatecall, etc.)
- **Taint information** for dataflow tracking
- **Temporal ordering** for operation sequencing
- **Guard tracking** for access control analysis
- **Value transfer** metadata

This intelligence dramatically improves precision by distinguishing between safe and unsafe edge traversals.

---

## Rich Edge Schema

**Location:** `src/alphaswarm_sol/kg/rich_edge.py`

```python
@dataclass
class RichEdge:
    # Core identity
    id: str                       # Unique edge ID
    type: str                     # Edge type (WRITES_STATE, CALLS_EXTERNAL, etc.)
    source: str                   # Source node ID
    target: str                   # Target node ID

    # Risk assessment
    risk_score: float             # 0-10 scale
    pattern_tags: list[str]       # ["reentrancy", "cei_violation"]

    # Execution context
    execution_context: str        # "normal", "delegatecall", "staticcall", etc.

    # Taint propagation
    taint_source: str             # "user_input", "external_call", "oracle", etc.
    taint_confidence: float       # 0-1 confidence in taint tracking

    # Temporal ordering (CFG-based)
    happens_before: list[str]     # Edge IDs this precedes
    happens_after: list[str]      # Edge IDs this follows
    cfg_order: int                # Position in control flow

    # Guard analysis
    guards_at_source: list[str]   # Active guards at source node
    guards_bypassed: list[str]    # Guards that can be bypassed

    # Value transfer
    transfers_value: bool         # Whether this edge transfers ETH/tokens
    value_amount: str             # "msg.value", "amount", variable name

    # Evidence
    evidence: list[Evidence]      # Source code locations
```

---

## Edge Types and Base Risk Scores

### State Modification

| Type | Base Risk | Description |
|------|-----------|-------------|
| `WRITES_STATE` | 3.0 | Writes any state variable |
| `WRITES_CRITICAL_STATE` | 7.0 | Writes owner/admin/role variables |
| `WRITES_BALANCE` | 6.0 | Writes user balance mappings |
| `WRITES_CONFIG` | 5.0 | Writes config parameters |

### State Reading

| Type | Base Risk | Description |
|------|-----------|-------------|
| `READS_STATE` | 1.0 | Reads any state variable |
| `READS_BALANCE` | 2.0 | Reads balance mappings |
| `READS_ORACLE` | 3.0 | Reads from oracle contract |

### External Calls

| Type | Base Risk | Description |
|------|-----------|-------------|
| `CALLS_EXTERNAL` | 5.0 | Any external contract call |
| `CALLS_UNTRUSTED` | 8.0 | Call to untrusted/user-provided address |
| `DELEGATECALL` | 9.0 | delegatecall operation (storage context) |
| `STATICCALL` | 2.0 | staticcall operation (read-only) |

### Value Transfer

| Type | Base Risk | Description |
|------|-----------|-------------|
| `TRANSFERS_ETH` | 7.0 | Transfers native ETH via .call, .transfer, .send |
| `TRANSFERS_TOKEN` | 6.0 | Transfers ERC20/721/1155 tokens |

### Taint Propagation

| Type | Base Risk | Description |
|------|-----------|-------------|
| `INPUT_TAINTS_STATE` | 4.0 | User input flows to state variable |
| `EXTERNAL_TAINTS` | 5.0 | External call result taints state |

---

## Risk Score Calculation

Base risk is modified by contextual factors:

```
final_risk = base_risk + context_modifiers + guard_adjustments
```

### Context Modifiers

| Condition | Modifier | Reason |
|-----------|----------|--------|
| In delegatecall context | +2.0 | Storage context is dangerous |
| Tainted data involved | +1.5 | User-controlled data increases risk |
| Transfers value | +1.0 | Value transfer = higher impact |
| After external call (CEI violation) | +2.5 | Reentrancy risk |
| In loop | +1.0 | DoS/gas griefing risk |

### Guard Adjustments

| Condition | Modifier | Reason |
|-----------|----------|--------|
| Has access control gate | -3.0 | Protected by authorization |
| Has reentrancy guard | -2.5 | Protected by mutex |
| Has bounds check | -1.0 | Validated inputs |
| Zero-address check | -0.5 | Basic validation |

### Example Calculation

```python
# Example: Writing critical state after external call
base_risk = 7.0  # WRITES_CRITICAL_STATE

# Context modifiers
+2.5  # After external call (CEI violation)
+1.5  # Tainted from user input

# Guard adjustments
-3.0  # Has access control (onlyOwner modifier)

# Final risk
final_risk = 7.0 + 2.5 + 1.5 - 3.0 = 8.0
```

**Result:** High risk despite access control due to CEI violation.

---

## Pattern Tags

Pattern tags classify edges by vulnerability type:

| Tag | Description |
|-----|-------------|
| `reentrancy` | Part of reentrancy attack surface |
| `cei_violation` | Checks-Effects-Interactions pattern violated |
| `unguarded_write` | State write without access control |
| `untrusted_call` | Call to untrusted contract |
| `oracle_manipulation` | Oracle price dependency |
| `dos_vector` | Denial-of-service attack surface |
| `front_running` | MEV/front-running vulnerability |
| `signature_replay` | Signature replay risk |
| `delegatecall_risk` | Dangerous delegatecall |
| `token_interaction` | ERC20/721 interaction |

**Usage in patterns:**

```yaml
id: reentrancy-classic
match:
  tier_a:
    all:
      - edge_has_tag: cei_violation
      - property: has_external_calls
        value: true
```

---

## Execution Contexts

Edges track the execution context in which operations occur:

| Context | Description | Risk Implications |
|---------|-------------|-------------------|
| `normal` | Standard call | Base risk applies |
| `delegatecall` | delegatecall context | +2.0 risk (storage context) |
| `staticcall` | staticcall context | -1.0 risk (read-only) |
| `constructor` | In constructor | Different initialization rules |
| `fallback` | Fallback function | Unpredictable behavior |
| `receive` | Receive function | ETH handling |

**Example:**

```python
# Same WRITES_STATE edge, different contexts
edge1 = RichEdge(
    type="WRITES_STATE",
    execution_context="normal",
    risk_score=3.0
)

edge2 = RichEdge(
    type="WRITES_STATE",
    execution_context="delegatecall",
    risk_score=5.0  # +2.0 for delegatecall context
)
```

---

## Taint Sources

Edges track where tainted data originates:

| Source | Description | Risk |
|--------|-------------|------|
| `user_input` | Function parameters | High |
| `external_call` | Return from external call | High |
| `storage` | State variable read | Medium |
| `msg.sender` | Transaction sender | Medium |
| `msg.value` | Transaction value | Medium |
| `block_data` | Block timestamp/number | Low |
| `oracle` | Oracle price data | High |

**Taint Confidence:**

- `1.0` - Direct taint (parameter → state write)
- `0.8` - One-hop taint (parameter → local var → state)
- `0.6` - Two-hop taint
- `0.4` - Weak taint (complex dataflow)

**Example:**

```python
edge = RichEdge(
    type="WRITES_STATE",
    taint_source="user_input",
    taint_confidence=0.9,
    risk_score=6.5  # Elevated due to taint
)
```

---

## Temporal Ordering

Edges include CFG-based ordering for detecting operation sequences:

```python
# Reentrancy: CALLS_EXTERNAL before WRITES_STATE
edge_call = RichEdge(
    id="edge_001",
    type="CALLS_EXTERNAL",
    cfg_order=10,
    happens_before=["edge_002"]
)

edge_write = RichEdge(
    id="edge_002",
    type="WRITES_STATE",
    cfg_order=15,
    happens_after=["edge_001"]
)
```

**Pattern matching with ordering:**

```yaml
match:
  tier_a:
    all:
      - sequence_order:
          before: CALLS_EXTERNAL
          after: WRITES_STATE
```

---

## Guard Tracking

Edges track which guards are active and which can be bypassed:

```python
edge = RichEdge(
    type="WRITES_CRITICAL_STATE",
    guards_at_source=["onlyOwner", "whenNotPaused"],
    guards_bypassed=[],  # All guards active
    risk_score=4.0  # Reduced from 7.0 due to guards
)

# vs.

edge_unguarded = RichEdge(
    type="WRITES_CRITICAL_STATE",
    guards_at_source=[],
    guards_bypassed=[],
    risk_score=7.0  # Full risk, no protection
)
```

**Bypass detection:**

```python
# Guard can be bypassed if:
# 1. Uses tx.origin instead of msg.sender
# 2. Role can be self-granted
# 3. Timelock can be bypassed

edge_bypassed = RichEdge(
    type="WRITES_CRITICAL_STATE",
    guards_at_source=["onlyOwner"],
    guards_bypassed=["uses_tx_origin"],  # Phishable!
    risk_score=6.5  # Still high risk
)
```

---

## Meta-Edges

Meta-edges connect nodes based on **semantic similarity** rather than code structure:

| Type | Description | Use Case |
|------|-------------|----------|
| `SIMILAR_TO` | Structural/behavioral similarity | Find similar vulnerabilities |
| `BUGGY_PATTERN_MATCH` | Matches known exploit pattern | Cross-contract learning |
| `ENABLES_ATTACK` | State change enables attack | Multi-step exploits |
| `REFACTOR_CANDIDATE` | Similar code that could be unified | Code quality |

### SIMILAR_TO

```python
# Two functions with similar behavioral signatures
meta_edge = RichEdge(
    type="SIMILAR_TO",
    source="contract1:withdraw",
    target="contract2:removeFunds",
    risk_score=compute_similarity_risk(fn1, fn2),
    pattern_tags=["behavioral_similarity"],
    evidence=[Evidence(
        description="Both functions: R:bal→X:out→W:bal signature",
        similarity_score=0.92
    )]
)
```

### BUGGY_PATTERN_MATCH

```python
# Function matches known exploit pattern
meta_edge = RichEdge(
    type="BUGGY_PATTERN_MATCH",
    source="my_contract:withdraw",
    target="exploit:dao_hack_2016",
    risk_score=9.0,
    pattern_tags=["known_exploit"],
    evidence=[Evidence(
        description="Matches DAO hack pattern: CEI violation with callback",
        cve="CVE-2016-xxxx"
    )]
)
```

### ENABLES_ATTACK

```python
# State transition enables subsequent attack
meta_edge = RichEdge(
    type="ENABLES_ATTACK",
    source="setState",
    target="exploitState",
    risk_score=7.5,
    pattern_tags=["state_dependency"],
    evidence=[Evidence(
        description="setState() disables guard, enabling exploitState()"
    )]
)
```

---

## Query Examples

### Find High-Risk Edges

```python
from alphaswarm_sol.kg.schema import KnowledgeGraph

graph = KnowledgeGraph.load("project/.vrs/graphs/graph.json")

# Find edges with risk > 7.0
high_risk = [
    edge for edge in graph.edges
    if edge.risk_score > 7.0
]

for edge in high_risk:
    print(f"{edge.source} --[{edge.type}]--> {edge.target}")
    print(f"  Risk: {edge.risk_score}")
    print(f"  Tags: {edge.pattern_tags}")
```

### Find CEI Violations

```python
# Find state writes after external calls
cei_violations = []

for edge_write in graph.edges:
    if edge_write.type == "WRITES_STATE":
        # Check if any external call precedes this write
        for edge_call in graph.edges:
            if (edge_call.type == "CALLS_EXTERNAL" and
                edge_call.cfg_order < edge_write.cfg_order and
                edge_call.source == edge_write.source):
                cei_violations.append((edge_call, edge_write))
```

### Find Unguarded Value Transfers

```python
# Find ETH transfers without access control
unguarded = [
    edge for edge in graph.edges
    if edge.type == "TRANSFERS_ETH"
    and not edge.guards_at_source
]
```

### Find Tainted State Writes

```python
# Find user input flowing to state
tainted_writes = [
    edge for edge in graph.edges
    if edge.type == "WRITES_STATE"
    and edge.taint_source == "user_input"
    and edge.taint_confidence > 0.7
]
```

---

## CLI Usage

```bash
# Query high-risk edges
uv run alphaswarm query "FIND edges WHERE risk_score > 8.0"

# Find edges by pattern tag
uv run alphaswarm query "FIND edges WHERE pattern_tags CONTAINS 'reentrancy'"

# Find edges by taint source
uv run alphaswarm query "FIND edges WHERE taint_source = 'user_input'"

# Find unguarded edges
uv run alphaswarm query "FIND edges WHERE guards_at_source IS EMPTY"
```

---

## Implementation Details

**Edge Creation:**

```python
# In VKGBuilder
def _create_rich_edge(
    self,
    source: Node,
    target: Node,
    edge_type: str
) -> RichEdge:
    base_risk = self.BASE_RISK_SCORES[edge_type]

    # Compute context modifiers
    context = self._get_execution_context(source)
    risk_modifier = self.CONTEXT_MODIFIERS.get(context, 0.0)

    # Check guards
    guards = self._detect_guards(source)
    guard_adjustment = -3.0 if guards else 0.0

    # Check taint
    taint_info = self._trace_taint(source, target)
    taint_modifier = 1.5 if taint_info['tainted'] else 0.0

    # Final risk
    final_risk = base_risk + risk_modifier + guard_adjustment + taint_modifier

    return RichEdge(
        type=edge_type,
        source=source.id,
        target=target.id,
        risk_score=min(final_risk, 10.0),
        execution_context=context,
        guards_at_source=guards,
        taint_source=taint_info['source'],
        taint_confidence=taint_info['confidence']
    )
```

---

## Testing

**Location:** `tests/test_rich_edges.py`

```bash
# Test rich edge creation
uv run pytest tests/test_rich_edges.py::test_edge_risk_scoring -v

# Test taint tracking
uv run pytest tests/test_rich_edges.py::test_taint_propagation -v

# Test guard detection
uv run pytest tests/test_rich_edges.py::test_guard_tracking -v

# Test temporal ordering
uv run pytest tests/test_rich_edges.py::test_temporal_ordering -v
```

---

## Performance Impact

| Feature | Overhead |
|---------|----------|
| Risk scoring | ~5% build time |
| Taint tracking | ~10% build time |
| Temporal ordering | ~5% build time |
| Guard detection | ~8% build time |
| **Total** | **~28% build time** |

**Trade-off:** 28% slower builds for 5x better precision.

---

## Pattern-Scoped Slicing and Omission Reporting (Phase 5.10-04)

Pattern-scoped slicing v2 provides edge-closure traversal with explicit omission tracking. When edges are excluded during slicing, the omission entries include both `edge_id` and `edge_type` for debugging.

### Typed Omission Entries

```python
@dataclass(frozen=True)
class TypedOmissionEntry:
    """An omission entry with edge type for debugging."""
    edge_id: str       # e.g., "e-0x1234"
    edge_type: str     # e.g., "calls", "writes_state", "external_call"
    reason: OmissionReason  # DEPTH_LIMIT, BUDGET_EXCEEDED, etc.
    details: str       # Human-readable details
```

**Omission Reasons:**
- `EDGE_CLOSURE_EXCLUDED` - Edge not reachable from seed nodes
- `DEPTH_LIMIT` - Edge beyond max_hops traversal depth
- `BUDGET_EXCEEDED` - Edge pruned due to node budget
- `REQUIRED_OP_MISSING` - Node missing required semantic operations
- `WITNESS_MISSING` - Expected witness evidence not found
- `ANTI_SIGNAL_EXCLUDED` - Edge excluded due to guard/mitigation

### Witness Extraction

Witnesses are the minimal proof subgraph required for pattern matches:

```python
@dataclass
class WitnessEvidence:
    evidence_ids: List[str]   # Sorted deterministically
    node_ids: List[str]       # Sorted by node ID
    edge_ids: List[str]       # Sorted by edge ID
    operations: List[str]     # Sorted alphabetically
```

**Determinism guarantees:**
- All witness lists are sorted for reproducibility
- Same inputs produce identical witnesses across builds
- Witness extraction is independent of graph traversal order

### Negative Witnesses

Negative witnesses track what must NOT exist for a pattern to match:

```python
@dataclass
class NegativeWitness:
    guard_types: List[str]           # ["reentrancy_guard", "access_control"]
    excluded_operations: List[str]   # Forbidden semantic ops
    guard_evidence_ids: List[str]    # Evidence of guards found
```

### Usage Example

```python
from alphaswarm_sol.kg.slicer import (
    PatternSliceFocus,
    slice_graph_for_pattern_focus,
)

# Create focus from PCP v2
focus = PatternSliceFocus(
    required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
    anti_signal_guard_types=["reentrancy_guard"],
    max_edge_hops=2,
)

# Slice with edge-closure
result = slice_graph_for_pattern_focus(
    graph=kg,
    focus=focus,
    focal_nodes=["F-withdraw"],
    category="reentrancy",
)

# Check completeness
if result.is_complete:
    print("All required evidence found")
else:
    print(f"Missing ops: {result.missing_required_ops}")

# Inspect omissions with edge types
for omission in result.typed_omissions:
    print(f"Excluded: {omission.edge_id} ({omission.edge_type}) - {omission.reason.value}")
```

---

*See [Operations Reference](operations.md) for edge types and base risk scores.*
*See [Agents Reference](agents.md) for how agents use rich edge metadata.*
*See [Graph Schema](../architecture/graph-schema.md) for full schema definition.*
