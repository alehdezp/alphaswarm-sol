# Graph Schema

**Node Types, Edge Types, and Property Reference**

---

## Node Types

### Contract

Represents a Solidity contract.

| Property | Type | Description |
|----------|------|-------------|
| `kind` | string | "contract", "library", "interface" |
| `is_proxy_like` | bool | Detected as proxy pattern |
| `proxy_type` | string | "UUPS", "Transparent", "Beacon", etc. |
| `has_initializer` | bool | Has initialize() function |
| `has_storage_gap` | bool | Has __gap for upgrades |

### Function

Primary analysis target with 50+ security properties.

**Core Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `visibility` | string | "public", "external", "internal", "private" |
| `state_mutability` | string | "view", "pure", "payable", "nonpayable" |
| `is_constructor` | bool | Constructor function |
| `is_fallback` | bool | Fallback function |
| `is_receive` | bool | Receive function |
| `modifiers` | list | Applied modifier names |
| `signature` | string | Function signature |

**Access Control:**

| Property | Type | Description |
|----------|------|-------------|
| `has_access_gate` | bool | Has auth modifier or inline check |
| `access_gate_modifiers` | list | Auth modifier names |
| `writes_privileged_state` | bool | Writes owner/admin/role vars |
| `uses_tx_origin` | bool | Uses tx.origin (phishing risk) |
| `uses_msg_sender` | bool | Uses msg.sender |

**Reentrancy:**

| Property | Type | Description |
|----------|------|-------------|
| `state_write_after_external_call` | bool | CEI violation |
| `state_write_before_external_call` | bool | Safe CEI pattern |
| `has_reentrancy_guard` | bool | Has nonReentrant |

**External Calls:**

| Property | Type | Description |
|----------|------|-------------|
| `has_external_calls` | bool | Any external call (including low-level) |
| `uses_delegatecall` | bool | Uses delegatecall |
| `uses_call` | bool | Uses low-level call |
| `low_level_calls` | list | Call details |
| `external_call_count` | int | Number of external calls |

**DoS:**

| Property | Type | Description |
|----------|------|-------------|
| `has_unbounded_loop` | bool | Loop with user-controlled bounds |
| `has_require_bounds` | bool | Has require() bounding loops |
| `external_calls_in_loop` | bool | External call inside loop |
| `has_unbounded_deletion` | bool | Unbounded delete in loop |
| `uses_transfer` | bool | Uses .transfer() (2300 gas) |
| `uses_send` | bool | Uses .send() (2300 gas) |
| `has_strict_equality_check` | bool | Strict == on balance |

**Crypto/Signatures:**

| Property | Type | Description |
|----------|------|-------------|
| `uses_ecrecover` | bool | Uses signature recovery |
| `checks_zero_address` | bool | Validates ecrecover != 0 |
| `checks_sig_s` | bool | Checks s for malleability |
| `uses_chainid` | bool | Includes chain ID |
| `has_nonce_parameter` | bool | Has nonce in signature |
| `has_deadline_check` | bool | Validates deadline |

**MEV:**

| Property | Type | Description |
|----------|------|-------------|
| `swap_like` | bool | Looks like swap function |
| `risk_missing_slippage_parameter` | bool | Swap without slippage |
| `risk_missing_deadline_check` | bool | Swap without deadline |
| `has_slippage_parameter` | bool | Has minAmountOut |
| `has_slippage_check` | bool | Validates slippage |

**Oracle:**

| Property | Type | Description |
|----------|------|-------------|
| `reads_oracle_price` | bool | Calls oracle |
| `has_staleness_check` | bool | Validates updatedAt |
| `oracle_freshness_ok` | bool | All oracle checks pass |
| `has_sequencer_uptime_check` | bool | L2 sequencer check |

**Tokens:**

