# Code Patterns: GMX V1 Reentrancy Vulnerability

## Pattern 1: Vulnerable - Refund to Untrusted Address with Non-Atomic State

This is the core vulnerability pattern from GMX v1.

### Vulnerable Code Example

```solidity
// VULNERABLE: Refund to untrusted _account parameter
// Semantic Operations: CALLS_EXTERNAL, TRANSFERS_VALUE_OUT, WRITES_SHARED_STATE, REENTRANCY_WINDOW
contract VulnerablePositionManager {
    struct Position {
        address account;
        uint256 size;
        uint256 collateral;
    }

    mapping(uint256 => Position) public positions;
    uint256 public positionCount;

    // Global state that should be updated atomically
    uint256 public globalShortSize;
    uint256 public globalAveragePrice;

    // VULNERABLE: Only guards reentrancy into this specific function
    modifier nonReentrant() {
        require(!_reentrancyLocked, "ReentrancyGuard: reentrant call");
        _reentrancyLocked = true;
        _;
        _reentrancyLocked = false;
    }
    bool private _reentrancyLocked = false;

    function executeDecreaseOrder(
        uint256 orderId,
        address payable _account,  // ← UNTRUSTED PARAMETER: can be attacker's contract
        uint256 decreaseSize
    )
        public
        nonReentrant  // ← Only protects THIS function, not cross-function reentrancy
    {
        require(orderId < positionCount, "Invalid order");
        Position storage position = positions[orderId];

        // STEP 1: Update position list
        // Semantic: WRITES_SHARED_STATE
        globalShortSize -= decreaseSize;
        position.size -= decreaseSize;

        // STEP 2: Calculate gas refund
        uint256 gasRefund = tx.gasprice * 200000;  // Example calculation

        // STEP 3: VULNERABILITY - Gap between state updates!
        // Position list is updated but globalAveragePrice is NOT yet updated

        // STEP 4: Transfer value to untrusted address
        // Semantic: TRANSFERS_VALUE_OUT, CALLS_EXTERNAL, TRIGGERS_CALLBACK
        (bool success, ) = _account.call{value: gasRefund}("");  // ← REENTRANCY WINDOW OPENS HERE
        require(success, "Refund failed");

        // At this point, attacker's callback has already executed!
        // The attacker re-entered other functions while state is inconsistent

        // STEP 5: Update global average price (NOW, too late!)
        // Semantic: WRITES_SHARED_STATE
        // But attacker has already read the stale price and manipulated state
        uint256 newAverage = calculateNewAverage(globalShortSize);
        globalAveragePrice = newAverage;  // ← Updated AFTER callback
    }

    // Another function that reads shared state
    function readPositionPrice() public view returns (uint256) {
        // Semantic: READS_SHARED_STATE, READS_ORACLE
        return globalAveragePrice;  // Attacker reads this while it's stale!
    }

    // GLP valuation depends on prices read from this contract
    function getAUM() public view returns (uint256) {
        // Semantic: READS_ORACLE, READS_AUM_CALCULATION
        // AUM calculation feeds into GLP token valuation
        return calculateAUM(globalAveragePrice);  // ← Uses potentially stale price
    }

    function calculateNewAverage(uint256 newShortSize) internal view returns (uint256) {
        // Simplified: just return some calculation
        // In real code, this would involve position history, etc.
        if (newShortSize == 0) return 0;
        return globalShortSize / 1 gwei;
    }

    function calculateAUM(uint256 price) internal view returns (uint256) {
        // AUM depends on current prices
        // If prices are stale/manipulated, AUM is wrong
        return price * 1000;  // Simplified calculation
    }
}
```

### Why This Is Vulnerable

