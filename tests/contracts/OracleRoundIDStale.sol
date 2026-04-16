// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleRoundIDStale
 * @notice VULNERABLE: Missing round ID validation (answeredInRound check)
 *
 *  * - Checks staleness via updatedAt but missing answeredInRound validation
 * - answeredInRound < roundId means answer is being "carried over"
 * - This can allow stale prices even if updatedAt is recent
 *
 * Related CWEs:
 * - CWE-20: Improper Input Validation
 * - CWE-1023: Incomplete Comparison with Missing Factors
 *
 * Note: answeredInRound is deprecated but still useful for detecting stale answers
 * Mitigation: Use both updatedAt check AND answeredInRound >= roundId check
 */

interface IChainlinkOracle {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

contract OracleRoundIDStale {
    IChainlinkOracle public oracle;
    uint256 public constant STALENESS_THRESHOLD = 1 hours;

    constructor(IChainlinkOracle oracle_) {
        oracle = oracle_;
    }

    // VULNERABLE: Missing answeredInRound check
    function getPrice() external view returns (int256) {
        (, int256 answer, , uint256 updatedAt, ) = oracle.latestRoundData();

        require(updatedAt >= block.timestamp - STALENESS_THRESHOLD, "Stale price");
        require(answer > 0, "Invalid price");

        // Missing: require(answeredInRound >= roundId, "Answer stale");

        return answer;
    }
}