| Property | Type | Description |
|----------|------|-------------|
| `uses_erc20_transfer` | bool | Calls transfer() |
| `uses_erc20_transfer_from` | bool | Calls transferFrom() |
| `token_return_guarded` | bool | Checks return value |
| `uses_safe_erc20` | bool | Uses SafeERC20 |

**Invariants:**

| Property | Type | Description |
|----------|------|-------------|
| `touches_invariant` | bool | Reads/writes invariant state |
| `has_invariant_check` | bool | Has require validating invariant |
| `touches_invariant_unchecked` | bool | Touches without checking |

**Upgradeability:**

| Property | Type | Description |
|----------|------|-------------|
| `is_upgrade_function` | bool | Upgrade function |
| `is_initializer_function` | bool | Initializer function |
| `upgrade_guarded` | bool | Has auth on upgrade |

**Semantic Operations (20+):**

| Property | Type | Description |
|----------|------|-------------|
| `semantic_ops` | list[str] | Detected semantic operations |
| `op_sequence` | list[dict] | Operations with CFG order |
| `behavioral_signature` | string | Operation sequence (e.g., "R:bal→X:out→W:bal") |
| `op_ordering` | list[tuple] | Before/after operation pairs |

**Hierarchical Classification:**

| Property | Type | Description |
|----------|------|-------------|
| `semantic_role` | string | Guardian, Checkpoint, EscapeHatch, EntryPoint, Internal |
| `risk_profile` | dict | Categorized risks |
| `attack_surface_score` | float | 0-10 overall risk score |

### StateVariable

Contract state variables.

| Property | Type | Description |
|----------|------|-------------|
| `type` | string | Solidity type |
| `visibility` | string | public, internal, private |
| `security_tags` | list | owner, balance, paused, etc. |
| `is_constant` | bool | Constant variable |
| `is_immutable` | bool | Immutable variable |

**Security Tags:**
- `owner`, `admin`, `role`, `guardian` - Authority
- `paused`, `locked`, `frozen` - Circuit breakers
- `fee`, `rate`, `treasury` - Value movement
- `whitelist`, `blacklist` - Access lists
- `nonce`, `used`, `claimed` - Replay protection

### Input

Function parameters and environment sources.

| Property | Type | Description |
|----------|------|-------------|
| `kind` | string | "parameter", "env" |
| `name` | string | Parameter name |
| `type` | string | Solidity type |

**Environment Sources:**
- `msg.sender`, `msg.value`, `msg.data`
- `block.timestamp`, `block.number`
- `tx.origin`, `tx.gasprice`

### Loop

Loop constructs for DoS analysis.

| Property | Type | Description |
|----------|------|-------------|
| `bound_sources` | list | What controls the bound |
| `has_external_call` | bool | External call in body |
| `has_delete` | bool | Delete operation in body |
| `is_bounded` | bool | Has fixed or validated bound |

### Invariant

Formal properties from NatSpec.

| Property | Type | Description |
|----------|------|-------------|
| `text` | string | Full invariant text |
| `source_kind` | string | "natspec", "config" |
| `target_type` | string | Contract, Function, StateVariable |
| `state_vars` | list | Referenced state variables |

### ExternalCallSite

Low-level call tracking.

| Property | Type | Description |
|----------|------|-------------|
| `call_kind` | string | "call", "delegatecall", "staticcall" |
| `has_call_value` | bool | Sends ETH |
| `destination` | string | Call target |

### ExecutionPath (IMPLEMENTED)

Multi-step attack sequences detected by path analysis engine.

**Location:** `src/alphaswarm_sol/kg/paths.py`

| Property | Type | Description |
|----------|------|-------------|
| `entry_point` | string | Starting function |
| `steps` | list[PathStep] | Ordered execution steps with operations |
| `state_preconditions` | dict | Required initial state |
| `state_postconditions` | dict | Resulting state |
| `invariants_violated` | list | Broken invariants along path |
| `attack_potential` | float | 0-10 exploitability score |
| `guards_on_path` | list | Access controls encountered |
| `bypass_conditions` | list | Conditions to bypass guards |

