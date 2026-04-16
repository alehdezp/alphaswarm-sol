// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleCircuitBreaker
 * @notice Demonstrates secure oracle integration with circuit breaker pattern
 *
 * Security Features:
 * - Staleness check (updatedAt validation)
 * - Round ID validation (answeredInRound >= roundId)
 * - Price bounds validation (circuit breaker)
 * - Zero price check
 * - L2 sequencer uptime check (for L2 deployments)
 *
 * Related CWEs:
 * - CWE-829: Inclusion of Functionality from Untrusted Control Sphere
 * - CWE-20: Improper Input Validation
 *
 * OWASP SC02:2025 - Price Oracle Manipulation mitigation pattern
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

interface ISequencerUptimeFeed {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

contract OracleCircuitBreaker {
    IChainlinkOracle public oracle;
    ISequencerUptimeFeed public sequencerUptimeFeed;

    uint256 public constant STALENESS_THRESHOLD = 1 hours;
    uint256 public constant GRACE_PERIOD_TIME = 3600; // 1 hour grace after sequencer comes back up
    int256 public constant MIN_PRICE = 1e6;
    int256 public constant MAX_PRICE = 1e12;

    int256 public lastValidPrice;
    uint256 public lastValidTimestamp;

    error StalePrice();
    error InvalidRound();
    error PriceOutOfBounds();
    error SequencerDown();
    error GracePeriodNotOver();
    error InvalidPrice();

    constructor(IChainlinkOracle oracle_, ISequencerUptimeFeed sequencerFeed_) {
        oracle = oracle_;
        sequencerUptimeFeed = sequencerFeed_;
    }

    function getPriceWithCircuitBreaker() external returns (int256) {
        // Check L2 sequencer uptime (important for Arbitrum/Optimism)
        _checkSequencerUptime();

        (uint80 roundId, int256 answer, , uint256 updatedAt, uint80 answeredInRound) = oracle.latestRoundData();

        // Validate freshness
        if (updatedAt < block.timestamp - STALENESS_THRESHOLD) {
            revert StalePrice();
        }

        // Validate round (note: answeredInRound is deprecated but still useful)
        if (answeredInRound < roundId) {
            revert InvalidRound();
        }

        // Validate price is positive
        if (answer <= 0) {
            revert InvalidPrice();
        }

        // Circuit breaker: check bounds
        if (answer < MIN_PRICE || answer > MAX_PRICE) {
            revert PriceOutOfBounds();
        }

        // Store last valid price
        lastValidPrice = answer;
        lastValidTimestamp = block.timestamp;

        return answer;
    }

    function _checkSequencerUptime() internal view {
        (, int256 answer, uint256 startedAt, ,) = sequencerUptimeFeed.latestRoundData();

        // answer == 0: Sequencer is up
        // answer == 1: Sequencer is down
        if (answer != 0) {
            revert SequencerDown();
        }

        // Check grace period after sequencer comes back up
        uint256 timeSinceUp = block.timestamp - startedAt;
        if (timeSinceUp < GRACE_PERIOD_TIME) {
            revert GracePeriodNotOver();
        }
    }

    function getFallbackPrice() external view returns (int256) {
        // Use last valid price if oracle fails
        require(lastValidTimestamp > 0, "No valid price stored");
        require(block.timestamp - lastValidTimestamp < 24 hours, "Fallback too old");
        return lastValidPrice;
    }
}
