# Property Reference - Complete Guide

**Version**: 1.0 (December 2025)
**Total Properties**: 50+

This document provides a complete reference of all properties derived by the BSKG builder for each node type.

---

## Property Organization

Properties are organized by **vulnerability class** (security lens) for easier pattern authoring:

| Class | Properties | Purpose |
|-------|------------|---------|
| **Access Control** | 38 | Authority, privileged operations |
| **Reentrancy** | 3 | CEI violations, guards |
| **DoS** | 9 | Gas exhaustion, griefing |
| **Crypto** | 12 | Signature verification |
| **MEV** | 7 | Front-running, sandwich attacks |
| **Oracle** | 8 | Price manipulation, staleness |
| **Tokens** | 8 | ERC20/721 handling |
| **Invariants** | 4 | Formal property tracking |
| **Upgradeability** | 3 | Proxy patterns |
| **Metadata** | 10+ | Visibility, mutability, etc. |

---

## Access Control Properties

### `has_access_gate` (Boolean)
**Type**: Function
**Purpose**: Indicates function has access control (modifier or inline)
**Detection**: Has modifier matching access keywords OR inline msg.sender check
**Keywords**: only, auth, role, admin, owner, guardian, governor

### `access_gate_logic` (Boolean)
**Type**: Function
**Purpose**: Has inline require(msg.sender == X) check
**Usage**: Distinguish modifier-based from inline access control

### `access_gate_modifiers` (List[String])
**Type**: Function
**Purpose**: Names of access control modifiers
**Example**: `["onlyOwner", "onlyAdmin"]`

### `access_gate_sources` (List[String])
**Type**: Function
**Purpose**: What the access check compares against
**Values**: `["msg.sender", "tx.origin", "mapping[msg.sender]"]`

### `writes_privileged_state` (Boolean)
**Type**: Function
**Purpose**: Writes to privileged state variables (owner, admin, role, etc.)
**Detection**: Writes to state vars with security tags: owner, admin, role, guardian, governor

### `has_auth_pattern` (Boolean)
**Type**: Function
**Purpose**: Uses recognized authentication pattern
**Detection**: Has modifiers classified as auth patterns

### `uses_tx_origin` (Boolean)
**Type**: Function
**Purpose**: Uses tx.origin (phishing vector)
**Risk**: Vulnerable to phishing attacks

### `uses_msg_sender` (Boolean)
**Type**: Function
**Purpose**: Reads msg.sender
**Usage**: Positive indicator for access control

### `public_wrapper_without_access_gate` (Boolean)
**Type**: Function
**Purpose**: Public/external wrapper calls internal logic without access control
**Detection**: visibility in [public, external] AND internal calls AND no access gate

### `governance_vote_without_snapshot` (Boolean)
**Type**: Function
**Purpose**: Governance voting uses live balances without a snapshot
**Detection**: Vote/proposal/quorum naming + reads balanceOf/reserves + no snapshot markers

### `multisig_threshold_change_without_gate` (Boolean)
**Type**: Function
**Purpose**: Multisig threshold updates without access control
**Detection**: Multisig contract + threshold in name/params + writes state + no access gate

### `multisig_signer_change_without_gate` (Boolean)
**Type**: Function
**Purpose**: Multisig signer/owner membership changes without access control
**Detection**: Multisig contract + signer/owner in name/params + writes state + no access gate

### `role_grant_like` (Boolean)
**Type**: Function
**Purpose**: Function appears to grant roles
**Detection**: Function name/params include grant/addrole/setrole/assignrole

### `role_revoke_like` (Boolean)
**Type**: Function
**Purpose**: Function appears to revoke roles
**Detection**: Function name/params include revoke/removerole

### `uses_selfdestruct` (Boolean)
**Type**: Function
**Purpose**: Function uses selfdestruct/suicide
**Detection**: Source text includes selfdestruct or suicide

### `multisig_threshold_is_zero` (Boolean)
**Type**: Contract
**Purpose**: Multisig threshold configured to zero
**Detection**: State var named threshold initialized to zero

### `governance_quorum_without_snapshot` (Boolean)
**Type**: Function
**Purpose**: Governance quorum/vote uses live balances without snapshot
**Detection**: Governance naming + reads balances/total supply + no snapshot markers

### `multisig_threshold_change_without_validation` (Boolean)
**Type**: Function
**Purpose**: Multisig threshold changes without validation
**Detection**: Threshold change + no threshold bounds check

