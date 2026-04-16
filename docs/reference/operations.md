# Operations Reference

**Semantic Operations & Edge Types for Vulnerability Detection**

---

## Overview

Operations are semantic abstractions that describe what code *does* rather than how it's named. This enables name-agnostic vulnerability detection.

**Taxonomy Version:** 2.0.0 (Phase 5.9)

---

## Ops Taxonomy Registry

The taxonomy registry provides a canonical mapping for all semantic operations and edge types. It supports:

- **Canonical names**: The authoritative operation/edge names
- **Legacy aliases**: Backward-compatible mappings with deprecation warnings
- **SARIF aliases**: Tool-output normalized names (kebab-case)
- **Short codes**: Compact notation for behavioral signatures
- **Migration rules**: How to update deprecated operations

### Resolution Examples

```python
from alphaswarm_sol.kg.taxonomy import ops_registry, resolve_operation

# Canonical name
resolve_operation("TRANSFERS_VALUE_OUT")  # -> "TRANSFERS_VALUE_OUT"

# SARIF alias (from tool output)
resolve_operation("transfers-eth")  # -> "TRANSFERS_VALUE_OUT"

# Legacy alias (with deprecation warning)
resolve_operation("TRANSFERS_ETH")  # -> "TRANSFERS_VALUE_OUT"

# Short code
ops_registry.resolve_short_code("X:out")  # -> "TRANSFERS_VALUE_OUT"
```

### Deprecation Warnings

Deprecated operations emit `DeprecationWarning` with migration guidance:

```python
>>> resolve_operation("TRANSFERS_ETH")
DeprecationWarning: Operation 'TRANSFERS_ETH' is deprecated, use 'TRANSFERS_VALUE_OUT' instead.
Migration: Use TRANSFERS_VALUE_OUT for all value transfers (ETH and tokens)
```

### Deprecated Aliases

| Deprecated | Replacement | Migration |
|------------|-------------|-----------|
| `TRANSFERS_ETH` | `TRANSFERS_VALUE_OUT` | Unified value transfer |
| `TRANSFERS_TOKEN` | `TRANSFERS_VALUE_OUT` | Unified value transfer |
| `TRANSFER_OUT` | `TRANSFERS_VALUE_OUT` | Standardized naming |
| `OWNER_CHANGE` | `MODIFIES_OWNER` | Standardized naming |

---

## Semantic Operations (20 Total)

### Value Movement (4)

| Operation | Short Code | Risk | Description |
|-----------|------------|------|-------------|
| `TRANSFERS_VALUE_OUT` | X:out | 7.0 | ETH or token transfers out |
| `RECEIVES_VALUE_IN` | X:in | 3.0 | Payable functions, token receipts |
| `READS_USER_BALANCE` | R:bal | 2.0 | balances[user], balanceOf() |
| `WRITES_USER_BALANCE` | W:bal | 6.0 | Balance modifications |

### Access Control (3)

| Operation | Short Code | Risk | Description |
|-----------|------------|------|-------------|
| `CHECKS_PERMISSION` | C:auth | 0.0 | require(msg.sender == owner) |
| `MODIFIES_OWNER` | M:own | 8.0 | Ownership transfers |
| `MODIFIES_ROLES` | M:role | 7.0 | Role assignments |

### External Interaction (3)

| Operation | Short Code | Risk | Description |
|-----------|------------|------|-------------|
| `CALLS_EXTERNAL` | X:call | 5.0 | Any external call |
| `CALLS_UNTRUSTED` | X:unk | 8.0 | User-supplied address calls |
| `READS_EXTERNAL_VALUE` | R:ext | 4.0 | External contract reads |

### State Management (3)

| Operation | Short Code | Risk | Description |
|-----------|------------|------|-------------|
| `MODIFIES_CRITICAL_STATE` | M:crit | 7.0 | Privileged state writes |
| `INITIALIZES_STATE` | I:init | 5.0 | Initializer patterns |
| `READS_ORACLE` | R:orc | 4.0 | Oracle reads |

### Control Flow (3)

| Operation | Short Code | Risk | Description |
|-----------|------------|------|-------------|
| `LOOPS_OVER_ARRAY` | L:arr | 4.0 | Array loops (DoS risk) |
| `USES_TIMESTAMP` | U:time | 2.0 | block.timestamp access |
| `USES_BLOCK_DATA` | U:blk | 3.0 | block.number, blockhash |

### Arithmetic (2)

| Operation | Short Code | Risk | Description |
|-----------|------------|------|-------------|
| `PERFORMS_DIVISION` | A:div | 3.0 | Division operations |
| `PERFORMS_MULTIPLICATION` | A:mul | 2.0 | Multiplication operations |

### Validation (2)

