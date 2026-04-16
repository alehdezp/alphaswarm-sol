// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleDeprecatedLatestAnswer
 * @notice VULNERABLE: Uses deprecated latestAnswer() without validation
 *
 * Vulnerabilities:
 * - Uses deprecated latestAnswer() instead of latestRoundData()
 * - No staleness check (no updatedAt validation)
 * - No round ID validation
 * - No zero price check
 * - Returns 0 on failure without revert
 *
 * Related CWEs:
 * - CWE-477: Use of Obsolete Function
 * - CWE-20: Improper Input Validation
 *
 * Real-world impact:
 * - Multiple Code4rena findings (2021-06-tracer, 2022-10-inverse)
 * - Can cause incorrect liquidations or over-borrowing
 */

interface IChainlinkDeprecated {
    function latestAnswer() external view returns (int256);
}

contract OracleDeprecatedLatestAnswer {
    IChainlinkDeprecated public oracle;

    constructor(IChainlinkDeprecated oracle_) {
        oracle = oracle_;
    }

    // VULNERABLE: No validation whatsoever
    function getPrice() external view returns (int256) {
        return oracle.latestAnswer();
    }

    // VULNERABLE: Only checks non-zero, but price could be stale
    function getPriceWithMinimalCheck() external view returns (int256) {
        int256 price = oracle.latestAnswer();
        require(price > 0, "Invalid price");
        return price;
    }
}
