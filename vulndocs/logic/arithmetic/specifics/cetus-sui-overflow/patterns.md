# Patterns: Cetus Protocol SUI Overflow

This document provides vulnerable and safe code patterns for the arithmetic overflow vulnerability.

## Vulnerable Pattern 1: Direct Unchecked Multiplication

### Vulnerable Code
```solidity
pragma solidity 0.7.6;

contract VulnerablePosition {
    mapping(address => uint256) public positions;

    uint256 constant POSITION_MULTIPLIER = 10**18;

    // VULNERABLE: No bounds checking before multiplication
    function setPosition(uint256 amount) public {
        // Attacker could supply large amounts causing overflow
        uint256 position = amount * POSITION_MULTIPLIER;
        positions[msg.sender] = position;
    }
}
```

**Why it's vulnerable:**
- User input `amount` is not validated before multiplication
- If `amount > type(uint256).max / POSITION_MULTIPLIER`, overflow occurs
- The overflowed value is written to critical state
- No error is thrown (in Solidity 0.7.x) - overflow silently wraps

**Attack example:**
```
amount = 2^256 / 10^18 + 1
position = amount * 10^18 = overflow = small value
Attacker gets large position with tiny input
```

### Safe Code - Using SafeMath
```solidity
pragma solidity 0.7.6;

import "@openzeppelin/contracts/math/SafeMath.sol";

contract SafePosition {
    using SafeMath for uint256;

    mapping(address => uint256) public positions;

    uint256 constant POSITION_MULTIPLIER = 10**18;

    // SAFE: Uses SafeMath for overflow protection
    function setPosition(uint256 amount) public {
        // SafeMath.mul reverts if overflow would occur
        uint256 position = amount.mul(POSITION_MULTIPLIER);
        positions[msg.sender] = position;
    }
}
```

**Why it's safe:**
- SafeMath library provides overflow-checked multiplication
- Operation reverts with error if overflow would occur
- No silent wrapping or data corruption

### Safe Code - Using Solidity 0.8.0+
```solidity
pragma solidity 0.8.0;

contract SafePosition {
    mapping(address => uint256) public positions;

    uint256 constant POSITION_MULTIPLIER = 10**18;

    // SAFE: Solidity 0.8.0+ has built-in overflow checks
    function setPosition(uint256 amount) public {
        // Overflow automatically reverts in 0.8.0+
        uint256 position = amount * POSITION_MULTIPLIER;
        positions[msg.sender] = position;
    }
}
```

