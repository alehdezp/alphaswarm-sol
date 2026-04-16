// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

/**
 * @title DeadlineProtectionTest
 * @notice Comprehensive test contract for mev-002: Missing Deadline Protection pattern
 * @dev Tests BOTH variants:
 *      1. Missing deadline parameter entirely (no expiration timestamp)
 *      2. Deadline parameter exists but is NOT enforced (no require check)
 *
 * Test Coverage:
 * - TRUE POSITIVES: Functions vulnerable to stale transaction execution
 * - TRUE NEGATIVES: Functions with proper deadline enforcement
 * - EDGE CASES: Internal/view functions, alternative time mechanisms
 * - VARIATIONS: Different parameter names (deadline, expiry, expiration)
 */

// =============================================================================
// TRUE POSITIVES - VARIANT 1: No Deadline Parameter
// =============================================================================

contract VulnerableNoDeadlineParameter {
    /**
     * TP1: Classic swap without any deadline parameter.
     * Vulnerable to stale transaction execution during network congestion.
     */
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256) {
        // ❌ No deadline parameter - can execute at ANY time
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TP2: exactInput naming (Uniswap V3 style) without deadline.
     */
    function exactInput(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256) {
        // ❌ No deadline - stale execution risk
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TP3: sell naming without deadline.
     */
    function sell(
        address token,
        uint256 amount,
        uint256 minReceived
    ) external returns (uint256) {
        // ❌ No deadline protection
        uint256 received = _performSwap(token, address(0), amount);
        require(received >= minReceived, "Slippage");
        return received;
    }

    /**
     * TP4: buy naming without deadline.
     */
    function buy(
        address token,
        uint256 amount,
        uint256 maxPaid
    ) external returns (uint256) {
        // ❌ No deadline protection
        uint256 paid = _performSwap(address(0), token, amount);
        require(paid <= maxPaid, "Slippage");
        return paid;
    }

    /**
     * TP5: swapExactTokensForTokens (Uniswap V2 style) without deadline.
     */
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 minAmountOut,
        address[] calldata path
    ) external returns (uint256) {
        // ❌ Has slippage protection but NO deadline
        uint256 amountOut = _performMultiHopSwap(path, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TP6: Multi-hop swap without deadline.
     */
    function swapMultiHop(
        address[] calldata path,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256) {
        // ❌ No deadline - vulnerable to stale execution
        uint256 amountOut = _performMultiHopSwap(path, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TP7: Swap with slippage protection but NO deadline.
     * Has good slippage protection but missing deadline.
     */
    function swapWithSlippage(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256) {
        // ✅ Has slippage protection
        // ❌ But NO deadline protection
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage too high");
        return amountOut;
    }

    function _performSwap(address, address, uint256) internal pure returns (uint256) {
        return 100;
    }

    function _performMultiHopSwap(address[] calldata, uint256) internal pure returns (uint256) {
        return 100;
    }
}

// =============================================================================
// TRUE POSITIVES - VARIANT 2: Unenforced Deadline Parameter
// =============================================================================

contract VulnerableUnenforcedDeadline {
    /**
     * TP8: Deadline parameter exists but is NEVER checked.
     * CRITICAL: False sense of security - users think they have protection.
     */
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline  // ✓ Parameter exists
    ) external returns (uint256) {
        // ❌ Deadline is NEVER checked!
        // Users and frontends think they have protection but they don't
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TP9: Deadline parameter only used in event, NOT validated.
     */
    function swapWithEvent(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");

        // ❌ Deadline only in event, not validated
        emit SwapExecuted(msg.sender, tokenIn, tokenOut, amountIn, amountOut, deadline);
        return amountOut;
    }

    /**
     * TP10: Deadline parameter only returned, never validated.
     */
    function exactInputSingle(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256 amountOut, uint256 usedDeadline) {
        amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");

        // ❌ Deadline returned but never validated
        usedDeadline = deadline;
    }

    /**
     * TP11: Deadline checked AFTER swap execution (too late).
     */
    function swapDeadlineCheckedAfter(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");

        // ❌ Checking AFTER swap wastes gas and doesn't prevent stale execution
        require(block.timestamp <= deadline, "Expired");
        return amountOut;
    }

    /**
     * TP12: Deadline with TODO comment but not implemented.
     */
    function swapWithTODO(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        // TODO: Add deadline check
        // ❌ Comment mentions it but doesn't implement it
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TP13: swapExactTokensForTokens with deadline parameter but no check.
     */
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 minAmountOut,
        address[] calldata path,
        address to,
        uint256 deadline  // ✓ Parameter exists
    ) external returns (uint256) {
        // ❌ Deadline parameter NOT enforced
        uint256 amountOut = _performMultiHopSwap(path, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TP14: Deadline used in calculation but not validated.
     */
    function swapWithDeadlineInCalc(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        // ❌ Deadline used in some calculation but never validated
        uint256 seed = uint256(keccak256(abi.encodePacked(deadline, amountIn)));
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn + (seed % 10));
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    event SwapExecuted(address indexed user, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut, uint256 deadline);

    function _performSwap(address, address, uint256) internal pure returns (uint256) {
        return 100;
    }

    function _performMultiHopSwap(address[] calldata, uint256) internal pure returns (uint256) {
        return 100;
    }
}

// =============================================================================
// TRUE NEGATIVES: Safe Implementations with Deadline Enforcement
// =============================================================================

contract SafeWithDeadlineProtection {
    /**
     * TN1: Standard safe implementation with deadline enforcement.
     * Industry-standard pattern used by Uniswap, SushiSwap, etc.
     */
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        // ✅ Deadline checked BEFORE swap execution
        require(block.timestamp <= deadline, "Transaction expired");

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TN2: Comprehensive MEV protection (deadline + slippage).
     */
    function swapWithComprehensiveProtection(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        // ✅ Deadline prevents stale execution
        require(block.timestamp <= deadline, "Expired");

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);

        // ✅ Slippage prevents sandwich attacks
        require(amountOut >= minAmountOut, "Slippage too high");
        return amountOut;
    }

    /**
     * TN3: exactInputSingle with proper deadline enforcement.
     */
    function exactInputSingle(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        // ✅ Enforced deadline
        require(block.timestamp <= deadline, "Transaction expired");

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TN4: swapExactTokensForTokens with deadline enforcement.
     * Uniswap V2 style with proper protection.
     */
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 minAmountOut,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256) {
        // ✅ Standard Uniswap V2 deadline check
        require(block.timestamp <= deadline, "UniswapV2Router: EXPIRED");

        uint256 amountOut = _performMultiHopSwap(path, amountIn);
        require(amountOut >= minAmountOut, "UniswapV2Router: INSUFFICIENT_OUTPUT_AMOUNT");
        return amountOut;
    }

    /**
     * TN5: Alternative deadline comparison (deadline >= block.timestamp).
     * Mathematically equivalent to block.timestamp <= deadline.
     */
    function swapAlternativeComparison(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        // ✅ Alternative but valid comparison
        require(deadline >= block.timestamp, "Expired");

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TN6: Custom error for deadline expiration.
     */
    function swapWithCustomError(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        // ✅ Custom error but still enforced
        if (block.timestamp > deadline) {
            revert TransactionExpired(deadline, block.timestamp);
        }

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * TN7: Bounded deadline (with maximum duration check).
     */
    function swapWithBoundedDeadline(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        // ✅ Enforce deadline in future
        require(block.timestamp <= deadline, "Expired");

        // ✅ Additional safety: prevent excessively long deadlines
        require(deadline <= block.timestamp + 1 hours, "Deadline too far");

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    error TransactionExpired(uint256 deadline, uint256 currentTime);

    function _performSwap(address, address, uint256) internal pure returns (uint256) {
        return 100;
    }

    function _performMultiHopSwap(address[] calldata, uint256) internal pure returns (uint256) {
        return 100;
    }
}

// =============================================================================
// EDGE CASES
// =============================================================================

contract EdgeCases {
    /**
     * EDGE1: Internal function without deadline (SAFE - not externally callable).
     * Internal functions inherit deadline protection from their callers.
     */
    function _swapInternal(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) internal pure returns (uint256) {
        // ✓ Internal - protected by caller's deadline check
        return 100;
    }

    /**
     * EDGE2: View function (SAFE - read-only, no execution risk).
     */
    function calculateSwapOutput(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) external pure returns (uint256) {
        // ✓ View function - no state changes, no stale execution risk
        return amountIn * 99 / 100;
    }

    /**
     * EDGE3: Pure function (SAFE - no state access).
     */
    function computeSwapRatio(
        uint256 reserveIn,
        uint256 reserveOut,
        uint256 amountIn
    ) external pure returns (uint256) {
        // ✓ Pure function - no state, no execution risk
        return amountIn * reserveOut / reserveIn;
    }

    /**
     * EDGE4: Swap that delegates to router with deadline.
     * Router enforces deadline, so this function is SAFE.
     */
    function swapViaRouter(
        address router,
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) external returns (uint256) {
        // ✓ Delegates to trusted router that enforces deadline
        bytes memory data = abi.encodeWithSignature(
            "swap(address,address,uint256,uint256,uint256)",
            tokenIn, tokenOut, amountIn, minAmountOut, deadline
        );
        (bool success, bytes memory result) = router.call(data);
        require(success, "Router call failed");
        return abi.decode(result, (uint256));
    }

    /**
     * EDGE5: Block number expiration (alternative time mechanism).
     * Less reliable than timestamp but still provides some protection.
     */
    function swapWithBlockExpiration(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 expiryBlock
    ) external returns (uint256) {
        // ⚠️ Block number expiration - less standard than timestamp
        // Pattern should still flag this as not using standard deadline
        require(block.number <= expiryBlock, "Block expired");

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * EDGE6: Reentrancy guard (different vulnerability mitigation).
     * Has reentrancy protection but NO deadline protection.
     */
    function swapWithReentrancyGuard(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256) {
        // ❌ Reentrancy guard is NOT deadline protection
        // Should be flagged as missing deadline
        require(!locked, "Reentrancy");
        locked = true;

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");

        locked = false;
        return amountOut;
    }

    bool private locked;

    function _performSwap(address, address, uint256) internal pure returns (uint256) {
        return 100;
    }
}

// =============================================================================
// VARIATION TESTING: Different Parameter Naming
// =============================================================================

contract NamingVariations {
    /**
     * VAR1: 'expiry' parameter name (vulnerable - not enforced).
     */
    function swapWithExpiry(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 expiry  // Alternative name: expiry
    ) external returns (uint256) {
        // ❌ expiry parameter NOT enforced
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * VAR2: 'expiry' parameter WITH enforcement (SAFE).
     */
    function swapWithExpirySafe(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 expiry
    ) external returns (uint256) {
        // ✅ expiry enforced
        require(block.timestamp <= expiry, "Transaction expired");

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * VAR3: 'expiration' parameter (vulnerable - not enforced).
     */
    function swapWithExpiration(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 expiration
    ) external returns (uint256) {
        // ❌ expiration parameter NOT enforced
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * VAR4: 'expiration' parameter WITH enforcement (SAFE).
     */
    function swapWithExpirationSafe(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 expiration
    ) external returns (uint256) {
        // ✅ expiration enforced
        require(block.timestamp <= expiration, "Expired");

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * VAR5: 'validUntil' parameter (vulnerable - not enforced).
     */
    function swapWithValidUntil(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 validUntil
    ) external returns (uint256) {
        // ❌ validUntil parameter NOT enforced
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    /**
     * VAR6: 'validUntil' parameter WITH enforcement (SAFE).
     */
    function swapWithValidUntilSafe(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 validUntil
    ) external returns (uint256) {
        // ✅ validUntil enforced
        require(block.timestamp <= validUntil, "No longer valid");

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        require(amountOut >= minAmountOut, "Slippage");
        return amountOut;
    }

    function _performSwap(address, address, uint256) internal pure returns (uint256) {
        return 100;
    }
}

// =============================================================================
// REAL-WORLD PATTERNS: Based on Actual DEX Implementations
// =============================================================================

contract RealWorldPatterns {
    /**
     * REAL1: Uniswap V2 style WITHOUT deadline (vulnerable).
     */
    function swapExactTokensForTokensUniV2Vulnerable(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to
    ) external returns (uint256[] memory amounts) {
        // ❌ Missing deadline parameter entirely
        // Real Uniswap V2 has deadline as 5th parameter
        amounts = new uint256[](path.length);
        amounts[0] = amountIn;
        amounts[path.length - 1] = amountOutMin + 10;
        return amounts;
    }

    /**
     * REAL2: Uniswap V2 style WITH deadline (SAFE).
     */
    function swapExactTokensForTokensUniV2Safe(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts) {
        // ✅ Standard Uniswap V2 Router implementation
        require(block.timestamp <= deadline, "UniswapV2Router: EXPIRED");

        amounts = new uint256[](path.length);
        amounts[0] = amountIn;
        amounts[path.length - 1] = amountOutMin + 10;
        return amounts;
    }

    /**
     * REAL3: SushiSwap style with deadline parameter but NO check (vulnerable).
     */
    function swapExactTokensForTokensSushiVulnerable(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts) {
        // ❌ Has deadline parameter (matches Uniswap signature) but doesn't check it
        // False sense of security - users expect protection
        amounts = new uint256[](path.length);
        amounts[0] = amountIn;
        amounts[path.length - 1] = amountOutMin + 10;
        return amounts;
    }

    /**
     * REAL4: 1inch aggregator style WITH deadline enforcement (SAFE).
     */
    function swap1inch(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minReturn,
        uint256 deadline
    ) external returns (uint256 returnAmount) {
        // ✅ 1inch enforces deadline
        require(block.timestamp <= deadline, "1inch: deadline expired");

        returnAmount = amountIn * 99 / 100;
        require(returnAmount >= minReturn, "1inch: insufficient return");
        return returnAmount;
    }

    /**
     * REAL5: Curve Finance style WITHOUT deadline (vulnerable).
     * Curve historically had some pools without deadline protection.
     */
    function exchange(
        int128 i,
        int128 j,
        uint256 dx,
        uint256 min_dy
    ) external returns (uint256) {
        // ❌ Curve exchange without deadline (some pools had this issue)
        uint256 dy = dx * 99 / 100;
        require(dy >= min_dy, "Slippage");
        return dy;
    }

    /**
     * REAL6: Curve Finance style WITH deadline (SAFE).
     */
    function exchange(
        int128 i,
        int128 j,
        uint256 dx,
        uint256 min_dy,
        uint256 deadline
    ) external returns (uint256) {
        // ✅ Improved Curve with deadline
        require(block.timestamp <= deadline, "Curve: deadline expired");

        uint256 dy = dx * 99 / 100;
        require(dy >= min_dy, "Slippage");
        return dy;
    }
}
