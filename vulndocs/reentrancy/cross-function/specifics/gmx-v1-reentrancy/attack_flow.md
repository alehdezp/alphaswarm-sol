# GMX V1 Attack Flow: Step-by-Step Breakdown

## The Exploit Timeline

### Setup Phase
The attacker prepares a malicious contract that will serve as the "account" parameter in the vulnerable function call.

```solidity
// Attacker's malicious contract
contract AttackerContract {
    address public gmx;

    // Fallback receives the gas refund and gains control
    receive() external payable {
        // Reentrancy window opens here!
        // Can call back into GMX functions before state is finalized
    }

    fallback() external payable {
        // Alternative callback vector
    }
}
```

### Attack Execution

#### Step 1: Trigger `executeDecreaseOrder()` with Malicious Account
```
Attacker calls: executeDecreaseOrder(_account=AttackerContract)
```

**Semantic Operations:**
- `CALLS_EXTERNAL` (attacker calls the vulnerable function)
- `INPUTS_UNTRUSTED` (attacker provides the account parameter)

---

#### Step 2: Position List Updated
```
Function state: Short position removed from global position list
```

**Semantic Operations:**
- `WRITES_SHARED_STATE` (position list modified)
- `MODIFIES_CRITICAL_STATE` (affects protocol accounting)

**Graph Signal:** `state_write_after_external_call = true`

---

#### Step 3: ETH Refund Triggers Callback
```solidity
// This line transfers control to the attacker's contract
call{value: gasRefund}(_account)  // ← Reentrancy window opens
```

**Semantic Operations:**
- `TRANSFERS_VALUE_OUT` (sends ETH)
- `CALLS_EXTERNAL` (to untrusted address)
- `TRIGGERS_CALLBACK` (enables reentrancy)

---

#### Step 4: Attacker Gains Control in Callback
The attacker's `receive()` or `fallback()` function executes with the contract state **inconsistent**:

- Short position list: **UPDATED** (position removed)
- Global average price: **NOT YET UPDATED** (still stale)
- AUM calculation: **Based on stale price**
- GLP tokens: **Currently overvalued based on stale data**

**Critical Gap:** There's a temporal inconsistency between two related state variables.

