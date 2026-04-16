# Property Reference

**275 Emitted Security Properties Derived by BSKG Builder**

---

## Quick Reference Table

| Category | Key Properties | Risk Level |
|----------|---------------|------------|
| **Access Control** | `has_access_gate`, `writes_privileged_state`, `uses_tx_origin` | High |
| **Reentrancy** | `state_write_after_external_call`, `has_reentrancy_guard` | Critical |
| **DoS** | `has_unbounded_loop`, `external_calls_in_loop`, `uses_transfer` | High |
| **Crypto** | `uses_ecrecover`, `checks_zero_address`, `uses_chainid` | High |
| **MEV** | `swap_like`, `risk_missing_slippage_parameter` | Medium |
| **Oracle** | `reads_oracle_price`, `has_staleness_check` | High |
| **Tokens** | `uses_erc20_transfer`, `token_return_guarded` | Medium |

---

## Access Control Properties

| Property | Type | Description |
|----------|------|-------------|
| `has_access_gate` | bool | Has access control (modifier or inline check) |
| `access_gate_logic` | bool | Has inline `require(msg.sender == X)` |
| `access_gate_modifiers` | list | Auth modifier names (`["onlyOwner"]`) |
| `writes_privileged_state` | bool | Writes owner/admin/role vars |
| `uses_tx_origin` | bool | Uses tx.origin (phishing risk) |
| `uses_msg_sender` | bool | Reads msg.sender |
| `public_wrapper_without_access_gate` | bool | Public wrapper missing auth |
| `role_grant_like` | bool | Function grants roles |
| `role_revoke_like` | bool | Function revokes roles |
| `uses_selfdestruct` | bool | Uses selfdestruct |

**Governance Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `governance_vote_without_snapshot` | bool | Voting uses live balances |
| `governance_exec_without_timelock_check` | bool | Execute without timelock |
| `governance_exec_without_quorum_check` | bool | Execute without quorum |

**Multisig Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `multisig_threshold_change_without_gate` | bool | Threshold change unprotected |
| `multisig_signer_change_without_gate` | bool | Signer change unprotected |
| `multisig_threshold_is_zero` | bool | Threshold configured to zero |

---

## Reentrancy Properties

| Property | Type | Description |
|----------|------|-------------|
| `state_write_after_external_call` | bool | CEI violation (DAO hack pattern) |
| `state_write_before_external_call` | bool | Safe CEI pattern |
| `has_reentrancy_guard` | bool | Has nonReentrant modifier |

---

## DoS Properties

| Property | Type | Description |
|----------|------|-------------|
| `has_loops` | bool | Contains loop constructs |
| `loop_count` | int | Number of loops |
| `has_unbounded_loop` | bool | Loop with user-controlled bounds |
| `has_require_bounds` | bool | Has require() bounding loops |
| `external_calls_in_loop` | bool | External call in loop body |
| `has_unbounded_deletion` | bool | Unbounded delete in loop |
| `uses_transfer` | bool | Uses .transfer() (2300 gas limit) |
| `uses_send` | bool | Uses .send() (2300 gas limit) |
| `has_strict_equality_check` | bool | Strict == on balance (gridlock) |

---

## Crypto/Signature Properties

| Property | Type | Description |
|----------|------|-------------|
| `uses_ecrecover` | bool | Uses signature recovery |
| `checks_zero_address` | bool | Validates ecrecover != 0 |
| `checks_sig_v` | bool | Validates v in [27, 28] |
| `checks_sig_s` | bool | Validates s for malleability |
| `uses_chainid` | bool | Includes chain ID |
| `has_nonce_parameter` | bool | Has nonce parameter |
| `reads_nonce_state` | bool | Reads nonce from state |
| `writes_nonce_state` | bool | Increments nonce |
| `uses_domain_separator` | bool | Uses EIP-712 domain |
| `has_deadline_check` | bool | Validates deadline |
| `is_permit_like` | bool | Function name contains "permit" |

---

## MEV Properties

| Property | Type | Description |
|----------|------|-------------|
| `swap_like` | bool | Looks like swap function |
| `risk_missing_slippage_parameter` | bool | Swap without slippage |
| `risk_missing_deadline_check` | bool | Swap without deadline |
| `has_slippage_parameter` | bool | Has minOut parameter |
| `has_slippage_check` | bool | Validates slippage |
| `has_deadline_parameter` | bool | Has deadline param |
| `risk_missing_twap_window` | bool | TWAP without window |

---

## Oracle Properties

