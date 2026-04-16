// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ============================================================================
// TEST CONTRACT: SafeMathTest080
// Tests for lib-004-safe-math pattern detection with unchecked blocks (0.8.0+)
// ============================================================================
//
// This contract demonstrates VULNERABLE unchecked arithmetic patterns
// that should be caught by lib-004-safe-math Scenario B.
//

// ============================================================================
// VULNERABLE: Solidity 0.8.0+ with unchecked arithmetic
// ============================================================================

contract VulnerableUnchecked080 {
    mapping(address => uint256) public balances;
    mapping(address => uint256) public shares;
    uint256 public totalSupply;

    // VULNERABLE: Scenario B - Unchecked arithmetic with user input
    // Should trigger: has_unchecked_block = true AND unchecked_operand_from_user = true
    function depositUnchecked(uint256 amount) external {
        unchecked {
            balances[msg.sender] += amount;  // User input in unchecked + writes balance state
            totalSupply += amount;
        }
    }

    // VULNERABLE: Scenario B - Unchecked affects balance state
    function mintSharesUnchecked(uint256 amount) external {
        unchecked {
            shares[msg.sender] += amount;  // Affects shares state
        }
    }

    // VULNERABLE: Scenario B - Fee calculation in unchecked
    function takeFeeUnchecked(uint256 amount) external {
        unchecked {
            uint256 fee = amount * 25 / 100;  // Precision loss in unchecked
            balances[msg.sender] -= fee;
        }
    }

    // VULNERABLE: Scenario B - Complex arithmetic in unchecked with user input
    function complexCalculationUnchecked(uint256 x, uint256 y) external returns (uint256) {
        uint256 result;
        unchecked {
            result = x * y;  // User input (x, y) in unchecked arithmetic
        }
        balances[msg.sender] = result;
        return result;
    }

    // VULNERABLE: Scenario B - Accumulation in unchecked loop
    function batchDepositUnchecked(uint256[] calldata amounts) external {
        uint256 total = 0;
        unchecked {
            for (uint i = 0; i < amounts.length; i++) {
                total += amounts[i];  // User input in unchecked accumulation
            }
        }
        balances[msg.sender] += total;
    }

    // VULNERABLE: Scenario B - Large number multiplication in unchecked
    function rewardCalculationUnchecked(uint256 blocks) external pure returns (uint256) {
        unchecked {
            return 1000000000 * blocks;  // 10^9 * user_input in unchecked
        }
    }

    // VULNERABLE: Scenario B - Nested unchecked with balance effects
    function nestedUnchecked(uint256 x, uint256 y) external {
        uint256 result;
        unchecked {
            result = x + y;  // User input in unchecked
            balances[msg.sender] += result;  // Affects balance state
        }
    }
}

// ============================================================================
// SAFE: Solidity 0.8.0+ without unchecked
// ============================================================================

contract SafeNativeOverflowCheck {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    // SAFE: Uses native overflow checks (not in unchecked)
    function deposit(uint256 amount) external {
        balances[msg.sender] += amount;  // Native overflow check in 0.8.0+
        totalSupply += amount;
    }

    // SAFE: Simple arithmetic without unchecked
    function calculateFee(uint256 amount) external pure returns (uint256) {
        return amount * 25 / 100;  // Native overflow protection
    }
}

// ============================================================================
// SAFE: Solidity 0.8.0+ with guarded unchecked
// ============================================================================

contract SafeGuardedUnchecked {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    // SAFE: Unchecked with pre-validation
    function depositGuarded(uint256 amount) external {
        require(amount > 0 && amount < type(uint256).max - balances[msg.sender]);
        unchecked {
            balances[msg.sender] += amount;  // Guarded by require above
        }
    }

    // SAFE: Unchecked but view function (no state change)
    function calculateUnchecked(uint256 x, uint256 y) external pure returns (uint256) {
        uint256 result;
        unchecked {
            result = x * y;  // No state mutation, just calculation
        }
        return result;
    }

    // SAFE: Unchecked with constant values only (no user input)
    function constantCalculation() external pure returns (uint256) {
        unchecked {
            return 100 * 50;  // Only constants, no user input
        }
    }

    // SAFE: Unchecked in constructor (lower risk)
    constructor() {
        unchecked {
            totalSupply = 1000000000 + 500000000;  // Initialization
        }
    }
}

// ============================================================================
// SAFE: Using SafeERC20-like patterns
// ============================================================================

contract SafeWithSafeERC20 {
    // This would normally import OpenZeppelin SafeERC20
    // For testing purposes, we just show the pattern

    mapping(address => uint256) public balances;

    // SAFE: Using checked ERC20 transfer
    function depositSafeERC20(uint256 amount) external {
        // In real code: token.safeTransferFrom(msg.sender, address(this), amount);
        // SafeERC20 handles overflow checks
        balances[msg.sender] += amount;
    }
}

// ============================================================================
// EDGE CASES
// ============================================================================

contract EdgeCases {
    // VULNERABLE: Unchecked on constants looks safe but matters if values are configurable
    function configuredMultiply(uint256 rate, uint256 blocks) external pure returns (uint256) {
        unchecked {
            return rate * blocks;  // User input in unchecked
        }
    }

    // VULNERABLE: Unchecked in fallback that affects state
    receive() external payable {
        unchecked {
            // If this contract tracked Ether, unchecked would be vulnerable here
        }
    }

    // SAFE: Unchecked in callback (no user balance effect)
    function safeCallback(uint256 data) external {
        unchecked {
            uint256 temp = data * 2;  // Temporary calculation, not stored to state
        }
    }
}