**PathStep Structure:**

| Property | Type | Description |
|----------|------|-------------|
| `function_id` | string | Function in this step |
| `operations` | list | Semantic operations performed |
| `state_changes` | dict | State modifications |
| `order` | int | Step number in path |
| `risk_score` | float | Risk added by this step |

### Hierarchical Node Roles (IMPLEMENTED)

Functions and state variables are classified into semantic roles:

**Function Roles:**

| Role | Description | Detection Criteria |
|------|-------------|-------------------|
| `Guardian` | Access control function | Checks permissions, no state writes |
| `Checkpoint` | Critical state mutation | Writes user balances, roles, critical state |
| `EscapeHatch` | Emergency function | Has pause/emergency modifiers |
| `EntryPoint` | Public interaction | Public/external + writes state |
| `Internal` | Helper function | Internal/private |

**State Variable Roles:**

| Role | Description | Detection Criteria |
|------|-------------|-------------------|
| `StateAnchor` | Used in guards | Referenced in require/modifier conditions |
| `CriticalState` | User-facing value | Balance mappings, user deposits |
| `ConfigState` | Admin parameters | Fee rates, limits, admin addresses |
| `InternalState` | Implementation detail | Not user-facing, not in guards |

**Location:** `src/alphaswarm_sol/kg/classification.py`

---

### SubGraph (IMPLEMENTED)

Query-aware graph extraction for efficient analysis.

**Location:** `src/alphaswarm_sol/kg/subgraph.py`

| Property | Type | Description |
|----------|------|-------------|
| `focal_nodes` | list | Center of analysis |
| `nodes` | list | All included nodes |
| `edges` | list | All included edges |
| `relevance_scores` | dict | Node → relevance score |
| `extraction_strategy` | string | "ego", "pattern_based", "risk_based" |
| `max_nodes` | int | Size limit (default: 50) |

### StateTransition (IMPLEMENTED)

Temporal state changes for attack window detection.

**Location:** `src/alphaswarm_sol/kg/temporal.py`

| Property | Type | Description |
|----------|------|-------------|
| `from_state` | dict | Initial state values |
| `to_state` | dict | Final state values |
| `trigger_function` | string | Function causing transition |
| `guard_conditions` | list | Required conditions |
| `enables_attacks` | list | Attack IDs enabled by this transition |
| `timestamp_window` | tuple | (min_time, max_time) for transition |

### ExternalDependency (IMPLEMENTED)

Cross-contract and supply-chain analysis.

**Location:** `src/alphaswarm_sol/kg/supply_chain.py`

| Property | Type | Description |
|----------|------|-------------|
| `interface` | string | Interface name (e.g., "IUniswapV2Router") |
| `known_implementations` | list | Identified implementations |
| `trust_level` | string | "trusted", "semi_trusted", "untrusted" |
| `callback_risk` | bool | Can callback to caller |
| `state_assumptions` | list | Assumptions about external state |
| `compromise_impact` | list | Impact if dependency is malicious |

### VulnerabilityNode (IMPLEMENTED)

Detected vulnerabilities in the graph.

**Location:** `src/alphaswarm_sol/agents/consensus.py`

| Property | Type | Description |
|----------|------|-------------|
| `vulnerability_id` | string | Unique ID |
| `category` | string | "reentrancy", "access_control", etc. |
| `severity` | string | "low", "medium", "high", "critical" |
| `status` | string | "potential", "confirmed", "mitigated" |
| `affected_functions` | list | Vulnerable function IDs |
| `attack_paths` | list | Execution paths exploiting this vuln |
| `consensus_score` | float | Agent agreement (0-1) |
| `agent_findings` | dict | Results from each agent |
| `remediation` | string | Fix recommendation |

---

## Edge Types

All edges are now **Rich Edges** with metadata (see [Rich Edges Reference](../reference/rich-edges.md)).

### Core Edge Schema