| Property | Type | Description |
|----------|------|-------------|
| `reads_oracle_price` | bool | Calls oracle |
| `has_staleness_check` | bool | Validates updatedAt |
| `oracle_round_check` | bool | Validates roundId |
| `oracle_freshness_ok` | bool | Complete oracle validation |
| `has_sequencer_uptime_check` | bool | L2 sequencer check |
| `l2_oracle_context` | bool | Oracle in L2 context |
| `reads_twap` | bool | Uses TWAP oracle |
| `has_twap_window_parameter` | bool | TWAP has window param |

---

## Token Properties

| Property | Type | Description |
|----------|------|-------------|
| `uses_erc20_transfer` | bool | Calls transfer() |
| `uses_erc20_transfer_from` | bool | Calls transferFrom() |
| `uses_erc20_approve` | bool | Calls approve() |
| `token_return_guarded` | bool | Checks return OR uses SafeERC20 |
| `uses_safe_erc20` | bool | Uses SafeERC20 library |
| `uses_erc20_mint` | bool | Calls mint() |
| `uses_erc20_burn` | bool | Calls burn() |

---

## Call Properties

| Property | Type | Description |
|----------|------|-------------|
| `has_external_calls` | bool | Any external call (incl. low-level) |
| `external_call_count` | int | Number of external calls |
| `has_internal_calls` | bool | Contains internal calls |
| `uses_delegatecall` | bool | Uses delegatecall |
| `uses_call` | bool | Uses .call or .staticcall |
| `low_level_calls` | list | Low-level call types |

---

## State Interaction

| Property | Type | Description |
|----------|------|-------------|
| `reads_state` | bool | Reads state variables |
| `writes_state` | bool | Writes state variables |
| `reads_state_count` | int | Number of vars read |
| `writes_state_count` | int | Number of vars written |
| `state_write_targets` | list | Security tags of written vars |

---

## Invariant Properties

| Property | Type | Description |
|----------|------|-------------|
| `touches_invariant` | bool | Reads/writes invariant state |
| `has_invariant_check` | bool | Has require validating invariant |
| `touches_invariant_unchecked` | bool | Touches without checking |
| `invariant_state_vars` | list | Invariant var names |

---

## Upgradeability Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_upgrade_function` | bool | Upgrade function |
| `is_initializer_function` | bool | Initializer function |
| `upgrade_guarded` | bool | Upgrade has access control |

---

## Metadata Properties

| Property | Type | Description |
|----------|------|-------------|
| `visibility` | string | public/external/internal/private |
| `state_mutability` | string | pure/view/payable/nonpayable |
| `payable` | bool | Function is payable |
| `is_constructor` | bool | Is constructor |
| `is_fallback` | bool | Is fallback function |
| `is_receive` | bool | Is receive function |
| `signature` | string | Function signature |
| `modifiers` | list | All modifier names |
| `parameter_names` | list | Parameter names |

---

## Contract Properties

| Property | Type | Description |
|----------|------|-------------|
| `kind` | string | contract/interface/library |
| `has_initializer` | bool | Has initialize() |
| `has_upgrade_function` | bool | Has upgrade functions |
| `is_proxy_like` | bool | Detected as proxy |
| `proxy_type` | string | uups/transparent/beacon/none |
| `has_storage_gap` | bool | Has __gap arrays |
| `upgradeable_without_storage_gap` | bool | Missing storage gap |

---

## StateVariable Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | string | Solidity type |
| `visibility` | string | public/internal/private |
| `security_tags` | list | Security classifications |
| `is_constant` | bool | Constant variable |
| `is_immutable` | bool | Immutable variable |

**Security Tags:**
- `owner`, `admin`, `role`, `guardian` - Authority
- `paused`, `locked`, `frozen` - Circuit breakers
- `fee`, `rate`, `treasury` - Value movement
- `whitelist`, `blacklist` - Access lists
- `nonce`, `used`, `claimed` - Replay protection

---

## Naming Conventions

| Prefix | Meaning | Example |
|--------|---------|---------|
| `has_*` | Presence/absence | `has_access_gate` |
| `is_*` | Classification | `is_constructor` |
| `uses_*` | Usage detection | `uses_delegatecall` |
| `writes_*` | State write | `writes_state` |
| `reads_*` | State read | `reads_oracle_price` |
| `checks_*` | Validation presence | `checks_zero_address` |
| `risk_*` | Vulnerability indicator | `risk_missing_slippage_parameter` |

---

*See [Operations Reference](operations.md) for semantic operations.*
*See [Architecture](../architecture.md) for system design.*