### `multisig_signer_change_without_validation` (Boolean)
**Type**: Function
**Purpose**: Multisig signer/owner change without validation
**Detection**: Signer/owner change + no non-zero address check

### `governance_exec_without_timelock_check` (Boolean)
**Type**: Function
**Purpose**: Governance execution without timelock enforcement
**Detection**: Governance execute/queue function + timelock present + no timelock check

### `governance_exec_without_quorum_check` (Boolean)
**Type**: Function
**Purpose**: Governance execution without quorum enforcement
**Detection**: Governance execute function + no quorum check

### `governance_exec_without_vote_period_check` (Boolean)
**Type**: Function
**Purpose**: Governance execution without voting period enforcement
**Detection**: Governance execute function + no time-based vote period check

### `contract_has_multisig` (Boolean)
**Type**: Function
**Purpose**: Contract has multisig signals
**Detection**: Contract-level multisig heuristics applied to function context

### `contract_has_governance` (Boolean)
**Type**: Function
**Purpose**: Contract has governance signals
**Detection**: Contract-level governance heuristics applied to function context

### `uses_extcodesize` (Boolean)
**Type**: Function
**Purpose**: Function uses extcodesize/code.length
**Detection**: Source text contains extcodesize or code.length

### `uses_extcodehash` (Boolean)
**Type**: Function
**Purpose**: Function uses extcodehash
**Detection**: Source text contains extcodehash

### `uses_gasleft` (Boolean)
**Type**: Function
**Purpose**: Function uses gasleft
**Detection**: Source text contains gasleft

### `owner_uninitialized` (Boolean)
**Type**: Contract
**Purpose**: Owner variable declared without initialization
**Detection**: Owner state var exists with no initializer

### `default_admin_address_is_zero` (Boolean)
**Type**: Contract
**Purpose**: Default admin address set to zero
**Detection**: Default admin address state var initialized to address(0)

### `is_multisig_threshold_change` (Boolean)
**Type**: Function
**Purpose**: Function appears to change multisig threshold
**Detection**: Function name/params include threshold

### `is_multisig_member_change` (Boolean)
**Type**: Function
**Purpose**: Function appears to add/remove signer/owner
**Detection**: Function name/params include signer/owner/member

### `access_gate_uses_balance_check` (Boolean)
**Type**: Function
**Purpose**: Access control uses balance/balanceOf checks
**Detection**: require() expressions reference balance or balanceOf

### `multisig_member_change_without_minimum_check` (Boolean)
**Type**: Function
**Purpose**: Multisig signer changes without minimum signer checks
**Detection**: Signer change without owners.length/signers.length check

### `multisig_threshold_change_without_owner_count_check` (Boolean)
**Type**: Function
**Purpose**: Threshold changes without owner count validation
**Detection**: Threshold change without owners.length vs threshold check

### `access_gate_uses_contract_address` (Boolean)
**Type**: Function
**Purpose**: Access control uses address(this) comparisons
**Detection**: require() contains address(this) and msg.sender

### `access_gate_uses_hash_compare` (Boolean)
**Type**: Function
**Purpose**: Access control uses keccak256/string hash comparisons
**Detection**: require() contains keccak256 with equality check

### `has_role_events` (Boolean)
**Type**: Contract
**Purpose**: Role grants emit role-related events
**Detection**: Contract defines events with role/grant/revoke/admin in name

### `access_gate_has_if_return` (Boolean)
**Type**: Function
**Purpose**: Access control uses if-return instead of revert
**Detection**: Source contains if with msg.sender/tx.origin and return without revert

### `access_gate_without_sender_source` (Boolean)
**Type**: Function
**Purpose**: Access control does not reference msg.sender/tx.origin
**Detection**: Access gate present without sender/origin sources

---

## Reentrancy Properties

### `state_write_after_external_call` (Boolean)
**Type**: Function
**Purpose**: CEI violation - writes state after external call
**Risk**: Classic reentrancy (DAO hack pattern)
**Pattern**: `reentrancy-basic`

### `state_write_before_external_call` (Boolean)
**Type**: Function
**Purpose**: Safe CEI pattern - state updated before call
**Usage**: Negative test (safe pattern)

### `has_reentrancy_guard` (Boolean)
**Type**: Function
**Purpose**: Has nonReentrant modifier
**Detection**: Modifier name contains "nonreentrant"

---

## DoS Properties

### `has_loops` (Boolean)
**Type**: Function
**Purpose**: Contains loop constructs
**Usage**: Filter for loop-related analysis

