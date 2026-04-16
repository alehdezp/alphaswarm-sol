# AlphaSwarm.sol Architecture & Feature Knowledge Base

**Version**: 1.0 (December 2025)
**Last Updated**: 2025-12-29

This document serves as the comprehensive knowledge base for the AlphaSwarm.sol architecture, implementation decisions, and feature evolution. It is intended for developers, maintainers, and AI assistants working with the codebase.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architectural Principles](#architectural-principles)
3. [Core Components](#core-components)
4. [Knowledge Graph Schema](#knowledge-graph-schema)
5. [Security Property Taxonomy](#security-property-taxonomy)
6. [Query System Architecture](#query-system-architecture)
7. [Pattern Pack System](#pattern-pack-system)
8. [Invariant System](#invariant-system)
9. [Feature Evolution Timeline](#feature-evolution-timeline)
10. [Implementation Decisions & Rationale](#implementation-decisions--rationale)
11. [Testing Philosophy](#testing-philosophy)
12. [Performance Characteristics](#performance-characteristics)

---

## 1. System Overview

### What AlphaSwarm.sol Is

AlphaSwarm.sol (Vulnerability Knowledge Graph) is a **deterministic Solidity security reasoning system** that:

1. **Builds** a per-project knowledge graph from Solidity code using Slither's static analysis
2. **Derives** 50+ security-relevant properties for each function, contract, and state variable
3. **Enables** LLM-driven vulnerability discovery through structured queries without fine-tuning
4. **Provides** deterministic, reproducible results via pattern packs and logic queries

### What AlphaSwarm.sol Is NOT

- ❌ A symbolic executor or formal verifier
- ❌ A runtime emulator or fuzzer
- ❌ A machine learning model requiring training
- ❌ A replacement for human audit judgment

### Core Design Philosophy

**"Lenses over lists"** - Model security primitives (authority, value movement, external influence, ordering, upgradeability, liveness) rather than maintaining vulnerability checklists.

**Key Principles:**
1. **Deterministic core**: Graph + rules, not hidden heuristics
2. **LLM as strategist**: Model chooses queries; system executes deterministically
3. **Soft evidence by default**: Enable novel reasoning while anchoring to code
4. **Composable primitives**: Small facts combine into complex vulnerability patterns
5. **Evidence-first**: Every finding ties back to code locations

---

## 2. Architectural Principles

### 2.1 Total Model, Not Partial Heuristics

Every security-relevant fact is **explicit in the graph**. No hidden scoring or probabilistic inference. If a pattern matches, you can trace exactly why through the graph structure and property values.

**Implementation**: VKGBuilder derives all properties during graph construction. Properties are boolean flags, strings, or lists - never opaque scores.

### 2.2 Deterministic Execution

Given the same Solidity code and Slither version, AlphaSwarm.sol produces **identical graphs and query results**. This enables:
- Regression testing via pattern packs
- Reproducible security audits
- CI/CD integration with deterministic pass/fail

**Implementation**: All property derivation uses Slither's IR and explicit rules. No random seeds, sampling, or model inference.

### 2.3 Composability

Small, focused properties combine via boolean logic to detect complex vulnerabilities.

**Example**: Reentrancy detection combines:
- `visibility in [public, external]`
- `state_write_after_external_call == true`
- `has_reentrancy_guard == false`

**Implementation**: Pattern YAML files specify match conditions using property operators (eq, in, gt, etc.) and boolean combinators (all, any, none).

### 2.4 Evidence-First

Every node and edge includes **Evidence objects** with file paths and line numbers. Query results preserve this provenance.

**Implementation**: Builder's `_evidence()` method creates Evidence from Slither's source mappings. All nodes carry evidence; query results include it by default (unless `--no-evidence` flag).

---

## 3. Core Components

### 3.1 Knowledge Graph Layer (`src/true_vkg/kg/`)

#### `builder.py` (Primary Component - 960 lines)

**Responsibility**: Orchestrate Slither analysis and derive all security properties.

**Key Methods**:
- `build(target)` - Main entry point, coordinates all building phases
- `_add_contract()` - Create Contract nodes with proxy detection
- `_add_functions()` - Create Function nodes with 50+ properties (largest method)
- `_add_state_variables()` - Create StateVariable nodes with security tags
- `_add_invariants()` - Extract formal properties from NatSpec comments
- `_analyze_loops()` - Detect loop bounds and DoS conditions
- `_augment_taint()` - Add dataflow edges for attacker-controlled inputs

**Properties Derived** (50+ total):
- **Access Control** (38): has_access_gate, access_gate_logic, access_gate_sources, writes_privileged_state, has_auth_pattern, uses_tx_origin, uses_msg_sender, public_wrapper_without_access_gate, governance_vote_without_snapshot, governance_quorum_without_snapshot, governance_exec_without_timelock_check, governance_exec_without_quorum_check, governance_exec_without_vote_period_check, multisig_threshold_change_without_gate, multisig_signer_change_without_gate, multisig_threshold_change_without_validation, multisig_signer_change_without_validation, role_grant_like, role_revoke_like, uses_selfdestruct, multisig_threshold_is_zero, contract_has_multisig, contract_has_governance, uses_extcodesize, uses_extcodehash, uses_gasleft, owner_uninitialized, default_admin_address_is_zero, is_multisig_threshold_change, is_multisig_member_change, access_gate_uses_balance_check, multisig_member_change_without_minimum_check, multisig_threshold_change_without_owner_count_check, access_gate_uses_contract_address, access_gate_uses_hash_compare, has_role_events, access_gate_has_if_return, access_gate_without_sender_source
- **Reentrancy** (3): state_write_after_external_call, state_write_before_external_call, has_reentrancy_guard
- **Calls** (6): has_external_calls (enhanced 2025-12), uses_delegatecall, uses_call, low_level_calls, external_call_count, internal_call_count
- **DoS** (9): has_unbounded_loop, has_require_bounds (new 2025-12), external_calls_in_loop, has_unbounded_deletion, uses_transfer (new 2025-12), uses_send (new 2025-12), has_strict_equality_check (new 2025-12), state_mutability (new 2025-12), has_loops
- **Crypto/Signatures** (12): uses_ecrecover, checks_zero_address, checks_sig_v, checks_sig_s, uses_chainid, has_nonce_parameter, reads_nonce_state, writes_nonce_state, uses_domain_separator, has_deadline_check, is_permit_like, has_signature_validity_checks
- **MEV** (7): swap_like, risk_missing_slippage_parameter, risk_missing_deadline_check, has_slippage_parameter, has_slippage_check, has_deadline_parameter, risk_missing_twap_window
- **Oracle** (8): reads_oracle_price, has_staleness_check, oracle_round_check, oracle_freshness_ok, has_sequencer_uptime_check, l2_oracle_context, reads_twap, reads_twap_with_window
- **Tokens** (8): uses_erc20_transfer, uses_erc20_transfer_from, uses_erc20_approve, token_return_guarded, uses_safe_erc20, uses_erc20_mint, uses_erc20_burn, uses_erc721_safe_transfer
- **Upgradeability** (3): is_upgrade_function, is_initializer_function, upgrade_guarded
- **Invariants** (4): touches_invariant, has_invariant_check, touches_invariant_unchecked, invariant_state_vars

**Design Decisions**:
- **Why 50+ properties?** Each property is a composable primitive. Complex patterns emerge from combinations.
- **Why boolean flags?** Simple, cacheable, deterministic. No floating-point scoring to debug.
- **Why enhance `has_external_calls`?** (Dec 2025) Low-level calls like `.call{value}("")` were missed, causing false negatives in DoS and reentrancy patterns.

#### `schema.py` (Data Model)

**Core Classes**:
```python
@dataclass
class Evidence:
    file: str
    line_start: int | None
    line_end: int | None

@dataclass
class Node:
    id: str
    type: str  # Contract, Function, StateVariable, Event, Input, Loop, Invariant, etc.
    label: str
    properties: dict[str, Any]
    evidence: list[Evidence]

@dataclass
class Edge:
    id: str
    type: str  # CONTAINS_FUNCTION, INPUT_TAINTS_STATE, etc.
    source: str  # Node ID
    target: str  # Node ID
    evidence: list[Evidence]

@dataclass
class KnowledgeGraph:
    nodes: dict[str, Node]
    edges: dict[str, Edge]
    metadata: dict[str, Any]
```

**Design Decisions**:
- **Dataclasses for immutability**: Easier to reason about, serialize, and test
- **String IDs**: Hash-based (SHA1 prefix) for determinism across builds
- **Flat dicts**: No nested structures - simpler queries, easier JSON serialization

#### `heuristics.py` (Security Tag Classification)

**Purpose**: Classify state variable names into security-relevant categories.

**Tags**:
- `owner`, `admin`, `role`, `guardian`, `governor` - Authority
- `paused`, `locked`, `frozen` - Circuit breakers
- `fee`, `rate`, `treasury`, `vault` - Value movement
- `whitelist`, `blacklist`, `allowlist` - Access lists
- `nonce`, `used`, `claimed` - Replay protection

**Usage**: Powers `is_privileged_state()` check for access control patterns.

#### `taint.py` (Dataflow Modeling)

**Purpose**: Track attacker-controlled inputs to state variable writes.

**Approach**:
1. Extract input sources: parameters, msg.value, block.timestamp, etc.
2. Use Slither's dataflow when available
3. Fall back to heuristic: if input name appears in written state var name
4. Create `INPUT_TAINTS_STATE` edges

**Limitations**: Heuristic-based (Slither's dataflow not always available). False negatives possible.

---

### 3.2 Query Layer (`src/true_vkg/queries/`)

#### `intent.py` (Natural Language Parser)

**Purpose**: Convert safe NL queries to structured Intent objects.

**Supported Formats**:
1. **Simple NL**: "public functions that write state"
2. **VQL (VKG Query Language)**: "find functions where visibility in [public, external] and writes_state limit 20"
3. **Pattern shortcuts**: "pattern:weak-access-control", "lens:Authority severity high"

**Property Aliases**:
- "auth gate" → has_access_gate
- "state write" → writes_state
- "external call" → has_external_calls
- etc.

**Design Decision**: VQL provides structured queries without JSON verbosity, balancing expressiveness and safety.

#### `executor.py` (Query Execution Engine)

**Query Types**:

1. **Logic Query**: Match nodes by properties + edges + paths
   ```json
   {
     "query_kind": "logic",
     "node_types": ["Function"],
     "match": {
       "all": [{"property": "visibility", "op": "in", "value": ["public", "external"]}],
       "any": [],
       "none": []
     },
     "edges": [{"type": "INPUT_TAINTS_STATE", "direction": "out"}],
     "limit": 50
   }
   ```

2. **Flow Query**: Enforce dataflow constraints
   ```json
   {
     "query_kind": "flow",
     "flow": {
       "from_kinds": ["parameter", "env"],
       "exclude_sources": ["msg.sender"],
       "target_type": "StateVariable",
       "edge_type": "INPUT_TAINTS_STATE"
     }
   }
   ```

3. **Pattern Query**: Execute named pattern from pattern pack
4. **Lens Query**: Group findings by security primitive

**Design Decision**: Separate query kinds allow specialized execution paths. Flow queries are more expensive (edge traversal) but critical for taint analysis.

#### `patterns.py` (Pattern Pack Engine)

**Pattern Structure** (YAML):
```yaml
id: weak-access-control
name: Weak Access Control on State Writes
description: Public functions that write privileged state without access control
scope: Function
lens:
  - Authority
severity: high
match:
  all:
    - property: visibility
      op: in
      value: [public, external]
    - property: writes_privileged_state
      op: eq
      value: true
  none:
    - property: has_access_gate
      op: eq
      value: true
```

**Pattern Pack Organization**:
- `patterns/core/` - Curated, tested patterns
- Categories: Authority, Reentrancy, MEV, Oracle, Token, Crypto, DoS
- Each pattern is a deterministic query with CWE/SWC mappings

**Design Decision**: Patterns are data (YAML), not code. Enables:
- Version control
- Community contributions
- Non-programmer pattern authoring
- Regression testing

---

## 4. Knowledge Graph Schema

### 4.1 Node Types

| Type | Count (typical) | Properties | Purpose |
|------|----------------|------------|---------|
| **Contract** | 1-10 | kind, has_initializer, proxy_type, is_proxy_like, has_storage_gap | Contract-level metadata |
| **Function** | 10-100 | 50+ security properties | Primary vulnerability detection target |
| **StateVariable** | 5-50 | type, visibility, security_tags | State mutation analysis |
| **Event** | 5-50 | - | Audit trail analysis |
| **Input** | 20-200 | kind (parameter/env) | Taint source tracking |
| **Loop** | 0-20 | bound_sources, has_external_call, has_delete | DoS analysis |
| **Invariant** | 0-10 | text, source_kind, state_vars | Formal property tracking |
| **ExternalCallSite** | 0-50 | call_kind, has_call_value, destination | Low-level call analysis |
| **SignatureUse** | 0-10 | uses_chainid, has_nonce_parameter | Crypto verification tracking |

### 4.2 Edge Types

| Type | Semantics | Count (typical) |
|------|-----------|----------------|
| **CONTAINS_FUNCTION** | Contract → Function | 10-100 |
| **CONTAINS_STATE** | Contract → StateVariable | 5-50 |
| **FUNCTION_HAS_INPUT** | Function → Input | 20-200 |
| **INPUT_TAINTS_STATE** | Input → StateVariable (dataflow) | 5-50 |
| **FUNCTION_TOUCHES_INVARIANT** | Function → Invariant | 0-20 |
| **FUNCTION_HAS_LOOP** | Function → Loop | 0-20 |
| **USES_MODIFIER** | Function → Modifier | 10-50 |
| **READS_STATE** / **WRITES_STATE** | Function → StateVariable | 20-100 |
| **CALLS_INTERNAL** / **CALLS_EXTERNAL** | Function → CallTarget | 10-50 |

### 4.3 ID Generation

**Format**: `<type>:<hash>` where hash is first 12 chars of SHA1(kind:name:file:line)

**Example**: `function:a3f2c1b5d8e9` for `withdraw(uint256)` in `Vault.sol:42`

**Rationale**: Deterministic, collision-resistant, stable across builds if source unchanged.

---

## 5. Security Property Taxonomy

### 5.1 Authority (Access Control)

**Goal**: Identify functions that modify privileged state without proper access control.

**Properties**:
- `has_access_gate` - Boolean: Has modifier or inline check for msg.sender
- `access_gate_logic` - Boolean: Has inline require(msg.sender == owner)
- `access_gate_modifiers` - List[str]: Names of access control modifiers
- `writes_privileged_state` - Boolean: Writes to owner/admin/role variables
- `uses_tx_origin` - Boolean: Uses tx.origin (phishing vector)

**Patterns**:
- `weak-access-control` - Public/external writes privileged state without gate
- `tx-origin-auth` - Uses tx.origin for authentication
- `arbitrary-delegatecall` - Delegatecall without access control

**Real-World Examples**: Parity Wallet hack (arbitrary delegatecall), DAO hack (reentrancy + access)

### 5.2 Reentrancy

**Goal**: Detect functions vulnerable to reentrancy attacks.

**Properties**:
- `state_write_after_external_call` - Boolean: CEI violation
- `state_write_before_external_call` - Boolean: Safe CEI pattern
- `has_reentrancy_guard` - Boolean: Has nonReentrant modifier
- `external_calls_in_loop` - Boolean: Loop with external calls

**Patterns**:
- `reentrancy-basic` - State write after external call without guard
- `cross-function-reentrancy` - Multiple functions with shared state
- `read-only-reentrancy` - View function reentrancy (flash loan attacks)

**Real-World Examples**: DAO hack (2016), Lendf.me hack (2020)

### 5.3 DoS (Denial of Service)

**Goal**: Identify functions that can be griefed or cause out-of-gas errors.

**Properties** (Enhanced Dec 2025):
- `has_unbounded_loop` - Boolean: Loop with user-controlled bounds
- `has_require_bounds` - Boolean: **NEW** - Has require() bounding loop params
- `external_calls_in_loop` - Boolean: Loop with external calls (block gas limit)
- `has_unbounded_deletion` - Boolean: Unbounded delete in loop
- `uses_transfer` - Boolean: **NEW** - Uses .transfer() (2300 gas limit)
- `uses_send` - Boolean: **NEW** - Uses .send() (2300 gas limit)
- `has_strict_equality_check` - Boolean: **NEW** - Strict == on balance (gridlock)
- `state_mutability` - String: **NEW** - "view", "pure", "payable", "nonpayable"

**Patterns** (9 total):
- `dos-unbounded-loop` - User-controlled loop bounds without require checks
- `dos-external-call-in-loop` - External calls in loop (block gas limit DoS)
- `dos-unbounded-deletion` - Unbounded delete operations
- `dos-revert-failed-call` - **NEW** - Failed call blocks execution
- `dos-strict-equality` - **NEW** - Gridlock via strict balance equality
- `dos-unbounded-mass-operation` - **NEW** - Mass array operations
- `dos-array-return-unbounded` - **NEW** - View function returning unbounded arrays
- `dos-transfer-in-loop` - **NEW** - Transfer/send in loops (fixed gas)
- `dos-user-controlled-batch` - **NEW** - Batch operations without limits

**Real-World Examples**:
- Edgeware Lockdrop (gridlock attack via strict equality)
- King of Ether Throne (revert DoS)
- Gas griefing attacks (unbounded loops)

**Enhancement Rationale (Dec 2025)**:
- `has_require_bounds` reduces false positives for paginated functions
- `uses_transfer`/`uses_send` detect fixed gas stipend issues
- `has_strict_equality_check` detects gridlock attacks
- `state_mutability` enables view function DoS detection
- Enhanced `has_external_calls` includes `.call{value}("")` for better DoS/reentrancy detection

### 5.4 Crypto/Signatures

**Goal**: Detect signature verification vulnerabilities.

**Properties** (12 total):
- `uses_ecrecover` - Boolean: Uses signature recovery
- `checks_zero_address` - Boolean: Validates ecrecover result
- `checks_sig_v` - Boolean: Validates v in [27, 28]
- `checks_sig_s` - Boolean: Checks s for malleability
- `uses_chainid` - Boolean: Includes chain ID (replay protection)
- `has_nonce_parameter` - Boolean: Has nonce in signature
- `writes_nonce_state` - Boolean: Increments nonce (replay protection)
- `uses_domain_separator` - Boolean: EIP-712 domain separator
- `has_deadline_check` - Boolean: Validates timestamp deadline

**Patterns** (11 total):
- `crypto-missing-chainid` - No chain ID (cross-chain replay)
- `crypto-missing-deadline` - No expiration check
- `crypto-signature-malleability` - Missing s-value validation
- `crypto-zero-address-check` - No zero address check post-ecrecover
- `crypto-permit-incomplete` - Incomplete EIP-2612 implementation

**Real-World Examples**: Permit front-running, cross-chain replays

### 5.5 MEV (Maximal Extractable Value)

**Goal**: Identify functions vulnerable to MEV extraction (sandwich, front-running).

**Properties**:
- `swap_like` - Boolean: Looks like token swap function
- `risk_missing_slippage_parameter` - Boolean: Swap without slippage protection
- `risk_missing_deadline_check` - Boolean: Swap without deadline
- `has_slippage_parameter` - Boolean: Has minAmountOut parameter
- `has_slippage_check` - Boolean: Validates slippage in require

**Patterns**:
- `mev-missing-slippage-parameter` - Swap without slippage
- `mev-missing-deadline-check` - Swap without deadline

**Real-World Examples**: Uniswap sandwich attacks, generalized front-running

### 5.6 Oracle

**Goal**: Detect oracle manipulation and stale data vulnerabilities.

**Properties**:
- `reads_oracle_price` - Boolean: Calls Chainlink/oracle
- `has_staleness_check` - Boolean: Validates updatedAt
- `oracle_round_check` - Boolean: Validates answeredInRound
- `has_sequencer_uptime_check` - Boolean: L2 sequencer check
- `reads_twap` - Boolean: Uses TWAP oracle
- `has_twap_window_parameter` - Boolean: Configurable TWAP window

**Patterns**:
- `oracle-freshness-missing-staleness` - No staleness check
- `oracle-staleness-missing-sequencer-check` - L2 without sequencer check
- `twap-missing-window` - TWAP without window parameter

**Real-World Examples**: Venus Protocol oracle manipulation (2023)

### 5.7 Invariants (Formal Properties)

**Goal**: Extract and track formal invariants from NatSpec comments.

**Node Type**: `Invariant`

**Properties**:
- `text` - String: Full invariant text from comment
- `source_kind` - String: "natspec", "config" (future: formal spec languages)
- `target_type` - String: "Contract", "Function", "StateVariable"
- `state_vars` - List[str]: State variables referenced
- `guard_functions` - List[str]: Guard functions that re-check invariant

**Function Properties**:
- `touches_invariant` - Boolean: Reads/writes invariant-related state
- `has_invariant_check` - Boolean: Has require() validating invariant
- `touches_invariant_unchecked` - Boolean: Touches without validating

**Pattern**:
- `invariant-violation` - Function touches invariant state without checking

**Example**:
```solidity
/// invariant: totalSupply == sum(balances)
uint256 public totalSupply;
```

**Design Decision**: Invariants are first-class nodes, not just properties. Enables:
- Tracking which functions must preserve which invariants
- Pattern matching on invariant violations
- Future: integration with formal verification tools

---

## 6. Query System Architecture

### 6.1 Query Pipeline

```
User Input (NL/VQL/JSON)
    ↓
Intent Parser (intent.py)
    ↓
Intent Object
    ↓
Query Planner (planner.py)
    ↓
QueryPlan Object
    ↓
Executor (executor.py)
    ↓
Results (with Evidence)
```

### 6.2 Query Optimization

**Strategies**:
1. **Property filters first**: Scan nodes by type, apply property filters before edge traversal
2. **Limit early**: Apply limit before evidence collection
3. **Compact mode**: Skip evidence if not needed (10x smaller results)
4. **Cached property access**: Properties are dict lookups, not recomputed

**Performance**: Queries on typical projects (100 functions) run in <100ms.

### 6.3 Output Modes

| Mode | Size | Use Case |
|------|------|----------|
| **Full** | ~5KB/function | Human review, debugging |
| **Compact** | ~0.5KB/function | LLM context (10x reduction) |
| **Explain** | ~6KB/function | Understanding pattern matches |
| **No-evidence** | ~2KB/function | Quick scans |

---

## 7. Pattern Pack System

### 7.1 Pattern Lifecycle

1. **Authoring**: Write YAML pattern with match conditions
2. **Testing**: Create test contract with vulnerable + safe patterns
3. **Regression**: Add to test suite (`test_queries_*.py`)
4. **Versioning**: Track pattern version in YAML metadata
5. **Distribution**: Patterns are data files, can be distributed separately

### 7.2 Pattern Categories (Lenses)

| Lens | Pattern Count | Focus |
|------|--------------|-------|
| Authority | 5+ | Access control, delegatecall |
| Reentrancy | 4+ | CEI violations, guards |
| DoS | 9 | Unbounded loops, gas limits |
| Crypto | 11+ | Signature verification |
| MEV | 5+ | Slippage, deadlines |
| Oracle | 6+ | Staleness, manipulation |
| Token | 3+ | ERC20 return values |
| Proxy | 3+ | Upgradeability, storage gaps |

### 7.3 Pattern Match Algorithm

```python
def evaluate_pattern(node, pattern):
    # Check scope (Function, Contract, StateVariable)
    if node.type != pattern.scope:
        return False

    # Evaluate match conditions
    for condition in pattern.match.all:
        if not evaluate_condition(node, condition):
            return False

    if pattern.match.any:
        if not any(evaluate_condition(node, c) for c in pattern.match.any):
            return False

    for condition in pattern.match.none:
        if evaluate_condition(node, condition):
            return False

    # Check edge requirements (optional)
    for edge_req in pattern.edges:
        if not has_edge(node, edge_req):
            return False

    return True
```

---

## 8. Invariant System

### 8.1 NatSpec Extraction

**Trigger**: Comments containing "invariant" keyword above contract/function/state var.

**Example**:
```solidity
/// @notice Total supply invariant
/// invariant: totalSupply == sum of all balances
uint256 public totalSupply;
```

**Extraction**:
1. Read source file lines (cached per file)
2. For each node (contract/function/state var), scan lines above
3. Collect comment block if contains "invariant"
4. Clean comment markers (`///`, `/*`, `*/`, `*`)
5. Extract referenced state variable names via regex
6. Create Invariant node with edges to referenced state vars

### 8.2 Invariant Tracking

**Function Properties Added**:
- `touches_invariant` - Function reads/writes state vars in invariant
- `has_invariant_check` - Function has require() mentioning invariant var
- `touches_invariant_unchecked` - Violation: touches without checking

**Pattern**: `invariant-violation` matches functions with `touches_invariant_unchecked == true`.

**Design Rationale**:
- Invariants are security-critical assumptions
- Violations are often logic bugs (not covered by typical patterns)
- Bridges gap between informal comments and formal verification

---

## 9. Feature Evolution Timeline

### Phase 1: Foundation (2023)
- ✅ Basic BSKG construction from Slither
- ✅ Contract, Function, StateVariable nodes
- ✅ Access control properties
- ✅ Simple pattern matching

### Phase 2: Query System (2024 Q1-Q2)
- ✅ Intent parser (safe NL)
- ✅ VQL (VKG Query Language)
- ✅ Logic queries with boolean combinators
- ✅ Flow queries for taint analysis
- ✅ Pattern pack system

### Phase 3: Vulnerability Coverage (2024 Q3-Q4)
- ✅ Reentrancy properties (CEI, guards)
- ✅ Crypto/signature properties (15+ properties)
- ✅ MEV properties (slippage, deadlines)
- ✅ Oracle properties (staleness, TWAP)
- ✅ Token properties (safe ERC20)
- ✅ Proxy/upgradeability properties

### Phase 4: DoS Enhancement (2024 Q4 - 2025 Dec)
- ✅ Loop analysis with bound detection
- ✅ External calls in loops
- ✅ Unbounded deletion detection
- ✅ **Dec 2025 Enhancement**: 5 new DoS properties + 1 enhanced
  - `has_require_bounds` - Reduce false positives
  - `uses_transfer` / `uses_send` - Gas limit DoS
  - `has_strict_equality_check` - Gridlock attacks
  - `state_mutability` - View function DoS
  - Enhanced `has_external_calls` - Include low-level calls
- ✅ 6 new DoS patterns (9 total)
- ✅ Comprehensive DoS test suite (25 tests)

### Phase 5: Invariant System (2025 Dec)
- ✅ NatSpec invariant extraction
- ✅ Invariant node type
- ✅ Function-invariant tracking
- ✅ `touches_invariant_unchecked` detection

### Phase 6: Future (Planned)
- ⏳ Graph database backend (Neo4j)
- ⏳ Multi-contract dependency analysis
- ⏳ Upgrade simulation (storage layout conflicts)
- ⏳ Integration with formal verification tools
- ⏳ LLM-guided query refinement

---

## 10. Implementation Decisions & Rationale

### 10.1 Why Slither?

**Alternatives Considered**: Solc AST, Mythril, Manticore

**Decision**: Slither

**Rationale**:
- ✅ Fast (seconds vs minutes for symbolic execution)
- ✅ IR (Intermediate Representation) abstracts Solidity complexity
- ✅ Dataflow analysis built-in
- ✅ Actively maintained by Trail of Bits
- ❌ Not a formal verifier (acceptable trade-off for speed)

### 10.2 Why JSON Graph Storage?

**Alternatives Considered**: Neo4j, SQLite, Pickle

**Decision**: JSON (with future Neo4j migration path)

**Rationale**:
- ✅ Human-readable, diffable in git
- ✅ No external dependencies (embedded DB)
- ✅ Easy serialization for LLM context
- ✅ Fast enough for single-project analysis (<10MB graphs)
- ⏳ Migration to Neo4j planned for multi-project analysis

### 10.3 Why YAML Patterns?

**Alternatives Considered**: JSON, Python DSL, custom language

**Decision**: YAML

**Rationale**:
- ✅ Human-readable
- ✅ Comment support (explain patterns)
- ✅ No code execution risk
- ✅ Easy for non-programmers to author
- ✅ Standard tooling (linters, validators)

### 10.4 Why 50+ Properties Per Function?

**Alternatives Considered**: Minimal property set, dynamic property derivation

**Decision**: Comprehensive property set (50+)

**Rationale**:
- ✅ Composability: Small properties combine into complex patterns
- ✅ Cacheability: Derive once, query many times
- ✅ Determinism: No runtime property derivation
- ✅ Explainability: Every pattern match is property-based
- ❌ Higher graph size (acceptable: ~50KB per contract)

### 10.5 Why Enhance `has_external_calls` in Dec 2025?

**Problem**: Low-level calls like `.call{value: X}("")` were not detected as external calls.

**Impact**: False negatives in DoS and reentrancy patterns.

**Solution**: Enhanced property to include `low_level_calls`.

**Rationale**:
- ✅ Backward compatible (only adds detections, never removes)
- ✅ Fixes real-world false negatives
- ✅ No performance impact (low_level_calls already extracted)
- ✅ Aligns with security semantics (low-level calls ARE external calls)

### 10.6 Why Add Invariant System?

**Problem**: Logic bugs often violate informal assumptions (total supply, balance sums, etc.).

**Existing Coverage**: Good for known patterns (reentrancy, access control), poor for custom logic.

**Solution**: Extract invariants from NatSpec, track violations.

**Rationale**:
- ✅ Bridges gap to formal verification
- ✅ Developer-authored (already writing NatSpec)
- ✅ Cheap to extract (regex on comments)
- ✅ Enables new pattern class (invariant violations)
- ⏳ Future: integrate with SMT solvers for proof

---

## 11. Testing Philosophy

### 11.1 Test Organization

```
tests/
├── contracts/           # Solidity fixtures (80+ contracts)
│   ├── ReentrancyClassic.sol
│   ├── DosComprehensive.sol
│   └── ...
├── graph_cache.py      # Cached graph builds
├── test_queries_access.py    # Access control tests
├── test_queries_dos.py       # DoS tests (original)
├── test_queries_dos_comprehensive.py  # DoS tests (enhanced)
├── test_queries_crypto.py    # Signature tests
├── test_vkg_enhancements.py  # BSKG builder tests
└── ...
```

### 11.2 Test Principles

1. **One fixture per vulnerability class**: `ReentrancyClassic.sol`, `TxOriginAuth.sol`, etc.
2. **Positive AND negative cases**: Every pattern tested against vulnerable AND safe code
3. **Property assertions**: Test derived properties, not just pattern matches
4. **Cached builds**: `load_graph("ContractName.sol")` caches Slither output
5. **Determinism**: Tests must pass 100% consistently (no flaky tests)

### 11.3 Test Coverage Requirements

**For New Properties**:
- ✅ Positive test (property == True when expected)
- ✅ Negative test (property == False for safe code)
- ✅ Edge cases (boundary conditions)

**For New Patterns**:
- ✅ Vulnerable contract triggers pattern
- ✅ Safe contract does NOT trigger pattern
- ✅ Explain mode includes correct reasoning
- ✅ Pattern documented in taxonomy (this file)

**Example (DoS Enhancement)**:
- Created `DosComprehensive.sol` with 14 vulnerable + 7 safe functions
- Created `test_queries_dos_comprehensive.py` with 17 tests
- All 25 tests (original + new) pass
- Backward compatibility verified (105/105 query tests pass)

---

## 12. Performance Characteristics

### 12.1 Graph Build Performance

| Project Size | Function Count | Build Time | Graph Size |
|-------------|---------------|------------|------------|
| Small (1 contract) | 10 | <1s | ~50KB |
| Medium (5 contracts) | 50 | 2-3s | ~250KB |
| Large (20 contracts) | 200 | 10-15s | ~1MB |
| Very Large (100 contracts) | 1000 | 60-90s | ~5MB |

**Bottleneck**: Slither analysis (95% of time), not BSKG derivation.

**Optimization**: Slither caching via `--exclude-dependencies` flag.

### 12.2 Query Performance

| Query Type | Typical Time | Scaling |
|-----------|-------------|---------|
| Property filter | <10ms | O(n) nodes |
| Pattern match | <50ms | O(n) nodes |
| Edge traversal | <100ms | O(n) nodes × O(e) edges |
| Flow query | <500ms | O(n × e) worst case |

**Optimization Strategies**:
1. Early property filtering (before edge traversal)
2. Limit enforcement (stop at N results)
3. Compact mode (skip evidence collection)

### 12.3 Memory Usage

| Component | Memory (typical) |
|-----------|-----------------|
| Graph (100 functions) | ~10MB |
| Slither objects | ~50MB (released after build) |
| Query results | ~1MB (full mode) / ~100KB (compact) |

**Total**: <100MB for typical project analysis.

---

## Appendix A: Property Quick Reference

### Function Properties (50+)

**Access Control**:
- `has_access_gate`, `access_gate_logic`, `access_gate_modifiers`, `access_gate_sources`, `writes_privileged_state`, `has_auth_pattern`, `uses_tx_origin`, `uses_msg_sender`, `public_wrapper_without_access_gate`, `governance_vote_without_snapshot`, `governance_quorum_without_snapshot`, `governance_exec_without_timelock_check`, `governance_exec_without_quorum_check`, `governance_exec_without_vote_period_check`, `multisig_threshold_change_without_gate`, `multisig_signer_change_without_gate`, `multisig_threshold_change_without_validation`, `multisig_signer_change_without_validation`, `role_grant_like`, `role_revoke_like`, `uses_selfdestruct`, `multisig_threshold_is_zero`, `contract_has_multisig`, `contract_has_governance`, `uses_extcodesize`, `uses_extcodehash`, `uses_gasleft`, `owner_uninitialized`, `default_admin_address_is_zero`, `is_multisig_threshold_change`, `is_multisig_member_change`, `access_gate_uses_balance_check`, `multisig_member_change_without_minimum_check`, `multisig_threshold_change_without_owner_count_check`, `access_gate_uses_contract_address`, `access_gate_uses_hash_compare`, `has_role_events`, `access_gate_has_if_return`, `access_gate_without_sender_source`

**Reentrancy**:
- `state_write_after_external_call`, `state_write_before_external_call`, `has_reentrancy_guard`

**Calls**:
- `has_external_calls` ⭐enhanced, `uses_delegatecall`, `uses_call`, `low_level_calls`, `external_call_count`, `internal_call_count`

**DoS**:
- `has_unbounded_loop`, `has_require_bounds` ⭐new, `external_calls_in_loop`, `has_unbounded_deletion`, `uses_transfer` ⭐new, `uses_send` ⭐new, `has_strict_equality_check` ⭐new, `state_mutability` ⭐new, `has_loops`, `loop_count`, `loop_bound_sources`

**Crypto**:
- `uses_ecrecover`, `checks_zero_address`, `checks_sig_v`, `checks_sig_s`, `uses_chainid`, `has_nonce_parameter`, `reads_nonce_state`, `writes_nonce_state`, `uses_domain_separator`, `has_deadline_check`, `is_permit_like`, `has_signature_validity_checks`

**MEV**:
- `swap_like`, `risk_missing_slippage_parameter`, `risk_missing_deadline_check`, `has_slippage_parameter`, `has_slippage_check`, `has_deadline_parameter`, `risk_missing_twap_window`

**Oracle**:
- `reads_oracle_price`, `has_staleness_check`, `oracle_round_check`, `oracle_freshness_ok`, `has_sequencer_uptime_check`, `l2_oracle_context`, `reads_twap`, `reads_twap_with_window`

**Tokens**:
- `uses_erc20_transfer`, `uses_erc20_transfer_from`, `uses_erc20_approve`, `token_return_guarded`, `uses_safe_erc20`, `uses_erc20_mint`, `uses_erc20_burn`, `uses_erc721_safe_transfer`

**Invariants**:
- `touches_invariant`, `has_invariant_check`, `touches_invariant_unchecked`, `invariant_state_vars`

**Upgradeability**:
- `is_upgrade_function`, `is_initializer_function`, `upgrade_guarded`

**Metadata**:
- `visibility`, `mutability`, `state_mutability` ⭐new, `payable`, `is_constructor`, `is_fallback`, `is_receive`, `signature`, `modifiers`

---

## Appendix B: Pattern Coverage Matrix

| Vulnerability Class | Pattern Count | Test Coverage | Real-World Examples |
|-------------------|--------------|--------------|-------------------|
| Access Control | 5+ | 28 tests | Parity Wallet, DAO |
| Reentrancy | 4+ | 8 tests | DAO, Lendf.me |
| DoS | 9 | 25 tests | Edgeware, King of Ether |
| Crypto/Signatures | 11+ | 24 tests | Permit front-running |
| MEV | 5+ | 11 tests | Sandwich attacks |
| Oracle | 6+ | 7 tests | Venus manipulation |
| Tokens | 3+ | 5 tests | ERC20 return values |
| Proxy/Upgrade | 3+ | 6 tests | Storage collisions |
| Invariants | 1 | 5 tests | Custom logic bugs |

**Total**: 47+ patterns, 120+ tests

---

## Document Maintenance

**Maintainers**: Update this document when:
- Adding new node/edge types
- Adding new properties (>3 properties)
- Changing architecture decisions
- Adding new vulnerability classes
- Major performance changes

**Version History**:
- v1.0 (2025-12-29): Initial comprehensive knowledge base after DoS enhancement

---

*End of Architecture Knowledge Base*