**Why it's safe:**
- Solidity 0.8.0 and later have checked arithmetic by default
- All arithmetic operations revert on overflow/underflow
- No need for SafeMath library (though it's still safe to use)

---

## Vulnerable Pattern 2: Unchecked Division in Liquidity Calculation

### Vulnerable Code
```solidity
pragma solidity 0.7.6;

contract VulnerableLiquidity {
    mapping(address => uint256) public liquidityPositions;

    uint256 public totalLiquidity;

    // VULNERABLE: Division without precision/bounds checks
    function addLiquidity(uint256 amount) public {
        // If attacker manipulates state.totalLiquidity or provides
        // crafted amounts, division can lose precision or overflow
        uint256 userPortion = totalLiquidity / amount;
        liquidityPositions[msg.sender] = userPortion;
    }
}
```

**Why it's vulnerable:**
- No validation that `amount > 0` (would divide by zero or revert)
- `userPortion` could be very small if `totalLiquidity < amount`
- Later multiplication with `userPortion` could cause state inconsistency
- No maximum limits on `amount`

### Safe Code
```solidity
pragma solidity 0.8.0;

contract SafeLiquidity {
    mapping(address => uint256) public liquidityPositions;

    uint256 public totalLiquidity;

    // Constants for maximum values
    uint256 constant MAX_LIQUIDITY = 10**18;  // Adjust based on protocol

    // SAFE: Comprehensive validation before division
    function addLiquidity(uint256 amount) public {
        // Validate input
        require(amount > 0, "Amount must be positive");
        require(amount <= MAX_LIQUIDITY, "Amount exceeds maximum");

        // Prevent division errors
        require(totalLiquidity > 0, "No liquidity available");

        // Safe division with precision protection
        // Using FixedPoint library would be even better
        uint256 userPortion = (totalLiquidity * 10**18) / amount;

        require(userPortion > 0, "Portion too small");
        require(userPortion <= type(uint256).max, "Calculation overflow");

        liquidityPositions[msg.sender] = userPortion;
    }
}
```

---

## Vulnerable Pattern 3: Chained Arithmetic Without Bounds

### Vulnerable Code
```solidity
pragma solidity 0.7.6;

contract VulnerableSwap {
    // VULNERABLE: Multiple unchecked operations
    function swapTokens(
        uint256 inputAmount,
        uint256 swapRate,
        uint256 feePercentage
    ) public returns (uint256 outputAmount) {
        // Step 1: Calculate raw swap output (unchecked)
        uint256 rawOutput = inputAmount * swapRate;

        // Step 2: Apply fee (second unchecked multiplication)
        uint256 feeAmount = rawOutput * feePercentage / 100;

        // Step 3: Calculate final output (underflow or precision loss)
        outputAmount = rawOutput - feeAmount;

        return outputAmount;
    }
}
```

**Why it's vulnerable:**
- Three arithmetic operations without bounds validation
- `inputAmount * swapRate` could overflow
- `rawOutput * feePercentage` could overflow
- Division by 100 causes precision loss
- Accumulated errors result in incorrect output

### Safe Code
```solidity
pragma solidity 0.8.0;

import "@openzeppelin/contracts/math/Math.sol";

contract SafeSwap {
    // Constants defining safe limits
    uint256 constant MAX_INPUT = 10**18;
    uint256 constant MAX_RATE = 10**18;
    uint256 constant MAX_FEE_PERCENTAGE = 10000;  // 100% = 10000

    // SAFE: Validated, step-by-step calculation
    function swapTokens(
        uint256 inputAmount,
        uint256 swapRate,
        uint256 feePercentage
    ) public returns (uint256 outputAmount) {
        // Validate all inputs
        require(inputAmount > 0 && inputAmount <= MAX_INPUT, "Invalid input amount");
        require(swapRate > 0 && swapRate <= MAX_RATE, "Invalid swap rate");
        require(feePercentage <= MAX_FEE_PERCENTAGE, "Fee percentage too high");

        // Step 1: Check for overflow before multiplication
        require(inputAmount <= type(uint256).max / swapRate, "Input * Rate overflow");
        uint256 rawOutput = inputAmount * swapRate;

        // Step 2: Calculate fee with precision
        require(rawOutput <= type(uint256).max / MAX_FEE_PERCENTAGE, "Fee calculation overflow");
        uint256 feeAmount = (rawOutput * feePercentage) / MAX_FEE_PERCENTAGE;

        // Step 3: Calculate final output
        require(feeAmount <= rawOutput, "Fee exceeds output");
        outputAmount = rawOutput - feeAmount;

        require(outputAmount > 0, "Output amount is zero");

        return outputAmount;
    }
}
```

---

## Vulnerable Pattern 4: Position Size Calculation (Cetus-Specific)

### Vulnerable Code
```solidity
pragma solidity 0.7.6;

contract VulnerablePositionManager {
    struct Position {
        uint256 size;
        uint256 collateral;
    }

    mapping(address => Position) public positions;

    uint256 constant POSITION_LEVERAGE = 10;  // 10x leverage

    // VULNERABLE: Like Cetus - unchecked position size calculation
    function openPosition(uint256 collateralAmount) public {
        // Attacker supplies large collateralAmount
        // Multiplication overflows silently
        uint256 positionSize = collateralAmount * POSITION_LEVERAGE;

        positions[msg.sender] = Position({
            size: positionSize,
            collateral: collateralAmount
        });
    }
}
```

**Why it's vulnerable (like Cetus):**
- Position size = collateral * leverage (unchecked)
- Large collateral amounts cause overflow
- Overflow results in small position size
- Attacker can later exploit this position for profit

### Safe Code
```solidity
pragma solidity 0.8.0;

contract SafePositionManager {
    struct Position {
        uint256 size;
        uint256 collateral;
    }

    mapping(address => Position) public positions;

    uint256 constant POSITION_LEVERAGE = 10;
    uint256 constant MAX_COLLATERAL = 10**18;  // 1 token unit
    uint256 constant MAX_POSITION_SIZE = 10**19;  // 10 token units

    // SAFE: Comprehensive validation like proper protocols
    function openPosition(uint256 collateralAmount) public {
        // Validate collateral amount
        require(collateralAmount > 0, "Collateral must be positive");
        require(collateralAmount <= MAX_COLLATERAL, "Collateral too large");

        // Prevent overflow in position size calculation
        require(
            collateralAmount <= type(uint256).max / POSITION_LEVERAGE,
            "Collateral would cause position overflow"
        );

        uint256 positionSize = collateralAmount * POSITION_LEVERAGE;

        // Verify position size is within protocol limits
        require(positionSize <= MAX_POSITION_SIZE, "Position exceeds maximum");

        // Verify invariant: position size >= collateral
        require(positionSize >= collateralAmount, "Invalid position size");

        positions[msg.sender] = Position({
            size: positionSize,
            collateral: collateralAmount
        });
    }
}
```

---

## Edge Cases and Variations

### Edge Case 1: Boundary Values
```solidity
// Test these specific values for overflow vulnerability:
uint256 testValues[] = [
    2^256 - 1,                      // Max uint256
    type(uint256).max,              // Same as above
    (2^256 - 1) / MULTIPLIER,       // Boundary
    (2^256 - 1) / MULTIPLIER + 1,   // One past boundary (overflow)
    0,                              // Zero
    1,                              // Minimal value
];
```

### Edge Case 2: Division Precision Loss
```solidity
// Division loses precision:
uint256 a = 10;
uint256 b = 3;
uint256 result = a / b;  // Result = 3, not 3.333...
uint256 loss = (a * 100) / b;  // Use intermediate multiplication to preserve precision
```

### Edge Case 3: Rounding Direction
```solidity
// Different rounding impacts positions:
// Floor division: 10 / 3 = 3 (loses 0.333...)
// Ceiling division: 10 / 3 = 4 (gains to overcompensate)

// VULNERABLE: Always floors, attacker exploits this
uint256 userShare = totalRewards / numUsers;

// SAFE: Explicit rounding control
uint256 userShare = (totalRewards + numUsers - 1) / numUsers;  // Ceiling
```

---

## Testing Recommendations

1. **Unit Test: Boundary Values**
   ```solidity
   function test_MaxInputMultiplication() public {
       uint256 maxInput = type(uint256).max / MULTIPLIER;
       // Should succeed
       setPosition(maxInput);

       // Should revert
       vm.expectRevert();
       setPosition(maxInput + 1);
   }
   ```

2. **Fuzz Testing**
   - Use Echidna or Foundry fuzzing
   - Test all arithmetic operations with random inputs
   - Check for invariant violations

3. **Integration Testing**
   - Multi-step operations that accumulate precision loss
   - Verify protocol invariants after each operation

4. **Property Testing**
   - Position size should always be >= collateral
   - Total tracked amounts should match actual amounts
   - No state inconsistencies after operations