### `loop_count` (Integer)
**Type**: Function
**Purpose**: Number of loops in function

### `loop_bound_sources` (List[String])
**Type**: Function
**Purpose**: Sources of loop iteration bounds
**Values**: `["user_input", "storage_length", "constant", "unknown"]`

### `has_unbounded_loop` (Boolean)
**Type**: Function
**Purpose**: Loop with user/unknown bounds, no constants
**Risk**: Gas exhaustion DoS

### `has_require_bounds` (Boolean) ⭐ NEW Dec 2025
**Type**: Function
**Purpose**: Has require() bounding loop parameters
**Detection**: `require(param <= MAX)` or `require(end - start <= LIMIT)`
**Impact**: Reduces false positives for pagination

### `external_calls_in_loop` (Boolean)
**Type**: Function
**Purpose**: Loop contains external calls
**Risk**: Block gas limit DoS

### `has_delete_in_loop` (Boolean)
**Type**: Function
**Purpose**: Loop contains delete operations

### `has_unbounded_deletion` (Boolean)
**Type**: Function
**Purpose**: Unbounded loop with delete
**Risk**: High gas cost DoS

### `uses_transfer` (Boolean) ⭐ NEW Dec 2025
**Type**: Function
**Purpose**: Uses deprecated .transfer() method
**Risk**: 2300 gas limit, DoS if recipient needs more

### `uses_send` (Boolean) ⭐ NEW Dec 2025
**Type**: Function
**Purpose**: Uses deprecated .send() method
**Risk**: 2300 gas limit

### `has_strict_equality_check` (Boolean) ⭐ NEW Dec 2025
**Type**: Function
**Purpose**: Strict equality on address(this).balance
**Risk**: Gridlock attack (Edgeware Lockdrop)

### `state_mutability` (String) ⭐ NEW Dec 2025
**Type**: Function
**Purpose**: Normalized state mutability
**Values**: `"pure"`, `"view"`, `"payable"`, `"nonpayable"`
**Usage**: View function DoS detection

---

## Crypto/Signature Properties

### `uses_ecrecover` (Boolean)
**Type**: Function
**Purpose**: Uses signature recovery

### `checks_zero_address` (Boolean)
**Type**: Function
**Purpose**: Validates ecrecover != address(0)
**Risk**: ecrecover returns 0x0 on invalid signature

### `checks_sig_v` (Boolean)
**Type**: Function
**Purpose**: Validates v in [27, 28]
**Risk**: Signature malleability

### `checks_sig_s` (Boolean)
**Type**: Function
**Purpose**: Validates s for malleability
**Detection**: Checks `s <= secp256k1 curve order / 2`

### `uses_chainid` (Boolean)
**Type**: Function
**Purpose**: Includes block.chainid in signature
**Risk**: Cross-chain replay without chainid

### `has_nonce_parameter` (Boolean)
**Type**: Function
**Purpose**: Has nonce parameter
**Usage**: Replay protection indicator

### `reads_nonce_state` (Boolean)
**Type**: Function
**Purpose**: Reads nonce from state

### `writes_nonce_state` (Boolean)
**Type**: Function
**Purpose**: Increments nonce (replay protection)

### `uses_domain_separator` (Boolean)
**Type**: Function
**Purpose**: Uses EIP-712 domain separator
**Usage**: Proper EIP-712 implementation

### `has_deadline_check` (Boolean)
**Type**: Function
**Purpose**: Validates deadline against block.timestamp
**Risk**: Signature replayable without expiration

### `is_permit_like` (Boolean)
**Type**: Function
**Purpose**: Function name contains "permit"
**Usage**: Target EIP-2612 analysis

### `has_signature_validity_checks` (Boolean)
**Type**: Function
**Purpose**: Complete signature validation (ecrecover + zero + deadline)
**Usage**: Comprehensive validation indicator

---

## MEV Properties

### `swap_like` (Boolean)
**Type**: Function
**Purpose**: Looks like token swap function
**Detection**: Name contains "swap", "exactinput", "exactoutput", "sell", "buy"

### `risk_missing_slippage_parameter` (Boolean)
**Type**: Function
**Purpose**: Swap function without slippage parameter
**Risk**: Sandwich attack vulnerability

### `risk_missing_deadline_check` (Boolean)
**Type**: Function
**Purpose**: Swap function without deadline
**Risk**: Transaction can be delayed indefinitely

