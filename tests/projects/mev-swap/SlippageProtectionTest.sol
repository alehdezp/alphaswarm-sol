// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

// =============================================================================
// SLIPPAGE PROTECTION TEST CONTRACT - mev-001 Pattern Testing
// =============================================================================
//
// This contract tests comprehensive slippage protection detection:
// 1. TRUE POSITIVES: Swap functions WITHOUT slippage protection
//    - No slippage parameter at all
//    - Slippage parameter exists but NOT enforced
//
// 2. TRUE NEGATIVES: Safe swap implementations
//    - Slippage parameter AND enforcement (require checks)
//
// 3. EDGE CASES:
//    - Internal swap helpers (not externally callable)
//    - View/pure functions (read-only)
//    - Alternative protection mechanisms
//
// 4. VARIATION TESTING:
//    - Different parameter naming conventions
//    - Different swap function patterns
//    - Different enforcement styles
// =============================================================================

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);
}

// =============================================================================
// TRUE POSITIVES - VARIANT 1: No Slippage Parameter
// =============================================================================

contract VulnerableNoSlippageParameter {
    IERC20 public tokenIn;
    IERC20 public tokenOut;

    // TP1: Classic swap without any slippage parameter
    function swap(
        address _tokenIn,
        address _tokenOut,
        uint256 amountIn
    ) external returns (uint256) {
        IERC20(_tokenIn).transferFrom(msg.sender, address(this), amountIn);
        uint256 amountOut = _performSwap(_tokenIn, _tokenOut, amountIn);
        IERC20(_tokenOut).transfer(msg.sender, amountOut);
        return amountOut;
    }

    // TP2: exactInput naming (Uniswap V3 style) without slippage
    function exactInput(
        address tokenA,
        address tokenB,
        uint256 amount
    ) external returns (uint256) {
        uint256 output = _performSwap(tokenA, tokenB, amount);
        return output;
    }

    // TP3: sell naming without slippage
    function sell(
        address asset,
        uint256 sellAmount
    ) public returns (uint256) {
        return _performSwap(asset, address(tokenOut), sellAmount);
    }

    // TP4: buy naming without slippage
    function buy(
        address asset,
        uint256 buyAmount
    ) external returns (uint256) {
        return _performSwap(address(tokenIn), asset, buyAmount);
    }

    // TP5: trade naming without slippage
    function trade(
        address from,
        address to,
        uint256 amount
    ) external returns (uint256) {
        return _performSwap(from, to, amount);
    }

    // TP6: swapExactTokensForTokens without minAmountOut
    function swapExactTokensForTokens(
        uint256 amountIn,
        address[] calldata path
    ) external returns (uint256[] memory) {
        uint256[] memory amounts = new uint256[](path.length);
        amounts[0] = amountIn;

        for (uint i = 0; i < path.length - 1; i++) {
            amounts[i + 1] = _performSwap(path[i], path[i + 1], amounts[i]);
        }

        return amounts;
    }

    // TP7: Multi-hop swap without slippage protection
    function swapMultiHop(
        address[] calldata path,
        uint256 amountIn
    ) external returns (uint256) {
        uint256 currentAmount = amountIn;

        for (uint i = 0; i < path.length - 1; i++) {
            currentAmount = _performSwap(path[i], path[i + 1], currentAmount);
        }

        return currentAmount;
    }

    // TP8: Swap with deadline but NO slippage protection
    function swapWithDeadline(
        address _tokenIn,
        address _tokenOut,
        uint256 amountIn,
        uint256 deadline
    ) external returns (uint256) {
        require(block.timestamp <= deadline, "Expired");
        return _performSwap(_tokenIn, _tokenOut, amountIn);
    }

    // Internal helper (used by vulnerable functions)
    function _performSwap(
        address from,
        address to,
        uint256 amountIn
    ) internal returns (uint256) {
        // Simulate AMM swap logic
        return amountIn * 99 / 100; // 1% slippage simulation
    }
}

// =============================================================================
// TRUE POSITIVES - VARIANT 2: Unenforced Slippage Parameter
// =============================================================================

contract VulnerableUnenforcedSlippage {

    // TP9: Parameter exists but NOT checked (CRITICAL vulnerability)
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut  // ← Parameter exists
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        // ❌ minAmountOut is IGNORED - no require check!
        return amountOut;
    }

    // TP10: Uses minAmountOut in event but NOT in validation
    function swapWithEvent(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        emit SwapExecuted(tokenIn, tokenOut, amountIn, amountOut, minAmountOut);
        // ❌ minAmountOut only in event, not validated!
        return amountOut;
    }

    // TP11: amountOutMin parameter but not enforced
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,  // ← Exists but unused
        address[] calldata path,
        address to
    ) external returns (uint256[] memory) {
        uint256[] memory amounts = new uint256[](path.length);
        amounts[0] = amountIn;

        for (uint i = 0; i < path.length - 1; i++) {
            amounts[i + 1] = _performSwap(path[i], path[i + 1], amounts[i]);
            // ❌ amountOutMin never checked!
        }

        return amounts;
    }

    // TP12: minOut parameter only used in return value
    function exactInputSingle(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minOut
    ) external returns (uint256, uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        // ❌ minOut returned but never validated!
        return (amountOut, minOut);
    }

    // TP13: slippageBps parameter but not enforced
    function swapWithSlippageBps(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 slippageBps  // Basis points (100 = 1%)
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        // ❌ slippageBps parameter ignored!
        return amountOut;
    }

    // TP14: Comment mentions slippage but code doesn't enforce it
    function swapWithComment(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut  // Minimum acceptable output
    ) external returns (uint256) {
        // TODO: Add slippage check
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        return amountOut;
    }

    event SwapExecuted(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOut,
        uint256 minAmountOut
    );

    function _performSwap(
        address from,
        address to,
        uint256 amountIn
    ) internal returns (uint256) {
        return amountIn * 98 / 100;
    }
}

