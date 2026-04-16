# VQL Query Library

VQL (Vulnerability Query Language) is a declarative query language for the BSKG (Behavioral Security Knowledge Graph). This document describes the minimum query set required for graph-first vulnerability detection.

## Overview

The VQL minimum set provides 8 core queries organized into three categories:

| Category | Queries | Description |
|----------|---------|-------------|
| Structural | VQL-MIN-01 to 03 | Basic graph topology queries |
| Semantic | VQL-MIN-04 to 06 | Operation-based pattern queries |
| Path | VQL-MIN-07 to 08 | Multi-hop attack path queries |

## Query Tiers

Queries are classified by detection tier:

- **Tier A**: Graph-only, deterministic. Results come directly from graph queries without LLM involvement.
- **Tier B**: Requires path enumeration or pattern matching. May need LLM verification.
- **Tier C**: Label-dependent. Requires semantic labels that may need LLM inference.

## Structural Queries

### VQL-MIN-01: Function Entry Points

**Purpose:** Find public/external functions that serve as entry points to the contract.

**Query:**
```yaml
select:
  - node_id, label, visibility, has_protection, file, line_start
from:
  - alias: fn, type: Function
where:
  - fn.properties.visibility IN ['public', 'external']
  - fn.properties.is_constructor == false
```

**Use Cases:**
- Identify attack surface
- Find unprotected entry points (filter: `has_protection == false`)
- Find payable entry points (filter: `fn.properties.payable == true`)

**Example Output:**
```json
[
  {
    "node_id": "fn:0x1234abcd",
    "label": "withdraw",
    "visibility": "external",
    "has_protection": false,
    "file": "contracts/Vault.sol",
    "line_start": 45
  }
]
```

### VQL-MIN-02: External Calls

**Purpose:** Find all external call targets and their resolution status.

**Query:**
```yaml
select:
  - source_id, target_id, source_label, call_type, confidence, target_label
from:
  - alias: edge, type_edge: CALLS
  - alias: src_fn, type: Function (join on edge.source)
  - alias: tgt_fn, type: Function (join on edge.target)
where:
  - edge.properties.call_type IN ['external', 'delegatecall', 'staticcall']
```

**Use Cases:**
- Map external dependencies
- Find delegatecall targets (high risk)
- Identify low-confidence resolutions (may hide vulnerabilities)

### VQL-MIN-03: State Writes

**Purpose:** Find functions that modify state and their write targets.

**Query:**
```yaml
select:
  - fn_id, fn_label, state_var_id, state_var_name, is_privileged, is_balance
from:
  - alias: edge, type_edge: WRITES
  - alias: fn, type: Function
  - alias: sv, type: StateVariable
where:
  - fn.properties.visibility IN ['public', 'external']
```

**Use Cases:**
- Identify state-changing functions
- Find functions that write privileged state (filter: `is_privileged == true`)
- Find functions that modify balances (filter: `is_balance == true`)

## Semantic Queries

### VQL-MIN-04: Reentrancy Pattern

**Purpose:** Detect the classic reentrancy pattern: Read balance -> External call -> Write balance.

**Behavioral Signature:** `R:bal -> X:out -> W:bal`

**Query:**
```yaml
select:
  - fn_id, fn_label, behavioral_signature, has_reentrancy_guard
from:
  - alias: fn, type: Function
where:
  - fn.properties.semantic_ops CONTAINS 'READS_USER_BALANCE'
  - fn.properties.semantic_ops CONTAINS 'TRANSFERS_VALUE_OUT'
  - fn.properties.semantic_ops CONTAINS 'WRITES_USER_BALANCE'
  - fn.properties.state_write_after_external_call == true
```

**Vulnerability:**
- Type: Reentrancy
- Severity: HIGH
- CWE: CWE-841
- SWC: SWC-107

**Safe Pattern:** `R:bal -> W:bal -> X:out` (Check-Effects-Interactions)

### VQL-MIN-05: Access Control Gap

**Purpose:** Detect unprotected state modifications (missing access control).

**Query:**
```yaml
select:
  - fn_id, fn_label, modifiers, modifies_owner, modifies_critical_state
from:
  - alias: fn, type: Function
where:
  - fn.properties.visibility IN ['public', 'external']
  - (semantic_ops CONTAINS 'MODIFIES_OWNER' OR 'MODIFIES_ROLES' OR 'MODIFIES_CRITICAL_STATE')
  - fn.properties.has_access_control == false
```

**Vulnerability:**
- Type: Missing Access Control
- Severity: CRITICAL
- CWE: CWE-284
- SWC: SWC-105

### VQL-MIN-06: Value Transfer Without Check

**Purpose:** Detect unprotected value transfers.