### `has_slippage_parameter` (Boolean)
**Type**: Function
**Purpose**: Has parameter like minOut, amountOutMin
**Usage**: Slippage protection present

### `has_slippage_check` (Boolean)
**Type**: Function
**Purpose**: Validates slippage parameter in require
**Detection**: require() mentions slippage param with comparison

### `has_deadline_parameter` (Boolean)
**Type**: Function
**Purpose**: Has deadline/expiry/expiration parameter

### `risk_missing_twap_window` (Boolean)
**Type**: Function
**Purpose**: Uses TWAP without window parameter
**Risk**: Manipulation via short observation window

---

## Oracle Properties

### `reads_oracle_price` (Boolean)
**Type**: Function
**Purpose**: Calls oracle (Chainlink, etc.)
**Detection**: Calls latestAnswer, latestRoundData, getPrice

### `has_staleness_check` (Boolean)
**Type**: Function
**Purpose**: Validates updatedAt timestamp
**Detection**: require() mentions updatedAt, answeredInRound, roundId

### `oracle_round_check` (Boolean)
**Type**: Function
**Purpose**: Validates answeredInRound matches roundId
**Usage**: Proper Chainlink oracle usage

### `oracle_freshness_ok` (Boolean)
**Type**: Function
**Purpose**: Complete oracle freshness validation
**Requires**: has_staleness_check AND oracle_round_check

### `has_sequencer_uptime_check` (Boolean)
**Type**: Function
**Purpose**: L2 sequencer uptime validation
**Usage**: Arbitrum/Optimism oracle safety

### `l2_oracle_context` (Boolean)
**Type**: Function
**Purpose**: Oracle used in L2 context
**Detection**: Mentions sequencer, l2, or reads sequencer state

### `reads_twap` (Boolean)
**Type**: Function
**Purpose**: Uses TWAP oracle
**Detection**: Calls consult, observe, price0Cumulative

### `reads_twap_with_window` (Boolean)
**Type**: Function
**Purpose**: TWAP with configurable window
**Requires**: reads_twap AND has_twap_window_parameter

### `has_twap_window_parameter` (Boolean)
**Type**: Function
**Purpose**: Has parameter like secondsAgo, window, interval

---

## Token Properties

### `uses_erc20_transfer` (Boolean)
**Type**: Function
**Purpose**: Calls ERC20 transfer()

### `uses_erc20_transfer_from` (Boolean)
**Type**: Function
**Purpose**: Calls ERC20 transferFrom()

### `uses_erc20_approve` (Boolean)
**Type**: Function
**Purpose**: Calls ERC20 approve()

### `token_return_guarded` (Boolean)
**Type**: Function
**Purpose**: Checks return value OR uses SafeERC20
**Risk**: Unchecked transfer can silently fail (USDT)

### `uses_safe_erc20` (Boolean)
**Type**: Function
**Purpose**: Uses SafeERC20 library
**Detection**: Calls safeTransfer, safeTransferFrom, safeApprove

### `uses_erc20_mint` (Boolean)
**Type**: Function
**Purpose**: Calls mint()

### `uses_erc20_burn` (Boolean)
**Type**: Function
**Purpose**: Calls burn()

### `uses_erc721_safe_transfer` (Boolean)
**Type**: Function
**Purpose**: Calls safeTransferFrom() (ERC721)

---

## Invariant Properties

### `touches_invariant` (Boolean)
**Type**: Function
**Purpose**: Reads/writes state vars mentioned in invariants
**Usage**: Functions that must preserve invariants

### `has_invariant_check` (Boolean)
**Type**: Function
**Purpose**: Has require() validating invariant state vars
**Detection**: require() mentions invariant-related variables

### `touches_invariant_unchecked` (Boolean) ⚠️ Vulnerability
**Type**: Function
**Purpose**: Touches invariant state WITHOUT validation
**Detection**: touches_invariant AND NOT has_invariant_check
**Risk**: Invariant violation

### `invariant_state_vars` (List[String])
**Type**: Function
**Purpose**: Names of invariant state vars read/written
**Example**: `["totalSupply", "totalShares"]`

---

## Upgradeability Properties

### `is_upgrade_function` (Boolean)
**Type**: Function
**Purpose**: Function name suggests upgrade operation
**Detection**: Name contains "upgrade", "setImplementation", "setBeacon"

### `is_initializer_function` (Boolean)
**Type**: Function
**Purpose**: Function name suggests initializer
**Detection**: Name contains "initialize"