// =============================================================================
// TRUE NEGATIVES - Safe Implementations
// =============================================================================

contract SafeWithSlippageProtection {

    // TN1: Standard safe implementation with require check
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);

        // ✅ SAFE: Slippage protection enforced
        require(amountOut >= minAmountOut, "Insufficient output amount");

        return amountOut;
    }

    // TN2: Alternative parameter naming (amountOutMin)
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory) {
        require(block.timestamp <= deadline, "Expired");

        uint256[] memory amounts = new uint256[](path.length);
        amounts[0] = amountIn;

        for (uint i = 0; i < path.length - 1; i++) {
            amounts[i + 1] = _performSwap(path[i], path[i + 1], amounts[i]);
        }

        // ✅ SAFE: Final output validated against minimum
        require(amounts[amounts.length - 1] >= amountOutMin, "Slippage too high");

        return amounts;
    }

    // TN3: Using minOut parameter with validation
    function exactInputSingle(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minOut
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);

        // ✅ SAFE: minOut validated
        require(amountOut >= minOut, "Slippage exceeded");

        return amountOut;
    }

    // TN4: Custom error for slippage protection
    function swapWithCustomError(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);

        // ✅ SAFE: Custom error used for validation
        if (amountOut < minAmountOut) {
            revert SlippageTooHigh(amountOut, minAmountOut);
        }

        return amountOut;
    }

    // TN5: Percentage-based slippage protection
    function swapWithSlippageBps(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 expectedOut,
        uint256 slippageBps
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);

        // ✅ SAFE: Percentage-based slippage validation
        uint256 minAcceptable = expectedOut * (10000 - slippageBps) / 10000;
        require(amountOut >= minAcceptable, "Slippage exceeds tolerance");

        return amountOut;
    }

    // TN6: Multi-hop with per-hop slippage protection
    function swapMultiHop(
        address[] calldata path,
        uint256 amountIn,
        uint256 minFinalOut,
        uint256[] calldata minIntermediateOuts
    ) external returns (uint256) {
        require(path.length >= 2, "Invalid path");
        require(minIntermediateOuts.length == path.length - 2, "Invalid intermediate");

        uint256 currentAmount = amountIn;

        for (uint i = 0; i < path.length - 1; i++) {
            currentAmount = _performSwap(path[i], path[i + 1], currentAmount);

            // ✅ SAFE: Per-hop slippage protection
            if (i < path.length - 2) {
                require(currentAmount >= minIntermediateOuts[i], "Intermediate slippage");
            }
        }

        // ✅ SAFE: Final output validation
        require(currentAmount >= minFinalOut, "Final slippage too high");

        return currentAmount;
    }

    error SlippageTooHigh(uint256 actual, uint256 minimum);

    function _performSwap(
        address from,
        address to,
        uint256 amountIn
    ) internal returns (uint256) {
        return amountIn * 99 / 100;
    }
}

// =============================================================================
// EDGE CASES
// =============================================================================

contract EdgeCases {

    // EDGE1: Internal function (not externally callable - SAFE from MEV)
    function _swapInternal(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) internal returns (uint256) {
        // No slippage parameter, but internal so not MEV-vulnerable
        return amountIn * 99 / 100;
    }

    // EDGE2: View function (read-only - SAFE, no state changes)
    function calculateSwapOutput(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) external view returns (uint256) {
        // No slippage parameter, but view function
        return amountIn * 99 / 100;
    }

    // EDGE3: Pure function (no state access - SAFE)
    function computeSwapRatio(
        uint256 amountIn,
        uint256 reserveIn,
        uint256 reserveOut
    ) external pure returns (uint256) {
        return (amountIn * reserveOut) / (reserveIn + amountIn);
    }

    // EDGE4: Swap with oracle price validation (alternative protection)
    function swapWithOracleValidation(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        address oracle
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);

        // Alternative protection: Oracle-based validation
        uint256 oraclePrice = IOraclePrice(oracle).getPrice(tokenIn, tokenOut);
        uint256 expectedMin = (amountIn * oraclePrice * 98) / (100 * 1e18);
        require(amountOut >= expectedMin, "Price deviation");

        return amountOut;
    }

    // EDGE5: Swap that delegates to trusted router (protection in router)
    function swapViaRouter(
        address router,
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minOut
    ) external returns (uint256[] memory) {
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;

        // Router enforces slippage protection
        return IUniswapV2Router(router).swapExactTokensForTokens(
            amountIn,
            minOut,
            path,
            msg.sender,
            block.timestamp + 300
        );
    }

    // EDGE6: Swap with reentrancy guard (different vulnerability mitigation)
    bool private locked;

    function swapWithReentrancyGuard(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) external returns (uint256) {
        require(!locked, "Reentrancy");
        locked = true;

        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);

        locked = false;
        return amountOut;
    }

    function _performSwap(
        address from,
        address to,
        uint256 amountIn
    ) internal returns (uint256) {
        return amountIn * 99 / 100;
    }
}

