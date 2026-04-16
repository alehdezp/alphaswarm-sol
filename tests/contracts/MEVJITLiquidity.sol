// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MEVJITLiquidity
 * @notice Demonstrates Just-In-Time (JIT) liquidity attack pattern on Uniswap V3
 *
 * Uniswap V3 concentrated liquidity allows JIT attacks where
 * attackers mint liquidity immediately before large swaps and burn immediately after.
 *
 * JIT Liquidity Attack Flow (LP Sandwich):
 * 1. Attacker monitors mempool for large swap transaction
 * 2. Attacker mints concentrated liquidity position just before swap (frontrun)
 * 3. Large swap executes, paying fees to attacker's fresh LP position
 * 4. Attacker burns LP position immediately after swap (backrun)
 * 5. Attacker profits from fees + price impact without long-term liquidity provision
 *
 * Scale: 36,671 attacks over 20 months generating 7,498 ETH profit
 * Entry barrier: Requires 269x swap volume in liquidity on average
 *
 * This is a specific type of MEV unique to concentrated liquidity AMMs
 */

interface IUniswapV3Pool {
    function mint(address recipient, int24 tickLower, int24 tickUpper, uint128 amount, bytes calldata data)
        external returns (uint256 amount0, uint256 amount1);
    function burn(int24 tickLower, int24 tickUpper, uint128 amount)
        external returns (uint256 amount0, uint256 amount1);
    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1);
}

contract MEVJITLiquidity {
    IUniswapV3Pool public pool;

    constructor(IUniswapV3Pool _pool) {
        pool = _pool;
    }

    // VULNERABLE: Allows same-block liquidity provision and removal
    // This enables JIT attacks where LP is added/removed atomically around swaps
    function jitAttack(
        int24 tickLower,
        int24 tickUpper,
        uint128 liquidityAmount,
        int256 swapAmount,
        uint160 sqrtPriceLimitX96
    ) external {
        // Step 1: Mint concentrated liquidity just before victim's swap
        // (In real attack, this would be separate frontrun transaction)
        pool.mint(address(this), tickLower, tickUpper, liquidityAmount, "");

        // Step 2: Victim's large swap executes (or attacker triggers it)
        // Fees accrue to the just-added liquidity
        pool.swap(address(this), true, swapAmount, sqrtPriceLimitX96, "");

        // Step 3: Burn liquidity immediately to collect fees + price impact
        // (In real attack, this would be separate backrun transaction)
        pool.burn(tickLower, tickUpper, liquidityAmount);

        // Attacker has extracted MEV without providing long-term liquidity
    }

    // VULNERABLE: No protection against same-block LP manipulation
    function provideLiquidity(int24 tickLower, int24 tickUpper, uint128 amount) external {
        // No checks for minimum liquidity duration
        // No checks for frontrunning detection
        pool.mint(msg.sender, tickLower, tickUpper, amount, "");
    }
}
