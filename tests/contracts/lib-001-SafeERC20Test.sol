// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * SafeERC20 Library Pattern Tests
 * Pattern: lib-001-safe-erc20
 *
 * Tests both VULNERABLE (direct ERC20 calls) and SAFE (SafeERC20 usage) patterns
 */

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

// ============================================================================
// VULNERABLE PATTERNS - Should be flagged by lib-001
// ============================================================================

/**
 * VULNERABLE: Direct transfer without SafeERC20
 * Pattern: uses_erc20_transfer = true, uses_safe_erc20 = false, token_return_guarded = false
 */
contract VulnerableDirectTransfer {
    function deposit(IERC20 token, uint256 amount) external {
        // VULNERABLE: Direct call, no SafeERC20 wrapper
        // Will fail with USDT (returns void, not bool)
        require(token.transfer(address(this), amount), "Transfer failed");
        // User balance accounting would happen here
    }

    function withdraw(IERC20 token, uint256 amount) external {
        // VULNERABLE: Direct call without SafeERC20
        token.transfer(msg.sender, amount);
        // No return value check
    }
}

/**
 * VULNERABLE: Direct transferFrom without SafeERC20
 * Pattern: uses_erc20_transfer_from = true, uses_safe_erc20 = false
 */
contract VulnerableDirectTransferFrom {
    function deposit(address token, uint256 amount) external {
        // VULNERABLE: Direct transferFrom call
        IERC20(token).transferFrom(msg.sender, address(this), amount);
        // No return value check - silent failure possible
    }

    function borrow(address token, address recipient, uint256 amount) external {
        // VULNERABLE: Direct transferFrom without guard
        bool success = IERC20(token).transferFrom(address(this), recipient, amount);
        // Does check return but if token returns void (USDT), this will revert
    }
}

/**
 * VULNERABLE: Direct approve without SafeERC20
 * Pattern: uses_erc20_approve = true, uses_safe_erc20 = false
 */
contract VulnerableDirectApprove {
    function approveRouter(address token, address router, uint256 amount) external {
        // VULNERABLE: Direct approve call
        IERC20(token).approve(router, amount);
        // No SafeERC20 - fails with non-standard tokens
        // Also has race condition if changing non-zero to non-zero
    }

    function setAllowance(IERC20 token, address spender, uint256 value) external {
        // VULNERABLE: Direct approve without SafeERC20
        // If changing from non-zero to non-zero, race condition exists
        require(token.approve(spender, value), "Approve failed");
    }
}

/**
 * VULNERABLE: Mixed operations without SafeERC20
 * Pattern: Multiple ERC20 calls, all unguarded
 */
contract VulnerableSwapPatternNoSafeERC20 {
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) external returns (uint256 amountOut) {
        // VULNERABLE: Input token without SafeERC20
        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);

        // Swap logic here
        amountOut = amountIn * 2; // placeholder

        // VULNERABLE: Output token without SafeERC20
        IERC20(tokenOut).transfer(msg.sender, amountOut);

        return amountOut;
    }

    function swapWithApproval(
        address tokenIn,
        address tokenOut,
        address router,
        uint256 amountIn
    ) external {
        // VULNERABLE: Multiple unguarded ERC20 calls
        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).approve(router, amountIn);
        // ... router interaction ...
        IERC20(tokenOut).transfer(msg.sender, 100); // hardcoded for test
    }
}

// ============================================================================
// SAFE PATTERNS - Should NOT be flagged by lib-001
// ============================================================================

/**
 * SAFE: Using SafeERC20 for transfers
 * Pattern: uses_safe_erc20 = true
 */
contract SafeDepositWithSafeERC20 {
    using SafeERC20 for IERC20;

    event Deposited(address indexed user, address indexed token, uint256 amount);

    function deposit(IERC20 token, uint256 amount) external {
        // SAFE: Using SafeERC20
        // Works with ALL tokens: USDT, BNB, OMG, standard ERC20
        token.safeTransferFrom(msg.sender, address(this), amount);
        // User accounting would happen here
        emit Deposited(msg.sender, address(token), amount);
    }

    function withdraw(IERC20 token, uint256 amount) external {
        // SAFE: Using SafeERC20
        token.safeTransfer(msg.sender, amount);
    }
}

/**
 * SAFE: Using SafeERC20 for approvals
 * Pattern: uses_safe_erc20 = true
 */