**Query:**
```yaml
select:
  - fn_id, fn_label, transfer_type, has_access_control
from:
  - alias: fn, type: Function
where:
  - fn.properties.visibility IN ['public', 'external']
  - fn.properties.semantic_ops CONTAINS 'TRANSFERS_VALUE_OUT'
  - fn.properties.has_access_control == false
  - fn.properties.semantic_ops NOT CONTAINS 'VALIDATES_INPUT'
```

**Vulnerability:**
- Type: Unauthorized Transfer
- Severity: HIGH
- CWE: CWE-862
- SWC: SWC-105

## Path Queries

### VQL-MIN-07: Cross-Function Flow

**Purpose:** Find multi-hop attack paths through function calls.

**Query:**
```yaml
path:
  start:
    type: Function
    where: visibility IN ['public', 'external']
  edges:
    type: CALLS
    min_hops: 2
    max_hops: 3
  end:
    type: Function
    where: has_external_calls == true OR writes_privileged_state == true
select:
  - path_id, start_fn, end_fn, hop_count, path_risk
where:
  - path.cumulative_risk >= 3.0
```

**Use Cases:**
- Find privilege escalation paths
- Identify indirect attack vectors
- Map cross-contract attack surfaces

### VQL-MIN-08: Callback Reachability

**Purpose:** Find callback attack surfaces (flash loans, ERC-777, etc.).

**Query:**
```yaml
path:
  start:
    type: Function
    where: label IN ['onFlashLoan', 'tokensReceived', 'uniswapV2Call', ...]
  edges:
    type: CALLS
    min_hops: 0
    max_hops: 3
  end:
    type: Function
    where: writes_balance_state == true OR modifies_critical_state == true
select:
  - callback_fn, callback_type, target_fn, has_reentrancy_guard
where:
  - path.end.properties.has_reentrancy_guard == false
```

**Vulnerability:**
- Type: Callback Reentrancy
- Severity: HIGH
- CWE: CWE-841
- SWC: SWC-107

## Semantic Operations Reference

### Value Movement
| Operation | Short Code | Description |
|-----------|------------|-------------|
| `TRANSFERS_VALUE_OUT` | `X:out` | ETH or token transfers out |
| `RECEIVES_VALUE_IN` | `X:in` | Payable functions, token receipts |
| `READS_USER_BALANCE` | `R:bal` | Balance reads |
| `WRITES_USER_BALANCE` | `W:bal` | Balance modifications |

### Access Control
| Operation | Short Code | Description |
|-----------|------------|-------------|
| `CHECKS_PERMISSION` | `C:auth` | Permission checks |
| `MODIFIES_OWNER` | `M:own` | Ownership transfers |
| `MODIFIES_ROLES` | `M:role` | Role assignments |

### External Interaction
| Operation | Short Code | Description |
|-----------|------------|-------------|
| `CALLS_EXTERNAL` | `X:call` | Any external call |
| `CALLS_UNTRUSTED` | `X:unk` | Calls to user-supplied addresses |
| `READS_EXTERNAL_VALUE` | `R:ext` | Reading from external contracts |

### State Management
| Operation | Short Code | Description |
|-----------|------------|-------------|
| `MODIFIES_CRITICAL_STATE` | `M:crit` | Privileged state writes |
| `INITIALIZES_STATE` | `I:init` | Initializer patterns |
| `READS_ORACLE` | `R:orc` | Oracle reads |

## Behavioral Signatures

Behavioral signatures are compact notations for operation sequences:

| Signature | Pattern | Risk |
|-----------|---------|------|
| `R:bal->X:out->W:bal` | Vulnerable reentrancy | HIGH |
| `R:bal->W:bal->X:out` | Safe CEI pattern | LOW |
| `M:crit` (no `C:auth`) | Missing access control | CRITICAL |
| `R:orc->A:mul->X:out` | Oracle manipulation risk | HIGH |

## Query Composition

Queries can be composed for comprehensive analysis:

```yaml
# Full reentrancy detection
compositions:
  reentrancy_comprehensive:
    queries:
      - "VQL-MIN-04"  # Direct pattern
      - "VQL-MIN-08"  # Callback paths
    combine: "UNION"
    deduplicate_by: "fn_id"
```

## Validation

Validate queries before execution:

```bash
# Validate all VQL queries
python scripts/validate_vql_queries.py

# Validate with dry-run on sample contract
python scripts/validate_vql_queries.py --dry-run tests/contracts/Reentrancy.sol
```

## Integration with Agents

VQL queries are used by investigation agents:

1. **vrs-attacker**: Runs VQL-MIN-04, VQL-MIN-08 to find attack paths
2. **vrs-defender**: Runs VQL-MIN-01, VQL-MIN-05 to find mitigations
3. **vrs-verifier**: Validates findings against VQL query results

## Schema Reference

Full BSKG schema: `.vrs/schema/bskg-schema.yaml`

Query library: `src/alphaswarm_sol/kg/queries/vql_minimum_set.yaml`