```python
@dataclass
class RichEdge:
    type: str                     # Edge type
    source: str                   # Source node ID
    target: str                   # Target node ID
    risk_score: float             # 0-10
    pattern_tags: list[str]       # Vulnerability tags
    execution_context: str        # Execution context
    taint_source: str             # Taint origin
    guards_at_source: list[str]   # Active guards
    cfg_order: int                # Temporal ordering
    evidence: list[Evidence]      # Source locations
```

### Containment Edges

| Type | From | To | Base Risk |
|------|------|----|----|
| `CONTAINS_FUNCTION` | Contract | Function | 0.0 |
| `CONTAINS_STATE` | Contract | StateVariable | 0.0 |
| `CONTAINS_EVENT` | Contract | Event | 0.0 |
| `CONTAINS_MODIFIER` | Contract | Modifier | 0.0 |

### Function Relationships

| Type | From | To | Base Risk | Description |
|------|------|----|----|-------------|
| `FUNCTION_HAS_INPUT` | Function | Input | 0.0 | Parameter |
| `FUNCTION_HAS_LOOP` | Function | Loop | 2.0 | Loop construct |
| `USES_MODIFIER` | Function | Modifier | 0.0 | Applied modifier |
| `CALLS_INTERNAL` | Function | Function | 1.0 | Internal call |
| `CALLS_EXTERNAL` | Function | External | 5.0 | External call |

### State Interaction Edges (Rich)

| Type | From | To | Base Risk | Description |
|------|------|----|----|-------------|
| `READS_STATE` | Function | StateVariable | 1.0 | State read |
| `WRITES_STATE` | Function | StateVariable | 3.0 | State write |
| `WRITES_CRITICAL_STATE` | Function | StateVariable | 7.0 | Writes owner/admin/role |
| `WRITES_BALANCE` | Function | StateVariable | 6.0 | Writes balance mapping |
| `READS_BALANCE` | Function | StateVariable | 2.0 | Reads balance mapping |
| `READS_ORACLE` | Function | StateVariable | 3.0 | Reads oracle data |

### External Call Edges (Rich)

| Type | From | To | Base Risk | Description |
|------|------|----|----|-------------|
| `CALLS_EXTERNAL` | Function | Contract | 5.0 | Any external call |
| `CALLS_UNTRUSTED` | Function | Contract | 8.0 | Untrusted address call |
| `DELEGATECALL` | Function | Contract | 9.0 | delegatecall operation |
| `STATICCALL` | Function | Contract | 2.0 | staticcall (read-only) |

### Value Transfer Edges (Rich)

| Type | From | To | Base Risk | Description |
|------|------|----|----|-------------|
| `TRANSFERS_ETH` | Function | Target | 7.0 | Native ETH transfer |
| `TRANSFERS_TOKEN` | Function | Target | 6.0 | ERC20/721/1155 transfer |

### Taint Propagation Edges (Rich)

| Type | From | To | Base Risk | Description |
|------|------|----|----|-------------|
| `INPUT_TAINTS_STATE` | Input | StateVariable | 4.0 | User input → state |
| `EXTERNAL_TAINTS` | External | StateVariable | 5.0 | External data → state |
| `FUNCTION_INPUT_TAINTS_STATE` | Function | StateVariable | 4.0 | Direct taint |

### Invariant Edges

| Type | From | To | Base Risk |
|------|------|----|-----------|
| `FUNCTION_TOUCHES_INVARIANT` | Function | Invariant | 0.0 |
| `INVARIANT_TARGETS_CONTRACT` | Invariant | Contract | 0.0 |
| `INVARIANT_TARGETS_STATE` | Invariant | StateVariable | 0.0 |

### Call Site Edges

| Type | From | To | Base Risk |
|------|------|----|-----------|
| `FUNCTION_HAS_CALLSITE` | Function | ExternalCallSite | 0.0 |
| `CALLSITE_TARGETS` | ExternalCallSite | Target | 5.0 |
| `CALLSITE_MOVES_VALUE` | ExternalCallSite | Target | 7.0 |