contract SafeApprovalWithSafeERC20 {
    using SafeERC20 for IERC20;

    function approveRouter(IERC20 token, address router, uint256 amount) external {
        // SAFE: Using SafeERC20.safeApprove
        // Handles race condition of changing non-zero to non-zero
        token.safeApprove(router, amount);
    }

    function increaseAllowance(IERC20 token, address spender, uint256 added) external {
        // SAFE: Using safeIncreaseAllowance
        token.safeIncreaseAllowance(spender, added);
    }
}

/**
 * SAFE: Complete swap with SafeERC20
 * Pattern: uses_safe_erc20 = true
 */
contract SafeSwapWithSafeERC20 {
    using SafeERC20 for IERC20;

    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256 amountOut) {
        // SAFE: Input token uses SafeERC20
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);

        // Swap logic
        amountOut = amountIn * 2; // placeholder

        // SAFE: Output token uses SafeERC20
        IERC20(tokenOut).safeTransfer(msg.sender, amountOut);

        return amountOut;
    }
}

/**
 * SAFE: Manual return value checking (alternative to SafeERC20)
 * Pattern: token_return_guarded = true
 */
contract SafeManualReturnGuard {
    function depositWithReturnCheck(address token, uint256 amount) external {
        // SAFE: Explicit return value checking via low-level call
        (bool ok, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transfer.selector, address(this), amount)
        );

        // Check both: call succeeded AND return value is true (or empty for void tokens)
        require(ok && (data.length == 0 || abi.decode(data, (bool))), "Transfer failed");
    }

    function transferFromWithCheck(
        address token,
        address from,
        address to,
        uint256 amount
    ) external {
        // SAFE: Guarded transferFrom with return value check
        (bool ok, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transferFrom.selector, from, to, amount)
        );

        require(ok && (data.length == 0 || abi.decode(data, (bool))), "TransferFrom failed");
    }
}

/**
 * SAFE: View/pure functions (no state modification risk)
 * Pattern: state_mutability = view/pure (excluded from pattern)
 */
contract SafeViewFunctions {
    function checkBalance(IERC20 token, address user) external view returns (uint256) {
        // SAFE: View function - no state modification
        // Even if using direct IERC20.balanceOf, view functions have no execution risk
        return token.balanceOf(user);
    }

    function canTransfer(IERC20 token, address from, uint256 amount) external view returns (bool) {
        // SAFE: Pure/view functions are read-only
        return token.balanceOf(from) >= amount;
    }
}

// ============================================================================
// EDGE CASES & PARTIAL PATTERNS
// ============================================================================

/**
 * EDGE CASE: SafeERC20 used for some operations but not all
 * Pattern: Mixed - some uses_safe_erc20 = true, some = false
 * Should this be flagged? Depends on which operation fails.
 */
contract PartialSafeERC20Coverage {
    using SafeERC20 for IERC20;

    function mixedTransfer(IERC20 token1, IERC20 token2, uint256 amount) external {
        // SAFE: Using SafeERC20 for token1
        token1.safeTransfer(msg.sender, amount);

        // POTENTIALLY VULNERABLE: Direct call for token2 without SafeERC20
        token2.transfer(msg.sender, amount);
    }
}

/**
 * EDGE CASE: Constructor with direct ERC20 call
 * Pattern: is_constructor = true (excluded from pattern)
 * Constructors are one-time execution, lower risk
 */
contract ConstructorDirectERC20 {
    IERC20 public token;

    constructor(IERC20 _token) {
        // SAFE (constructor): One-time setup, excluded from pattern
        _token.transfer(address(1), 1);
    }
}

/**
 * EDGE CASE: Custom wrapper that mimics SafeERC20
 * Pattern: token_return_guarded = true (manually checked)
 * Should NOT be flagged if return guard is comprehensive
 */
contract CustomTokenWrapper {
    function safeTransfer(IERC20 token, address to, uint256 amount) internal {
        // Custom wrapper that checks return value
        (bool ok, bytes memory data) = address(token).call(
            abi.encodeWithSelector(IERC20.transfer.selector, to, amount)
        );
        require(ok && (data.length == 0 || abi.decode(data, (bool))), "Transfer failed");
    }

    function deposit(IERC20 token, uint256 amount) external {
        // SAFE: Using custom wrapper
        safeTransfer(token, address(this), amount);
    }
}

/**
 * EDGE CASE: Approve with explicit zero check
 * Pattern: token_return_guarded could be true if return is explicitly checked
 */
contract ExplicitApproveCheck {
    function approveWithCheck(IERC20 token, address spender, uint256 amount) external {
        // Explicitly check return value
        bool ok = token.approve(spender, amount);
        require(ok, "Approve failed");
    }
}
