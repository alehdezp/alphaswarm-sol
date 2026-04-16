// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MEVOracleManipulation
 * @notice Demonstrates oracle manipulation via flash loan + MEV
 *
 * Using single DEX spot price as oracle allows flash loan attacks
 * to manipulate price within single transaction.
 *
 * Flash Loan Oracle Manipulation Flow:
 * 1. Attacker takes flash loan (e.g., 1M USDC)
 * 2. Buys target token on DEX, drastically moving spot price
 * 3. Calls vulnerable contract that reads manipulated spot price
 * 4. Contract performs action based on inflated price (mint/borrow/liquidate)
 * 5. Attacker sells tokens back, repays flash loan, keeps profit
 *
 * CWE Mapping: SCWE-028 (Price Oracle Manipulation)
 * Related: SC07:2025 Flash Loan Attacks, CWE-20
 *
 * Protection: Use TWAP, Chainlink, or multi-oracle aggregation
 */

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
}

contract MEVOracleManipulation {
    IUniswapV2Pair public pair;

    constructor(IUniswapV2Pair _pair) {
        pair = _pair;
    }

    // VULNERABLE: Uses spot price from single DEX as oracle
    function getPrice() public view returns (uint256) {
        (uint112 reserve0, uint112 reserve1,) = pair.getReserves();
        // Direct spot price calculation - manipulable in single transaction
        return (uint256(reserve1) * 1e18) / uint256(reserve0);
    }

    // VULNERABLE: Mints based on manipulable oracle
    function mintBasedOnPrice(uint256 amount) external view returns (uint256) {
        uint256 price = getPrice();
        // Attacker can inflate price to mint excess tokens
        return amount * price / 1e18;
    }

    // VULNERABLE: No staleness check, no TWAP, no multi-oracle
    function borrowLimit() external view returns (uint256) {
        uint256 price = getPrice();
        return price * 100; // Collateral value based on manipulable price
    }
}
