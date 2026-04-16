// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TwapFlashLoanManipulation
 * @notice VULNERABLE: Uses spot price from Uniswap reserves (flash loan manipulable)
 *
 * Vulnerabilities:
 * - Uses getReserves() spot price instead of TWAP
 * - No time-weighting, vulnerable to single-block manipulation
 * - Flash loans can drain one side of pool to manipulate price
 *
 * Related CWEs:
 * - CWE-20: Improper Input Validation
 * - SCWE-028: Price Oracle Manipulation
 *
 * Real-world exploits:
 * - Visor Finance (2021)
 * - Value DeFi (2020)
 * - Multiple DeFi hacks using flash loan + spot price manipulation
 *
 * Attack vector:
 * 1. Take flash loan
 * 2. Drain pool reserves (alter spot price)
 * 3. Call this contract to get manipulated price
 * 4. Profit from mispricing (borrow more, mint cheaper, etc)
 * 5. Repay flash loan
 */

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
}

contract TwapFlashLoanManipulation {
    IUniswapV2Pair public pair;

    constructor(IUniswapV2Pair pair_) {
        pair = pair_;
    }

    // VULNERABLE: Spot price is flash loan manipulable
    function getSpotPrice() external view returns (uint256) {
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();
        require(reserve0 > 0 && reserve1 > 0, "Invalid reserves");

        // This is the spot price, NOT time-weighted
        return (uint256(reserve1) * 1e18) / uint256(reserve0);
    }

    // VULNERABLE: Even with balance checks, still manipulable
    function getPriceForCollateral(address token) external view returns (uint256) {
        (uint112 reserve0, uint112 reserve1, ) = pair.getReserves();

        // Some protocols check that reserves are "reasonable"
        // But this doesn't prevent flash loan manipulation
        require(reserve0 > 1e18 && reserve1 > 1e18, "Insufficient liquidity");

        return (uint256(reserve1) * 1e18) / uint256(reserve0);
    }
}