| Operation | Short Code | Risk | Description |
|-----------|------------|------|-------------|
| `VALIDATES_INPUT` | V:in | 0.0 | require/assert on params |
| `EMITS_EVENT` | E:evt | 0.0 | Event emissions |

---

## Edge Types

### State Modification

| Type | Risk | Description |
|------|------|-------------|
| `WRITES_STATE` | 3.0 | Writes any state variable |
| `WRITES_CRITICAL_STATE` | 7.0 | Writes owner/admin/role vars |
| `WRITES_BALANCE` | 6.0 | Writes balance-related state |

### State Reading

| Type | Risk | Description |
|------|------|-------------|
| `READS_STATE` | 1.0 | Reads any state variable |
| `READS_BALANCE` | 2.0 | Reads balance-related state |
| `READS_ORACLE` | 3.0 | Reads from oracle contract |

### External Calls

| Type | Risk | Description |
|------|------|-------------|
| `CALLS_EXTERNAL` | 5.0 | Any external contract call |
| `CALLS_UNTRUSTED` | 8.0 | Call to untrusted address |
| `DELEGATECALL` | 9.0 | delegatecall operation |
| `STATICCALL` | 2.0 | staticcall operation |

### Value Transfer

| Type | Risk | Description |
|------|------|-------------|
| `TRANSFERS_ETH` | 7.0 | Transfers native ETH |
| `TRANSFERS_TOKEN` | 6.0 | Transfers ERC20/721 tokens |

### Taint Propagation

| Type | Risk | Description |
|------|------|-------------|
| `INPUT_TAINTS_STATE` | 4.0 | User input flows to state |
| `EXTERNAL_TAINTS` | 5.0 | External data taints state |

### Containment (Structural)

| Type | Description |
|------|-------------|
| `CONTAINS_FUNCTION` | Contract contains function |
| `CONTAINS_STATE` | Contract contains state var |
| `CONTAINS_EVENT` | Contract contains event |
| `CONTAINS_MODIFIER` | Contract contains modifier |
| `FUNCTION_HAS_INPUT` | Function has parameter |
| `FUNCTION_HAS_LOOP` | Function has loop construct |

### Function Relationships

| Type | Description |
|------|-------------|
| `CALLS_INTERNAL` | Internal function call |
| `USES_MODIFIER` | Function uses modifier |

### Meta-Edges (Graph Intelligence)

| Type | Description |
|------|-------------|
| `SIMILAR_TO` | Similar code pattern detected |
| `BUGGY_PATTERN_MATCH` | Matches known bug pattern |
| `REFACTOR_CANDIDATE` | Code could be refactored |

---

## Risk Score Calculation

Risk scores (0-10) are computed based on:

```
base_risk + context_modifiers + guard_adjustments
```

**Context Modifiers:**
- `+2.0` if in delegatecall context
- `+1.5` if tainted data involved
- `+1.0` if transfers value
- `+2.5` if after external call (CEI violation)
- `-3.0` if guarded by access control

**Example:**
```
WRITES_CRITICAL_STATE (7.0)
  + after_external_call (+2.5)
  - has_access_gate (-3.0)
  = 6.5 risk score
```

---

## Taint Sources

| Source | Description |
|--------|-------------|
| `user_input` | Function parameters |
| `external_call` | Return from external call |
| `storage` | State variable read |
| `msg.sender` | Transaction sender |
| `msg.value` | Transaction value |
| `block_data` | Block timestamp/number |
| `oracle` | Oracle price data |

---

## Execution Contexts

| Context | Description |
|---------|-------------|
| `normal` | Standard call context |
| `delegatecall` | delegatecall context |
| `staticcall` | staticcall context |
| `constructor` | Contract constructor |
| `fallback` | Fallback function |
| `receive` | Receive function |

---

## Rich Edge Schema

```python
RichEdge:
  id: str                    # Unique edge identifier
  type: str                  # Edge type (see above)
  source: str                # Source node ID
  target: str                # Target node ID

  # Risk Assessment
  risk_score: float          # 0-10 scale
  pattern_tags: list[str]    # ["reentrancy", "cei_violation"]

  # Execution Context
  execution_context: str     # "normal", "delegatecall", etc.

  # Taint Information
  taint_source: str          # Origin of tainted data
  taint_confidence: float    # 0-1 confidence

  # Temporal Ordering (CFG-based)
  happens_before: list[str]  # Edge IDs this precedes
  happens_after: list[str]   # Edge IDs this follows
  cfg_order: int             # Position in CFG

  # Guard Analysis
  guards_at_source: list[str]   # Active protections
  guards_bypassed: list[str]    # Bypassed guards

  # Value Transfer
  transfers_value: bool
  value_amount: str          # "msg.value", "amount", etc.

  # Evidence
  evidence: list[Evidence]
```