### `upgrade_guarded` (Boolean)
**Type**: Function
**Purpose**: Upgrade function with access control
**Requires**: is_upgrade_function AND has_access_gate

---

## Call Properties

### `has_external_calls` (Boolean) ⭐ ENHANCED Dec 2025
**Type**: Function
**Purpose**: Contains external calls (high-level OR low-level)
**Enhancement**: Now includes .call{value}(""), .delegatecall(), .staticcall()
**Usage**: Reentrancy, DoS analysis

### `external_call_count` (Integer)
**Type**: Function
**Purpose**: Number of external calls

### `internal_call_count` (Integer)
**Type**: Function
**Purpose**: Number of internal calls

### `has_internal_calls` (Boolean)
**Type**: Function
**Purpose**: Contains internal calls

### `uses_delegatecall` (Boolean)
**Type**: Function
**Purpose**: Uses delegatecall
**Risk**: Arbitrary delegatecall vulnerability

### `uses_call` (Boolean)
**Type**: Function
**Purpose**: Uses .call or .staticcall

### `low_level_calls` (List[String])
**Type**: Function
**Purpose**: Names of low-level calls
**Example**: `["call", "delegatecall"]`

---

## State Interaction Properties

### `reads_state` (Boolean)
**Type**: Function
**Purpose**: Reads state variables

### `reads_state_count` (Integer)
**Type**: Function
**Purpose**: Number of state variables read

### `writes_state` (Boolean)
**Type**: Function
**Purpose**: Writes state variables

### `writes_state_count` (Integer)
**Type**: Function
**Purpose**: Number of state variables written

### `state_write_targets` (List[String])
**Type**: Function
**Purpose**: Security tags of written state vars
**Example**: `["owner", "role", "fee"]`

---

## Metadata Properties

### `visibility` (String)
**Type**: Function
**Purpose**: Function visibility
**Values**: `"public"`, `"external"`, `"internal"`, `"private"`

### `mutability` (String)
**Type**: Function
**Purpose**: Slither's raw state_mutability attribute

### `state_mutability` (String) ⭐ NEW Dec 2025
**Type**: Function
**Purpose**: Normalized state mutability
**Values**: `"pure"`, `"view"`, `"payable"`, `"nonpayable"`

### `payable` (Boolean)
**Type**: Function
**Purpose**: Function is payable

### `is_constructor` (Boolean)
**Type**: Function
**Purpose**: Is constructor

### `is_fallback` (Boolean)
**Type**: Function
**Purpose**: Is fallback function

### `is_receive` (Boolean)
**Type**: Function
**Purpose**: Is receive function

### `signature` (String)
**Type**: Function
**Purpose**: Function signature

### `modifiers` (List[String])
**Type**: Function
**Purpose**: All modifier names

### `parameter_names` (List[String])
**Type**: Function
**Purpose**: Parameter names

---

## Contract Properties

### `kind` (String)
**Type**: Contract
**Purpose**: Contract kind
**Values**: `"contract"`, `"interface"`, `"library"`

### `has_initializer` (Boolean)
**Type**: Contract
**Purpose**: Has initialize() function

### `has_upgrade_function` (Boolean)
**Type**: Contract
**Purpose**: Has upgrade functions

### `is_proxy_like` (Boolean)
**Type**: Contract
**Purpose**: Name or structure suggests proxy

### `proxy_type` (String)
**Type**: Contract
**Purpose**: Detected proxy pattern
**Values**: `"uups"`, `"transparent"`, `"beacon"`, `"generic"`, `"none"`

### `has_storage_gap` (Boolean)
**Type**: Contract
**Purpose**: Has storage gap arrays

### `storage_gap_sizes` (List[Integer])
**Type**: Contract
**Purpose**: Sizes of storage gap arrays
**Example**: `[50, 100]`

### `upgradeable_without_storage_gap` (Boolean) ⚠️ Vulnerability
**Type**: Contract
**Purpose**: Upgradeable but missing storage gap
**Risk**: Storage collision on upgrade

---

## StateVariable Properties

### `type` (String)
**Type**: StateVariable
**Purpose**: Solidity type

### `visibility` (String)
**Type**: StateVariable
**Purpose**: Variable visibility
**Values**: `"public"`, `"internal"`, `"private"`

### `security_tags` (List[String])
**Type**: StateVariable
**Purpose**: Security-relevant classifications
**Values**: `["owner", "admin", "role", "paused", "fee", "nonce", etc.]`

---

## Loop Node Properties

