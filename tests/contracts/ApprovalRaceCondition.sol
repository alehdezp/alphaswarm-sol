// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ApprovalRaceCondition
 * @dev Demonstrates ERC-20 approval race condition vulnerability
 *
 * Changing allowance from non-zero to non-zero value creates
 * a race condition where spender can front-run and spend both old and new amounts.
 *
 * This is a well-known ERC-20 design flaw documented in:
 * - EIP-20 known issues
 * - Multiple audit reports
 *
 * Attack scenario:
 * 1. Alice approves Bob for 100 tokens
 * 2. Alice decides to change to 50 tokens, calls approve(Bob, 50)
 * 3. Bob sees the pending transaction and front-runs it
 * 4. Bob spends 100 tokens before approve(50) executes
 * 5. approve(50) executes, Bob now has 50 more tokens to spend
 * 6. Bob steals 150 tokens instead of intended 50
 */

interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

// Standard ERC-20 with vulnerable approve
contract VulnerableERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    // VULNERABLE: Direct allowance update without checking current value
    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

// Attacker exploiting race condition
contract ApprovalRaceAttacker {
    VulnerableERC20 public token;
    address public victim;
    uint256 public firstAmount;
    uint256 public secondAmount;

    constructor(address _token, address _victim) {
        token = VulnerableERC20(_token);
        victim = _victim;
    }

    // Victim initially approved attacker for firstAmount
    // Then tries to change to secondAmount
    function frontRunApproval() public {
        // 1. Monitor mempool for victim's approve transaction changing from firstAmount to secondAmount
        // 2. Front-run with higher gas to spend firstAmount before new approval
        uint256 currentAllowance = token.allowance(victim, address(this));
        token.transferFrom(victim, address(this), currentAllowance);

        // 3. Victim's approve(secondAmount) now executes
        // 4. Attacker has new allowance of secondAmount
        // 5. Spend it again
        // Total stolen: firstAmount + secondAmount
    }

    // After victim's approve executes
    function spendSecondAllowance() public {
        uint256 newAllowance = token.allowance(victim, address(this));
        token.transferFrom(victim, address(this), newAllowance);
    }
}

// SAFE: ERC-20 with increaseAllowance/decreaseAllowance
contract SafeERC20WithIncDec {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    // Still provided for compatibility, but users warned to use increase/decrease
    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    // SAFE: Increase by delta, not set to absolute value
    function increaseAllowance(address spender, uint256 addedValue) public returns (bool) {
        allowance[msg.sender][spender] += addedValue;
        return true;
    }

    // SAFE: Decrease by delta, not set to absolute value
    function decreaseAllowance(address spender, uint256 subtractedValue) public returns (bool) {
        require(allowance[msg.sender][spender] >= subtractedValue, "Decreased below zero");
        allowance[msg.sender][spender] -= subtractedValue;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

// SAFE: Approve with expectation of current value
contract SafeERC20WithExpectedValue {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    // Original approve (kept for compatibility)
    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    // SAFE: Only updates if current allowance matches expectedCurrent
    function approveWithExpectedValue(
        address spender,
        uint256 expectedCurrent,
        uint256 newAmount
    ) public returns (bool) {
        require(
            allowance[msg.sender][spender] == expectedCurrent,
            "Current allowance mismatch"
        );
        allowance[msg.sender][spender] = newAmount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

// SAFE: Best practice - always reset to 0 first
contract SafeApprovalPattern {
    IERC20 public token;

    function safeUpdateApproval(address spender, uint256 newAmount) public {
        // Step 1: Reset to 0
        token.approve(spender, 0);

        // Step 2: Set new amount
        token.approve(spender, newAmount);

        // This prevents race condition because:
        // - If spender front-runs first approve(0), they spend old amount but then have 0
        // - If spender front-runs second approve(new), they have 0 allowance
        // - Cannot exploit both
    }
}

// VULNERABLE: Infinite approval pattern (common but dangerous)
contract InfiniteApprovalVulnerable {
    IERC20 public token;
    address public dex;

    constructor(address _token, address _dex) {
        token = IERC20(_token);
        dex = _dex;

        // PROBLEM: Infinite approval to DEX
        // If DEX is compromised or has bug, all tokens at risk
        token.approve(dex, type(uint256).max);
    }

    // User's tokens permanently at risk
}

// SAFE: Exact approval pattern
contract ExactApprovalSafe {
    IERC20 public token;
    address public dex;

    constructor(address _token, address _dex) {
        token = IERC20(_token);
        dex = _dex;
        // No infinite approval
    }

    function swap(uint256 amount) public {
        // Approve exact amount needed
        token.approve(dex, amount);

        // Perform swap

        // Revoke any remaining approval
        token.approve(dex, 0);
    }
}

// VULNERABLE: Not checking approval success
contract VulnerableApprovalCheck {
    function unsafeApprove(address token, address spender, uint256 amount) public {
        // PROBLEM: Some tokens (like USDT) don't return bool on approve
        // This will revert on those tokens
        IERC20(token).approve(spender, amount);

        // PROBLEM: Doesn't verify approval actually happened
    }
}

// SAFE: Using SafeERC20 pattern
contract SafeApprovalCheck {
    function safeApprove(address token, address spender, uint256 amount) public {
        // Check current allowance
        uint256 currentAllowance = IERC20(token).allowance(address(this), spender);

        if (currentAllowance < amount) {
            // Need to increase
            if (currentAllowance > 0) {
                // Reset to 0 first
                (bool success,) = token.call(
                    abi.encodeWithSelector(IERC20.approve.selector, spender, 0)
                );
                require(success, "Approve to 0 failed");
            }

            // Set new amount
            (bool success,) = token.call(
                abi.encodeWithSelector(IERC20.approve.selector, spender, amount)
            );
            require(success, "Approve failed");
        }

        // Verify allowance was set
        require(IERC20(token).allowance(address(this), spender) >= amount, "Allowance not set");
    }
}