1. **Untrusted Address Parameter**: `_account` is attacker-controlled. Attacker passes their own contract.
2. **Non-Atomic Updates**: `globalShortSize` is updated (Step 1) but `globalAveragePrice` is updated much later (Step 5).
3. **Callback Opens Reentrancy Window**: The `call{value:}` transfer gives control to the attacker's contract mid-execution.
4. **Cross-Function Reentrancy Not Guarded**: The `nonReentrant` modifier only prevents same-function reentrancy. Other functions (like `readPositionPrice()` and `getAUM()`) have no protection.
5. **Cascading State Corruption**: Attacker reads stale `globalAveragePrice`, manipulates positions, and causes `getAUM()` to return inflated values. GLP valuation becomes wrong.

### Semantic Operations Present

```
CALLS_EXTERNAL           (to _account via call{value:})
TRANSFERS_VALUE_OUT      (sends ETH as refund)
WRITES_SHARED_STATE      (position list, global size)
READS_SHARED_STATE       (in attacker's callback, reads globalAveragePrice)
MODIFIES_CRITICAL_STATE  (attacker manipulates positions)
REENTERS_CONTEXT         (callback re-enters position functions)
READS_ORACLE             (reads stale globalAveragePrice)
READS_AUM_CALCULATION    (GLP valuation reads stale AUM)
MODIFIES_TOKEN_VALUATION (GLP tokens become overvalued)
```

### BSKG Detection

```
pattern: state_write_after_external_call AND shared_state_variables > 1
  signals:
    - visibility = [public, external] ✓
    - calls_external_with_value = true ✓
    - shared_state_variables: globalShortSize, globalAveragePrice ✓
    - has_reentrancy_guard = true (BUT: function-level only)
    - has_global_reentrancy_guard = false ✗

  operation_sequence:
    - M:poslist -> X:call{value:} -> (callback executes) -> R:price(stale) -> M:aum
```

---

## Pattern 2: Safe - Atomic Updates with Global Reentrancy Guard

This is the corrected version with multiple fixes applied.

### Safe Code Example

```solidity
// SAFE: Atomic updates + global reentrancy guard
// Semantic Operations: CHECKS_PERMISSION, WRITES_SHARED_STATE, CEI pattern observed
contract SafePositionManager {
    struct Position {
        address account;
        uint256 size;
        uint256 collateral;
    }

    mapping(uint256 => Position) public positions;
    uint256 public positionCount;

    // Global state - updated atomically
    uint256 public globalShortSize;
    uint256 public globalAveragePrice;

    // SAFE: Global reentrancy guard protects ALL functions
    // Semantic: CHECKS_PERMISSION
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "ReentrancyGuard: reentrant call");
        locked = true;
        _;
        locked = false;
    }

    function executeDecreaseOrder(
        uint256 orderId,
        uint256 decreaseSize
    )
        external
        payable
        nonReentrant  // ← Global lock prevents any reentrancy
    {
        require(orderId < positionCount, "Invalid order");
        Position storage position = positions[orderId];

        // Verify caller is the account (not allowing arbitrary _account parameter)
        // Semantic: CHECKS_PERMISSION
        require(position.account == msg.sender, "Not position owner");

        // CRITICAL FIX 1: Calculate refund amount upfront
        uint256 gasRefund = tx.gasprice * 200000;
        require(msg.value >= gasRefund, "Insufficient value for refund");

        // CRITICAL FIX 2: Atomic state updates BEFORE any external calls
        // Semantic: WRITES_SHARED_STATE (both updates happen together)
        uint256 oldShortSize = globalShortSize;
        globalShortSize -= decreaseSize;

        // Update BOTH related state variables atomically
        uint256 newAverage = calculateNewAverageAtomic(oldShortSize, globalShortSize);
        globalAveragePrice = newAverage;  // ← Updated in same transaction block

        // All state is now consistent - no gap for reentrancy

        // CRITICAL FIX 3: Refund to msg.sender, not arbitrary parameter
        // Semantic: TRANSFERS_VALUE_OUT (but to trusted caller)
        (bool success, ) = msg.sender.call{value: gasRefund}("");
        require(success, "Refund failed");

        // At this point:
        // - Position list is updated
        // - Global average price is updated (in same block)
        // - Global reentrancy lock is still held
        // - Attacker cannot re-enter other functions
        // - All state is consistent
    }

    function readPositionPrice() external view returns (uint256) {
        // Semantic: READS_SHARED_STATE
        // Will always read consistent globalAveragePrice
        return globalAveragePrice;
    }

    function getAUM() external view returns (uint256) {
        // Semantic: READS_AUM_CALCULATION
        // Always uses consistent prices
        return calculateAUM(globalAveragePrice);
    }

    function calculateNewAverageAtomic(
        uint256 oldSize,
        uint256 newSize
    ) internal view returns (uint256) {
        // Calculate new average with both sizes in mind
        if (newSize == 0) return 0;
        return (globalShortSize * globalAveragePrice + newSize * 100) / newSize;
    }

    function calculateAUM(uint256 price) internal view returns (uint256) {
        // AUM calculation always uses consistent, current prices
        return price * 1000;
    }
}
```

