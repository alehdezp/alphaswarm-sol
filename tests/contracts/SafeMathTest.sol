// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

// ============================================================================
// TEST CONTRACT: SafeMathTest
// Tests for lib-004-safe-math pattern detection
// ============================================================================
//
// This contract demonstrates VULNERABLE patterns that should be caught by
// lib-004-safe-math pattern. These are intentionally vulnerable for testing.
//
// Scenarios tested:
// 1. Pre-0.8.0 arithmetic without SafeMath (Scenario A)
// 2. Arithmetic affecting user balances without protection
// 3. Fee calculations with precision loss
//

// ============================================================================
// VULNERABLE: Pre-0.8.0 without SafeMath
// ============================================================================

contract VulnerablePre08NoSafeMath {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    // VULNERABLE: Scenario A - Pre-0.8.0 arithmetic without SafeMath
    // Should trigger: pre_08_arithmetic = true
    function deposit(uint256 amount) external {
        balances[msg.sender] += amount;  // Vulnerable: no overflow check
        totalSupply += amount;           // Vulnerable: accumulation
    }

    // VULNERABLE: Scenario A - User input in arithmetic
    function multiplyBalance(uint256 factor) external {
        balances[msg.sender] = balances[msg.sender] * factor;  // User can trigger overflow
    }

    // VULNERABLE: Scenario A - Large number multiplication
    // large_number_multiplication will be true (both > 10^9)
    function calculateReward(uint256 blocks) external pure returns (uint256) {
        uint256 rate = 1000000000;  // 10^9
        return rate * blocks;        // Vulnerable without SafeMath
    }

    // VULNERABLE: Scenario A - Fee calculation with precision loss
    function takeFee(uint256 amount) external {
        uint256 fee = amount * 25 / 100;     // Precision loss: divides after multiply
        balances[msg.sender] -= fee;
    }

    // VULNERABLE: Scenario A - Batch transfer overflow
    function batchTransfer(address[] calldata recipients, uint256 amount) external {
        uint256 totalAmount = 0;
        for (uint i = 0; i < recipients.length; i++) {
            totalAmount += amount;  // Can overflow without checks
        }
        require(balances[msg.sender] >= totalAmount);
        // ... transfer logic ...
    }
}

// ============================================================================
// VULNERABLE: Pre-0.8.0 with Large Number Arithmetic
// ============================================================================

contract VulnerableLargeNumberArithmetic {
    uint256 public constant RATE = 1000000000;      // 10^9 (large)
    uint256 public constant BLOCKS = 1000000000;    // 10^9 (large)

    // VULNERABLE: Scenario C - Large number multiplication
    // Should trigger: large_number_multiplication = true AND multiplication_overflow_risk = true
    function calculateTotalReward(uint256 numberOfBlocks) external pure returns (uint256) {
        return RATE * numberOfBlocks;  // 10^9 * user_input = overflow risk
    }

    // VULNERABLE: Large multiplication chain
    function complexCalculation(uint256 x, uint256 y, uint256 z) external pure returns (uint256) {
        return (x * y) * z;  // Multiple multiplications: overflow vector
    }
}

// ============================================================================
// SAFE: Pre-0.8.0 with SafeMath
// ============================================================================

import "@openzeppelin/contracts/math/SafeMath.sol";

contract SafePre08WithSafeMath {
    using SafeMath for uint256;

    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    // SAFE: Scenario A excluded - Uses SafeMath
    function deposit(uint256 amount) external {
        balances[msg.sender] = balances[msg.sender].add(amount);  // SafeMath reverts on overflow
        totalSupply = totalSupply.add(amount);
    }

    // SAFE: Scenario A excluded - Uses SafeMath
    function calculateReward(uint256 blocks) external pure returns (uint256) {
        uint256 rate = 1000000000;
        return rate.mul(blocks);  // SafeMath handles overflow
    }
}

// ============================================================================
// SAFE: Pre-0.8.0 with Small Numbers (cannot overflow)
// ============================================================================

contract SafePre08SmallNumbers {
    mapping(address => uint256) public balances;

    // SAFE: Small numbers that cannot overflow
    // amount < 2^256 / 2 is guaranteed by parameter validation
    function safeSmallDeposit(uint8 amount) external {
        require(amount < 100);
        balances[msg.sender] += amount;  // Safe: amount is bounded
    }
}

// ============================================================================
// SAFE: View/Pure Functions (no state mutation)
// ============================================================================

contract SafeViewFunctions {
    mapping(address => uint256) public balances;

    // SAFE: View function - no state changes
    function calculateFeeView(uint256 amount) external view returns (uint256) {
        return amount * 25 / 100;  // No vulnerability (pure calculation)
    }

    // SAFE: Pure function - no state changes
    function calculateFeePure(uint256 amount) external pure returns (uint256) {
        return amount * 25 / 100;  // No vulnerability (pure calculation)
    }
}

// ============================================================================
// REFERENCE: Note about Solidity 0.8.0+
// ============================================================================
//
// For Solidity 0.8.0+, patterns would need to be tested in separate files
// with `pragma solidity ^0.8.0;` to properly detect unchecked block scenarios.
//
// Example vulnerabilities in 0.8.0+:
//
// contract Vulnerable080 {
//     function unsafeUnchecked(uint256 amount) external {
//         unchecked {
//             balance[msg.sender] += amount;  // Scenario B: Unchecked + user input
//         }
//     }
//
//     function unsafeLargeMultiply(uint256 x) external {
//         unchecked {
//             return 1000000000 * x;  // Scenario B: Unchecked + large number
//         }
//     }
// }
//
// Safe patterns in 0.8.0+:
//
// contract Safe080 {
//     function safeWithoutUnchecked(uint256 amount) external {
//         balance[msg.sender] += amount;  // Safe: Native overflow check
//     }
//
//     function safeWithGuards(uint256 amount) external {
//         require(amount < type(uint256).max - balance[msg.sender]);
//         unchecked {
//             balance[msg.sender] += amount;  // Safe: Guarded
//         }
//     }
// }
