# Unsafe Downcasting - Detection

## Overview

Solidity 0.8+ checks arithmetic overflow but NOT explicit type casts. Downcasting uint256 to smaller types silently truncates high bits if value exceeds target type's max.

## Detection Signals

**Tier A:**
1. `has_explicit_downcast = true` - Function contains `uint128(value)` style casts
2. `no_bounds_check_before_cast = true` - Missing bounds validation
3. `cast_result_used_in_critical_logic = true` - Cast value affects balances/state

**Signature:** `C:downcast{no_check}->W:balance`

## Vulnerable Pattern

```solidity
// VULNERABLE: No check before downcast
function deposit(uint256 amount) external {
    // If amount > type(uint128).max, truncation occurs
    uint128 amount128 = uint128(amount);  // UNSAFE
    balances[msg.sender] = amount128;     // WRONG VALUE STORED
}

// Example: amount = 2^128 + 100
// amount128 = 100 (high bits lost!)
```

## Safe Pattern 1: SafeCast Library

```solidity
import "@openzeppelin/contracts/utils/math/SafeCast.sol";

function deposit(uint256 amount) external {
    uint128 amount128 = SafeCast.toUint128(amount);  // Reverts if overflow
    balances[msg.sender] = amount128;
}
```

## Safe Pattern 2: Manual Check

```solidity
function deposit(uint256 amount) external {
    require(amount <= type(uint128).max, "Value too large");
    uint128 amount128 = uint128(amount);  // SAFE
    balances[msg.sender] = amount128;
}
```

## Detection

Search for: `uint{N}(` where N < 256, check if bounds validated.
