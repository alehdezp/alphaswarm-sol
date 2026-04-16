# Property Schema Contract

**Purpose:** Define the contract (type, semantics, invariants) for critical builder properties.

**Last Updated:** 2026-01-07

---

## Property Contract Format

Each property is documented with:
- **Type**: Python type (bool, int, list, str)
- **Default**: Value when not applicable
- **Semantics**: What the property means
- **Invariants**: Conditions that must always hold
- **Patterns Using**: Which vulnerability patterns depend on this property
- **Examples**: True positive and true negative examples

---

## Access Control Properties

### 1. `has_access_gate`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function has modifier or logic that restricts who can call it |
| **Invariants** | If `True`, then `access_gate_sources` is non-empty |

**True when:**
- Has `onlyOwner` modifier
- Has `require(msg.sender == owner)`
- Has role-based checks (`hasRole`)

**False when:**
- No access restrictions
- Only internal visibility (not counted as gate)

**Patterns Using:**
- `auth-001` (missing access control)
- `callback-controlled-recipient`
- `flash-loan-reward-attack`

---

### 2. `writes_privileged_state`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function modifies owner, admin, role, or configuration state |
| **Invariants** | If `True`, state variable must be security-sensitive |

**True when:**
- Writes to `owner`, `admin`, `role` variables
- Modifies access control mappings
- Changes critical configuration

**False when:**
- Only writes user balances
- Only writes non-privileged state

**Patterns Using:**
- `auth-005` (unprotected privileged write)
- `auth-012` (unprotected role change)

---

### 3. `public_wrapper_without_access_gate`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Public/external function that calls internal functions without access control |
| **Invariants** | Must be public/external visibility |

**True when:**
- Visibility is `public` or `external`
- Has internal calls
- No access gate detected

**False when:**
- Has any access modifier
- Internal/private visibility

**Patterns Using:**
- `callback-controlled-recipient`
- `external-call-public-no-gate`

---

## Value Transfer Properties

### 4. `is_value_transfer`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function transfers ETH or tokens to a recipient |
| **Invariants** | If `True`, function must have transfer/send/call operations |

**True when:**
- Uses `transfer()`, `send()`, `call{value:}()`
- Uses ERC20 `transfer()`, `safeTransfer()`
- Has value-sending operations

**False when:**
- Only reads balances
- Only writes state without transfers

**Patterns Using:**
- `callback-controlled-recipient`
- `unprotected-value-transfer`

---

### 5. `payment_recipient_controllable`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Transfer recipient is derived from user-controlled input |
| **Invariants** | Requires `is_value_transfer` to be relevant |

**True when:**
- Recipient is function parameter
- Recipient derived from callback data
- Recipient from external call result

**False when:**
- Recipient is `msg.sender`
- Recipient is hardcoded constant
- Recipient from storage (owner)

**Patterns Using:**
- `callback-controlled-recipient`
- `arbitrary-recipient-transfer`

---

### 6. `can_affect_user_funds`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function can modify user token balances or ETH |
| **Invariants** | High-impact property requiring careful validation |

**True when:**
- Transfers user tokens
- Burns/mints affecting user shares
- Modifies user balance mappings

**False when:**
- Only affects contract's own balance
- Only reads without modification

**Patterns Using:**
- `flash-loan-reward-attack`
- `governance-flash-loan`

---

## Callback Properties

### 7. `callback_chain_surface`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function is a callback from protocol integration |
| **Invariants** | Should implement interface or have callback naming |

**True when:**
- Implements callback interface (IProxyCreationCallback, etc.)
- Has `on*` naming pattern (onFlashLoan, onCallback)
- Called by external protocol during operation

**False when:**
- Regular entry point
- Internal helper function

**Patterns Using:**
- `callback-controlled-recipient`
- `flash-loan-callback`

---

### 8. `protocol_callback_chain_surface`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Callback from DeFi protocol (Uniswap, Aave, etc.) |
| **Invariants** | Subset of `callback_chain_surface` |

**True when:**
- Flash loan receiver callback
- DEX swap callback
- Proxy creation callback

**False when:**
- General callback without protocol context

**Patterns Using:**
- `callback-controlled-recipient`

---

## Loop & DoS Properties

### 9. `has_unbounded_loop`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function has loop without upper bound check |
| **Invariants** | If `True`, `loop_bound_sources` shows where bound comes from |

**True when:**
- Iterates over user-controlled array
- Iterates over storage array without length limit
- While loop without iteration cap

**False when:**
- Fixed iteration count
- Has explicit require on array length

**Patterns Using:**
- `dos-001` (unbounded loop)
- `msg-value-loop-reuse`

---

### 10. `has_loops`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function contains for/while loops |
| **Invariants** | If `True`, `loop_count >= 1` |

**True when:**
- Has `for` loop
- Has `while` loop
- Has `do-while` loop

**False when:**
- No loop constructs

**Patterns Using:**
- `msg-value-loop-reuse`
- `external-call-in-loop`