interface IOraclePrice {
    function getPrice(address tokenA, address tokenB) external view returns (uint256);
}

// =============================================================================
// VARIATION TESTING - Different Naming Conventions
// =============================================================================

contract NamingVariations {

    // VAR1: minOut naming (vulnerable - no check)
    function swapWithMinOut(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minOut
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        // ❌ minOut parameter ignored
        return amountOut;
    }

    // VAR2: minimumReceived naming (vulnerable - no check)
    function swapWithMinimumReceived(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minimumReceived
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        // ❌ minimumReceived not validated
        return amountOut;
    }

    // VAR3: minReturnAmount naming (vulnerable - no check)
    function swapWithMinReturnAmount(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minReturnAmount
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        // ❌ minReturnAmount not validated
        return amountOut;
    }

    // VAR4: amountOutMinimum (Uniswap V3 style - vulnerable without check)
    function exactInputSingle(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOutMinimum
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        // ❌ amountOutMinimum not validated
        return amountOut;
    }

    // VAR5: Safe with minOut and validation
    function swapWithMinOutSafe(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minOut
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        // ✅ SAFE: minOut validated
        require(amountOut >= minOut, "Insufficient output");
        return amountOut;
    }

    // VAR6: Safe with minimumReceived and validation
    function swapWithMinimumReceivedSafe(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minimumReceived
    ) external returns (uint256) {
        uint256 amountOut = _performSwap(tokenIn, tokenOut, amountIn);
        // ✅ SAFE: minimumReceived validated
        require(amountOut >= minimumReceived, "Below minimum");
        return amountOut;
    }

    function _performSwap(
        address from,
        address to,
        uint256 amountIn
    ) internal returns (uint256) {
        return amountIn * 98 / 100;
    }
}

// =============================================================================
// COMBINED SCENARIOS - Complex Real-World Patterns
// =============================================================================

contract RealWorldSwapPatterns {

    // REAL1: Uniswap V2 style - VULNERABLE (no slippage)
    function swapExactTokensForTokensUniV2Vulnerable(
        uint amountIn,
        address[] calldata path,
        address to
    ) external returns (uint[] memory amounts) {
        amounts = new uint[](path.length);
        amounts[0] = amountIn;

        for (uint i = 0; i < path.length - 1; i++) {
            amounts[i + 1] = _performSwap(path[i], path[i + 1], amounts[i]);
        }

        return amounts;
    }

    // REAL2: Uniswap V2 style - SAFE (with slippage)
    function swapExactTokensForTokensUniV2Safe(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts) {
        require(block.timestamp <= deadline, "UniswapV2Router: EXPIRED");

        amounts = new uint[](path.length);
        amounts[0] = amountIn;

        for (uint i = 0; i < path.length - 1; i++) {
            amounts[i + 1] = _performSwap(path[i], path[i + 1], amounts[i]);
        }

        // ✅ SAFE: Slippage protection
        require(amounts[amounts.length - 1] >= amountOutMin, "UniswapV2Router: INSUFFICIENT_OUTPUT_AMOUNT");

        return amounts;
    }

    // REAL3: SushiSwap style - VULNERABLE (parameter exists but not checked)
    function swapExactTokensForTokensSushiVulnerable(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts) {
        require(block.timestamp <= deadline, "SushiSwap: EXPIRED");

        amounts = new uint[](path.length);
        amounts[0] = amountIn;

        for (uint i = 0; i < path.length - 1; i++) {
            amounts[i + 1] = _performSwap(path[i], path[i + 1], amounts[i]);
        }

        // ❌ VULNERABLE: amountOutMin parameter exists but never checked!
        return amounts;
    }

    // REAL4: 1inch aggregator style - SAFE
    function swap1inch(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minReturn
    ) external returns (uint256 returnAmount) {
        returnAmount = _performSwap(tokenIn, tokenOut, amountIn);

        // ✅ SAFE: 1inch always enforces slippage
        require(returnAmount >= minReturn, "1inch: return amount is not enough");
    }

    function _performSwap(
        address from,
        address to,
        uint256 amountIn
    ) internal returns (uint256) {
        return amountIn * 97 / 100;
    }
}