### Meta-Edges (Cross-Contract Intelligence)

| Type | From | To | Base Risk | Description |
|------|------|----|-----------|-------------|
| `SIMILAR_TO` | Function | Function | Varies | Structural/behavioral similarity |
| `BUGGY_PATTERN_MATCH` | Function | KnownExploit | 9.0 | Matches known vulnerability |
| `ENABLES_ATTACK` | Function | Function | 7.0 | State transition enables exploit |
| `REFACTOR_CANDIDATE` | Function | Function | 0.0 | Code duplication detected |

**Location:** `src/alphaswarm_sol/kg/similarity.py`, `src/alphaswarm_sol/kg/exploit_detection.py`

---

## ID Generation

**Format:** `<type>:<hash12>`

**Hash:** First 12 chars of SHA1(kind:name:file:line)

**Examples:**
- `function:a3f2c1b5d8e9` - withdraw() in Vault.sol:42
- `contract:b7e9f1c2d3a4` - Vault contract
- `state:c2d3e4f5a6b7` - balances mapping

**Properties:**
- Deterministic (same source = same ID)
- Collision-resistant
- Stable across builds if source unchanged

---

## Evidence Structure

```python
@dataclass
class Evidence:
    file: str        # "contracts/Vault.sol"
    line_start: int  # 42
    line_end: int    # 45
```

All nodes and edges carry evidence for traceability.

---

## Graph Statistics (Typical)

| Metric | Small | Medium | Large |
|--------|-------|--------|-------|
| Contracts | 1-3 | 5-10 | 20-50 |
| Functions | 10-30 | 50-150 | 200-500 |
| StateVariables | 5-15 | 20-50 | 50-200 |
| Edges | 50-100 | 200-500 | 500-2000 |
| Graph Size | 50KB | 250KB | 1MB |

---

---

## Implementation Status

**All 22 phases complete with 1315+ passing tests.**

| Feature | Status | Location |
|---------|--------|----------|
| Rich Edges | ✅ COMPLETE | `src/alphaswarm_sol/kg/rich_edge.py` |
| Semantic Operations | ✅ COMPLETE | `src/alphaswarm_sol/kg/operations.py` |
| Operation Sequencing | ✅ COMPLETE | `src/alphaswarm_sol/kg/sequencing.py` |
| Hierarchical Classification | ✅ COMPLETE | `src/alphaswarm_sol/kg/classification.py` |
| Execution Paths | ✅ COMPLETE | `src/alphaswarm_sol/kg/paths.py` |
| Subgraph Extraction | ✅ COMPLETE | `src/alphaswarm_sol/kg/subgraph.py` |
| Multi-Agent Verification | ✅ COMPLETE | `src/alphaswarm_sol/agents/` |
| Cross-Contract Intelligence | ✅ COMPLETE | `src/alphaswarm_sol/kg/similarity.py` |
| Constraint Verification (Z3) | ✅ COMPLETE | `src/alphaswarm_sol/kg/constraints.py` |
| Supply-Chain Analysis | ✅ COMPLETE | `src/alphaswarm_sol/kg/supply_chain.py` |
| Temporal Layer | ✅ COMPLETE | `src/alphaswarm_sol/kg/temporal.py` |
| Semantic Scaffolding | ✅ COMPLETE | `src/alphaswarm_sol/kg/scaffold.py` |
| Attack Path Synthesis | ✅ COMPLETE | `src/alphaswarm_sol/analysis/attack_synthesis.py` |

---

*See [Property Reference](../reference/properties.md) for complete property list.*
*See [Operations Reference](../reference/operations.md) for semantic operations.*
*See [Rich Edges Reference](../reference/rich-edges.md) for edge metadata.*
*See [Agents Reference](../reference/agents.md) for multi-agent verification.*