### Why This Is Safe

1. **Trusted Refund**: Refund goes to `msg.sender` (the caller), not an arbitrary parameter.
2. **Atomic Updates**: Both `globalShortSize` and `globalAveragePrice` are updated in the same transaction block before external calls.
3. **Checks-Effects-Interactions (CEI) Pattern**:
   - Checks: Verify ownership
   - Effects: Update all state variables
   - Interactions: Send refund (external call)
4. **Global Reentrancy Guard**: The `locked` flag prevents re-entry into ANY function in the contract, not just the current one.
5. **No State Inconsistency Window**: No gap between related state updates, so attacker can't exploit inconsistencies.

### Semantic Operations Present

```
CHECKS_PERMISSION        (verify msg.sender is position owner)
WRITES_SHARED_STATE      (both global vars updated atomically)
MODIFIES_CRITICAL_STATE  (updates happen before external calls)
TRANSFERS_VALUE_OUT      (refund to trusted address)
CEI_PATTERN              (checks → effects → interactions)
```

### BSKG Detection

```
pattern: state_write_after_external_call AND shared_state_variables > 1
  signals:
    - visibility = [public, external] ✓
    - calls_external_with_value = true ✓
    - shared_state_variables: globalShortSize, globalAveragePrice ✓
    - has_reentrancy_guard = true ✓
    - has_global_reentrancy_guard = true ✓ (This is the key difference!)
    - state_updates_before_external_call = true ✓

  operation_sequence:
    - C:perm -> M:poslist -> M:price (atomic) -> X:call{value:} ✓
    - No gap between related state updates
```

This pattern is SAFE because:
- Global reentrancy guard prevents cross-function reentrancy
- Atomic updates prevent state inconsistency
- Trusted refund recipient prevents callback attacks

---

## Pattern 3: Safe - Using SafeERC20 and High-Level Abstractions

For token transfers (instead of ETH), using established libraries.

### Safe Code Example

```solidity
// SAFE: Using SafeERC20 for transfers + global guard
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract SafeTokenPositionManager is ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public token;

    struct Position {
        address account;
        uint256 size;
        uint256 collateral;
    }

    mapping(uint256 => Position) public positions;
    uint256 public globalSize;
    uint256 public globalPrice;

    function decreasePosition(
        uint256 posId,
        uint256 amount
    )
        external
        nonReentrant  // ← Uses OpenZeppelin's battle-tested global guard
    {
        require(posId < positions.length, "Invalid position");
        Position storage pos = positions[posId];
        require(pos.account == msg.sender, "Not position owner");

        // Atomic updates
        globalSize -= amount;
        globalPrice = recalculatePrice(globalSize);

        pos.size -= amount;

        // CEI: All effects before interactions
        // SafeERC20 handles the external call safely
        token.safeTransfer(msg.sender, amount);  // ← Safe transfer (guarded by nonReentrant)
    }

    function recalculatePrice(uint256 newSize) internal view returns (uint256) {
        if (newSize == 0) return 0;
        return (globalSize / newSize);
    }
}
```