### `bound_sources` (List[String])
**Type**: Loop
**Purpose**: Sources of this specific loop's bounds
**Values**: `["user_input", "storage_length", "constant", "unknown"]`

### `has_external_call` (Boolean)
**Type**: Loop
**Purpose**: This loop contains external calls

### `has_delete` (Boolean)
**Type**: Loop
**Purpose**: This loop contains delete operations

---

## Invariant Node Properties

### `text` (String)
**Type**: Invariant
**Purpose**: Full invariant text from NatSpec

### `source_kind` (String)
**Type**: Invariant
**Purpose**: Source of invariant
**Values**: `"natspec"`, `"config"` (future: formal spec languages)

### `target_type` (String)
**Type**: Invariant
**Purpose**: What the invariant applies to
**Values**: `"Contract"`, `"Function"`, `"StateVariable"`

### `target_name` (String)
**Type**: Invariant
**Purpose**: Name of target entity

### `state_vars` (List[String])
**Type**: Invariant
**Purpose**: State variables referenced in invariant

### `guard_functions` (List[String])
**Type**: Invariant
**Purpose**: Guard functions that re-check the invariant

---

## Property Naming Conventions

**Boolean Properties**:
- `has_*` - Presence/absence (has_access_gate, has_loops)
- `is_*` - Classification (is_constructor, is_proxy_like)
- `uses_*` - Usage detection (uses_delegatecall, uses_ecrecover)
- `writes_*` / `reads_*` - State interaction
- `checks_*` - Validation presence
- `risk_*` - Vulnerability indicator (risk_missing_slippage_parameter)

**List Properties**:
- Plural names: `modifiers`, `parameter_names`, `state_vars`
- Sorted for determinism

**String Properties**:
- Lowercase values for consistency
- Normalized (state_mutability)

---

## Query Usage Examples

### Find Vulnerable Functions

```bash
# Unbounded loops without bounds check
uv run alphaswarm query "find functions where has_unbounded_loop and not has_require_bounds"

# Reentrancy without guard
uv run alphaswarm query "find functions where state_write_after_external_call and not has_reentrancy_guard"

# Weak access control
uv run alphaswarm query "find functions where writes_privileged_state and not has_access_gate"

# Transfer without return check
uv run alphaswarm query "find functions where uses_erc20_transfer and not token_return_guarded"
```

### Combine Multiple Properties

```bash
# Public functions writing state after external call (reentrancy risk)
uv run alphaswarm query '{
  "query_kind": "logic",
  "node_types": ["Function"],
  "match": {
    "all": [
      {"property": "visibility", "op": "in", "value": ["public", "external"]},
      {"property": "state_write_after_external_call", "op": "eq", "value": true}
    ],
    "none": [
      {"property": "has_reentrancy_guard", "op": "eq", "value": true}
    ]
  }
}'
```

---

## Property Evolution

### Phase 1 (2023-2024): Foundation
- Access control properties (8)
- Basic reentrancy (3)
- Call detection (4)

### Phase 2 (2024 Q1-Q3): Expansion
- Crypto/signatures (12)
- MEV (7)
- Oracle (8)
- Tokens (8)
- Proxy/upgrade (3)

### Phase 3 (2024 Q4): DoS Initial
- Loop analysis (5)

### Phase 4 (2025 Dec): DoS Enhancement
- ✅ has_require_bounds (reduce false positives)
- ✅ uses_transfer / uses_send (gas limit DoS)
- ✅ has_strict_equality_check (gridlock)
- ✅ state_mutability (view function DoS)
- ✅ Enhanced has_external_calls (low-level calls)

### Phase 5 (2025 Dec): Invariants
- ✅ Invariant extraction (4 properties)
- ✅ touches_invariant_unchecked (violation detection)

---

## Performance Characteristics

**Property Derivation Cost** (per function):
- Simple boolean flags: ~1µs
- String comparisons: ~2µs
- List building: ~5µs
- Regex matching: ~10µs
- IR traversal: ~20µs

**Total per Function**: ~500µs (0.5ms)

**Caching**: Properties derived once during graph build, cached in JSON.

---

## Future Properties (Roadmap)

- 🔮 has_assembly_block (inline assembly detection)
- 🔮 gas_complexity_estimate (function gas complexity)
- 🔮 state_dependency_depth (state read/write depth)
- 🔮 external_dependency_count (imported contract calls)
- 🔮 has_try_catch (error handling presence)

---

*For pattern authoring guide, see [Pattern Pack Guide](../guides/pattern-packs.md)*