---

## Pattern Matching with Operations

### Using in YAML Patterns

```yaml
id: reentrancy-basic
match:
  tier_a:
    all:
      - has_operation: TRANSFERS_ETH
      - has_operation: WRITES_BALANCE
      - sequence_order:
          before: TRANSFERS_ETH
          after: WRITES_BALANCE
    none:
      - property: has_reentrancy_guard
        value: true
```

### Sequence Ordering

```yaml
# Operation A happens before B
- sequence_order:
    before: CALLS_EXTERNAL
    after: WRITES_STATE

# Operation happens first
- sequence_first: CHECKS_PERMISSION

# Operation happens last
- sequence_last: TRANSFERS_ETH
```

### Operation Sets

```yaml
# All required
- has_all_operations:
    - TRANSFERS_ETH
    - WRITES_BALANCE

# Any required
- has_any_operation:
    - CALLS_EXTERNAL
    - DELEGATECALL
```

---

## Query Examples

### Find High-Risk Edges

```sql
MATCH (f:Function)-[e:CALLS_EXTERNAL]->(target)
WHERE e.risk_score > 7.0
RETURN f.label, target, e.risk_score
```

### Find CEI Violations

```sql
MATCH (f:Function)-[w:WRITES_STATE]->(s:StateVariable),
      (f)-[c:CALLS_EXTERNAL]->(ext)
WHERE c.cfg_order < w.cfg_order
  AND NOT f.has_reentrancy_guard
RETURN f.label, s.label
```

### Find Unguarded Value Transfers

```sql
MATCH (f:Function)-[t:TRANSFERS_ETH]->()
WHERE NOT f.has_access_gate
RETURN f.label, t.value_amount
```

---

## Operation Detection

Operations are detected from Slither IR analysis:

| Slither IR | Operation |
|------------|-----------|
| `HighLevelCall` | `CALLS_EXTERNAL` |
| `LowLevelCall(.call)` | `CALLS_EXTERNAL` |
| `LowLevelCall(.delegatecall)` | `DELEGATECALL` |
| `Transfer` | `TRANSFERS_ETH` |
| `StateVariableWrite` | `WRITES_STATE` |
| `StateVariableRead` | `READS_STATE` |

---

## SARIF Integration

The taxonomy registry provides SARIF-normalized operation names for cross-tool integration. These kebab-case aliases map to canonical operations:

| SARIF Name | Canonical Operation |
|------------|---------------------|
| `transfers-eth` | `TRANSFERS_VALUE_OUT` |
| `transfers-token` | `TRANSFERS_VALUE_OUT` |
| `reads-balance` | `READS_USER_BALANCE` |
| `writes-balance` | `WRITES_USER_BALANCE` |
| `calls-external` | `CALLS_EXTERNAL` |
| `calls-untrusted` | `CALLS_UNTRUSTED` |
| `reads-oracle` | `READS_ORACLE` |
| `modifies-owner` | `MODIFIES_OWNER` |
| `modifies-roles` | `MODIFIES_ROLES` |
| `checks-auth` | `CHECKS_PERMISSION` |
| `performs-division` | `PERFORMS_DIVISION` |
| `emits-event` | `EMITS_EVENT` |

### Resolution

```python
from alphaswarm_sol.kg.taxonomy import ops_registry

# Resolve SARIF name from tool output
canonical = ops_registry.resolve_sarif_operation("transfers-eth")
# -> "TRANSFERS_VALUE_OUT"
```

---

## Pattern Tags

Operations are associated with pattern tags for vulnerability detection:

| Operation | Pattern Tags |
|-----------|--------------|
| `TRANSFERS_VALUE_OUT` | reentrancy, value_movement, cei_violation |
| `WRITES_USER_BALANCE` | reentrancy, cei_violation, balance_update |
| `CALLS_UNTRUSTED` | reentrancy, untrusted_call, arbitrary_call |
| `CALLS_EXTERNAL` | reentrancy, external_call |
| `READS_ORACLE` | oracle_dependency, price_manipulation |
| `LOOPS_OVER_ARRAY` | dos, gas_limit, unbounded_operation |
| `CHECKS_PERMISSION` | access_control, guard |
| `VALIDATES_INPUT` | input_validation, guard |

### Usage in Pattern Matching

```python
from alphaswarm_sol.kg.operations import get_operation_pattern_tags

# Get tags for pattern matching
tags = get_operation_pattern_tags("TRANSFERS_VALUE_OUT")
# -> {"reentrancy", "value_movement", "cei_violation"}
```

---

*See [Properties Reference](properties.md) for node properties.*
*See [Architecture](../architecture.md) for system design.*