### Why This Is Safe

1. **ReentrancyGuard**: OpenZeppelin's battle-tested global reentrancy guard.
2. **SafeERC20**: Wrapper that ensures safe token transfers.
3. **CEI Pattern**: All state updates before the token transfer.
4. **No Arbitrary Address**: No untrusted address parameter for refunds/transfers.

---

## Edge Cases and Variations

### Case 1: Multiple Callbacks in Same Transaction

If an attacker can trigger multiple callbacks in sequence:

```solidity
// VULNERABLE:
function vulnerableMultiCallback() external {
    // Update A
    stateA = newValue;

    // Callback 1: attacker re-enters and reads B
    externalContract.call{value: x}(data);

    // Update B (but B was already read by callback 1)
    stateB = newValue;

    // Callback 2: another re-entry
    externalContract2.call{value: y}(data);
}
```

**Fix:** Global reentrancy guard prevents all callbacks after the first one.

---

### Case 2: Attacker Uses Push vs. Pull Pattern

**Vulnerable (Push):**
```solidity
// Attacker controls when callback happens
function withdraw(address payable recipient) public {
    uint256 amount = balances[msg.sender];
    balances[msg.sender] = 0;  // ← Correct: CEI pattern
    recipient.call{value: amount}("");  // ← But attacker can pass their contract
}
```

**Safe (Pull):**
```solidity
// Attacker must pull, giving protocol control
function withdraw() public nonReentrant {
    uint256 amount = balances[msg.sender];
    balances[msg.sender] = 0;
    msg.sender.call{value: amount}("");  // ← Refund to caller, not parameter
}
```

---

## Common Mistakes When Fixing

### Mistake 1: Only Adding nonReentrant to the Vulnerable Function

```solidity
// STILL VULNERABLE
modifier nonReentrant() {
    require(!lockedFunction, "reentrant");
    lockedFunction = true;
    _;
    lockedFunction = false;
}

function executeDecreaseOrder() external nonReentrant {
    // ...
    call{value:}(_account);
}

function readPrice() external {  // ← NOT protected!
    return globalPrice;
}

// Attacker's callback calls readPrice() → no protection
```

**Fix:** Use global lock across all functions that access shared state.

### Mistake 2: Updating One State Variable But Not Another

```solidity
// STILL VULNERABLE
function decreasePosition() external nonReentrant {
    globalSize -= amount;  // Updated

    call{value:}(recipient);

    globalPrice = calculatePrice();  // ← Updated too late!
}
```

**Fix:** Update all related state variables before the external call.

### Mistake 3: Checking the Guard Only at Entry

```solidity
// STILL VULNERABLE
function decreasePosition() external {
    require(!locked, "locked");  // Check at entry

    locked = true;

    globalSize -= amount;

    // But attacker can somehow bypass locked (e.g., nested call)
    call{value:}(recipient);

    locked = false;  // Never reached if re-entry happens
}
```

**Fix:** Use try-finally or OpenZeppelin's ReentrancyGuard which uses a local variable and return guard.

---

## Summary

| Pattern | Vulnerability | Safety Mechanism | Status |
|---------|---|---|---|
| Untrusted `_account` parameter with `call{value:}` | Arbitrary callback execution | Trust only `msg.sender` | VULNERABLE |
| Non-atomic state updates with gap | Temporal inconsistency | Atomic updates before external calls | VULNERABLE |
| Function-level `nonReentrant` only | Cross-function reentrancy | Global reentrancy guard | VULNERABLE |
| State updates BEFORE external calls with global guard | N/A (CEI + Guard) | Checks-Effects-Interactions + Global Lock | SAFE |
| Using trusted recipient + ReentrancyGuard | N/A (properly defended) | OpenZeppelin patterns + trusted addresses | SAFE |