**Semantic Operations:**
- `EXECUTES_CALLBACK` (attacker's function runs)
- `READS_SHARED_STATE` (attacker reads the protocol's state)

---

#### Step 5: Attacker Manipulates Positions via Callback
While the protocol state is inconsistent, the attacker calls position management functions:

```solidity
// Inside attacker's receive() callback:
function receive() external payable {
    // Re-enter position functions while global price is stale
    gmx.decreasePosition(...)  // Manipulates positions
    gmx.updatePrice(...)        // May trigger more state changes
    gmx.readGlobalPrice()       // Reads stale price
}
```

**What Happens:**
- Attacker operations see the short position **already removed** from the list
- Attacker operations read the global average price **not yet updated**
- This mismatch creates artificial pricing distortion

**Semantic Operations:**
- `REENTERS_CONTEXT` (re-enters the same or different function)
- `READS_SHARED_STATE` (reads now-stale global price)
- `MODIFIES_CRITICAL_STATE` (further manipulates positions)

---

#### Step 6: Price Manipulation via Stale State
The attacker exploits the temporal gap:

**Before Attack:**
- BTC short position exists in global list
- Global average short price: $109,515.05
- AUM: Calculated using $109,515.05 price

**During Callback:**
- BTC short position: ALREADY REMOVED from list (step 2)
- Global average price: STILL $109,515.05 (not updated)
- Attacker actions: Manipulate other positions

**Result:**
- Attacker's operations artificially lower the global average price to $1,913.70
- But the system can't detect this because the position list is already updated
- This creates **extreme price distortion**

**Semantic Operations:**
- `MODIFIES_PRICE_ORACLE` (manipulates price calculations)
- `READS_ORACLE` (reads stale price values)

---

#### Step 7: AUM Inflation from Stale Price
The GLP system calculates Assets Under Management based on:
- Protocol holdings
- Position valuations
- Global average prices

With the artificially depressed global price (driven down from $109,515 to $1,913):

```
AUM = Σ(position_value) + protocol_reserves
    where position_value = position_size × global_price

Stale global_price = $1,913 (artificially low)
→ AUM appears much smaller than reality
→ This affects GLP token valuation
```

**Wait for the paradox:**
Actually, a lower average price makes position values appear smaller, which should make AUM lower. But the attack's sophistication involves the **circular relationship** between positions, prices, and token supply. When one decreases artificially, it cascades through the system.

**Semantic Operations:**
- `READS_AUM_CALCULATION` (reads AUM which depends on stale price)
- `MODIFIES_TOKEN_VALUATION` (affects GLP token value)

---

#### Step 8: GLP Token Valuation Inflation
The GLP system values tokens based on:
```
GLP_value_per_token = AUM / total_GLP_supply
```

With the stale price manipulation creating AUM distortion:
- GLP tokens become **overvalued**
- Attacker can now redeem fewer tokens for larger underlying value

**Semantic Operations:**
- `MODIFIES_TOKEN_SUPPLY_TRACKING` (affects valuation)
- `READS_ORACLE` (reads manipulated prices)

---

#### Step 9: Attacker Redeems Overvalued GLP
```solidity
// Attacker redeems GLP tokens while they're overvalued
glp.redeem(amount, recipient)
→ Receives more underlying assets than should be possible
```

**Semantic Operations:**
- `CALLS_EXTERNAL` (calls GLP redemption)
- `TRANSFERS_VALUE_OUT` (receives underlying assets)
- `DRAINS_VALUE` (extracts $42M)

---

#### Step 10: Protocol Left with Deficit
After the attack, GMX v1 on Arbitrum was left with a **$42 million shortfall**:

- Attacker redeemed overvalued GLP
- Underlying assets were transferred out
- The accounting inconsistency made the deficit possible

---

## The Circular Dependency Chain

```
executeDecreaseOrder() called
    │
    ├─→ [ATOMIC UPDATE SHOULD BE HERE]
    │   Update position list AND global average price
    │
    ├─→ M:poslist (position removed) ✓
    │
    ├─→ [GAP - THIS IS THE VULNERABILITY]
    │
    ├─→ X:call{value:} → Attacker's callback
    │   ├─→ Read global_price (NOT YET UPDATED) ← STALE
    │   ├─→ Manipulate positions
    │   └─→ Drive global price artificially low
    │
    ├─→ [AFTER CALLBACK RETURNS]
    │
    ├─→ M:globalprice (now updates, but damaged)
    │
    └─→ AUM calculation uses contaminated price
        GLP valuation uses contaminated AUM
        Redemptions proceed at overvalued rates
```

## Why Traditional Reentrancy Defenses Failed

### `nonReentrant` on `executeDecreaseOrder()`
```solidity
function executeDecreaseOrder(...) public nonReentrant {
    // nonReentrant only prevents re-entry INTO THIS FUNCTION
}
```

**The Problem:**
- `nonReentrant` prevents the **same function** from being called recursively
- It does **NOT** prevent re-entry into **other functions** in the contract
- The attacker doesn't need to re-call `executeDecreaseOrder()` directly
- The attacker re-enters different position management functions

**Semantic Analysis:**
- `function_level_reentrancy_guard_present = true`
- `cross_function_reentrancy_guard_present = false` ← This is what was missing

### What Was Needed
A **global reentrancy lock** across all position-affecting functions:

```solidity
// BAD: Function-level lock
modifier nonReentrant {
    require(!locked_function, "...");
    locked_function = true;
    _;
    locked_function = false;
}

// GOOD: Global lock
modifier nonReentrant {
    require(!locked_global, "...");  // Shared state
    locked_global = true;
    _;
    locked_global = false;
}
```

This prevents reentrancy into **any** state-modifying function, not just the current one.

## Semantic Operation Summary

| Operation | Step | Purpose |
|-----------|------|---------|
| `CALLS_EXTERNAL` | 1,3 | Attacker calls vulnerable function and refund triggers callback |
| `WRITES_SHARED_STATE` | 2 | Position list is updated |
| `TRIGGERS_CALLBACK` | 3 | ETH refund opens reentrancy window |
| `EXECUTES_CALLBACK` | 4 | Attacker gains control mid-execution |
| `READS_SHARED_STATE` | 5 | Attacker reads stale global price |
| `REENTERS_CONTEXT` | 5 | Attacker re-enters position functions |
| `MODIFIES_CRITICAL_STATE` | 5 | Attacker manipulates positions |
| `MODIFIES_PRICE_ORACLE` | 6 | Artificial price distortion created |
| `READS_ORACLE` | 6,7 | System reads contaminated prices |
| `READS_AUM_CALCULATION` | 7 | AUM depends on stale price |
| `MODIFIES_TOKEN_VALUATION` | 8 | GLP tokens become overvalued |
| `TRANSFERS_VALUE_OUT` | 9 | $42M extracted via redemption |
| `DRAINS_VALUE` | 10 | Protocol left with deficit |

## BSKG Detection Points

**High-Confidence Signals:**
1. `state_write_after_external_call = true` + `calls_external_with_value = true` + `shared_state_variables > 1`
2. Multiple functions accessing same state without global synchronization
3. External calls to untrusted addresses (like arbitrary `_account` parameter)
4. Absence of global reentrancy guard despite cross-function state sharing

**Behavioral Signature:**
```
X:call{value:}→F:fallback→R:shared(stale)→M:state→R:oracle→M:aum→M:token
```

This signature captures: external call → callback → read stale state → modify → cascade effect