---

## Oracle Properties

### 11. `balance_used_for_collateralization`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Token balance or reserves used to calculate collateral value |
| **Invariants** | High-risk oracle manipulation indicator |

**True when:**
- Reads balance for loan-to-value calculation
- Uses reserves for price oracle
- Collateral requirement based on balance

**False when:**
- Balance only for transfer amounts
- Balance for UI display

**Patterns Using:**
- `dex-oracle-manipulation`

---

### 12. `has_staleness_check`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Oracle price validated for freshness |
| **Invariants** | Implies oracle usage |

**True when:**
- Checks `updatedAt` timestamp
- Validates price age
- Has time-based validation

**False when:**
- Uses price without time check

**Patterns Using:**
- `oracle-003` (missing staleness)

---

## Governance Properties

### 13. `governance_exec_without_quorum_check`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Governance execution without validating quorum |
| **Invariants** | Specific to governance contracts |

**True when:**
- Executes proposal without quorum validation
- Missing vote count check

**False when:**
- Validates quorum before execution
- Non-governance context

**Patterns Using:**
- `governance-flash-loan`

---

## Reentrancy Properties

### 14. `state_write_after_external_call`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | State variable modified after external call (CEI violation) |
| **Invariants** | Key reentrancy indicator |

**True when:**
- External call precedes state write
- Write happens in code path after call

**False when:**
- State writes before all external calls
- Has reentrancy guard

**Patterns Using:**
- `reentrancy-basic`
- `state-write-after-call`

---

### 15. `has_reentrancy_guard`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function protected by reentrancy guard |
| **Invariants** | Mitigates reentrancy findings |

**True when:**
- Has `nonReentrant` modifier
- Uses lock pattern
- OpenZeppelin ReentrancyGuard

**False when:**
- No guard detected

**Patterns Using:**
- None condition in reentrancy patterns

---

## Financial Properties

### 16. `is_withdraw_like`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function withdraws/claims user funds |
| **Invariants** | Name-agnostic semantic detection |

**True when:**
- Reads user balance and transfers out
- Has withdraw/claim semantic pattern
- Reduces user's stored balance

**False when:**
- Deposit function
- Internal transfer

**Patterns Using:**
- `flash-loan-reward-attack`

---

### 17. `accounting_update_missing`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Value transfer without corresponding balance update |
| **Invariants** | Indicates potential accounting bug |

**True when:**
- Transfers value but doesn't update balance mapping
- Missing state update in transfer path

**False when:**
- Proper balance update before/after transfer

**Patterns Using:**
- `flash-loan-reward-attack`

---

## External Call Properties

### 18. `has_untrusted_external_call`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | External call to potentially untrusted target |
| **Invariants** | Call target not validated as trusted |

**True when:**
- Call target from user input
- Call to arbitrary address
- Low-level call without target validation

**False when:**
- Call to known contract
- Call target from trusted storage

**Patterns Using:**
- `arbitrary-call-target`

---

## Payable Properties

### 19. `payable`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function can receive ETH |
| **Invariants** | Direct from Solidity attribute |

**True when:**
- Has `payable` modifier

**False when:**
- Not payable

**Patterns Using:**
- `msg-value-loop-reuse`

---

### 20. `has_internal_calls`

| Field | Value |
|-------|-------|
| **Type** | `bool` |
| **Default** | `False` |
| **Semantics** | Function calls other internal/private functions |
| **Invariants** | Indicates composition |

**True when:**
- Calls internal functions
- Calls private functions
- Uses helper functions

**False when:**
- Standalone function

**Patterns Using:**
- `msg-value-loop-reuse`

---

## Schema Invariants (Global)

1. **Boolean Consistency**: All bool properties default to `False`
2. **List Consistency**: All list properties default to `[]`
3. **Integer Consistency**: All integer properties default to `0`
4. **Dependency Integrity**: Related properties are consistent
5. **Determinism**: Same code produces same property values

---

## Validation Rules

```python
def validate_property_consistency(node: dict) -> list[str]:
    """Validate property consistency for a node."""
    errors = []
    props = node.get("properties", {})

    # Rule 1: has_access_gate implies access_gate_sources
    if props.get("has_access_gate") and not props.get("access_gate_sources"):
        errors.append("has_access_gate=True but access_gate_sources is empty")

    # Rule 2: has_loops implies loop_count >= 1
    if props.get("has_loops") and props.get("loop_count", 0) < 1:
        errors.append("has_loops=True but loop_count < 1")

    # Rule 3: is_value_transfer should imply transfer operations
    if props.get("is_value_transfer") and not (
        props.get("uses_transfer") or
        props.get("uses_erc20_transfer") or
        props.get("has_call_with_value")
    ):
        errors.append("is_value_transfer=True but no transfer operation detected")

    return errors
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-07 | Initial schema for 20 properties |

---

*This document defines the contract between builder.py and patterns. Changes to these properties require pattern review.*
