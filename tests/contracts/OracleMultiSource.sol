// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleMultiSource
 * @notice Demonstrates multi-oracle aggregation for manipulation resistance
 *
 * Security Features:
 * - Aggregates prices from multiple independent oracles
 * - Calculates median to resist outliers
 * - Validates each oracle source independently
 * - Detects price deviation beyond threshold
 *
 * Related CWEs:
 * - CWE-829: Inclusion of Functionality from Untrusted Control Sphere
 * - CWE-20: Improper Input Validation
 *
 * OWASP SC02:2025 mitigation: "Aggregate data from multiple, independent oracles"
 */

interface IPriceOracle {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

contract OracleMultiSource {
    IPriceOracle[] public oracles;
    uint256 public constant STALENESS_THRESHOLD = 1 hours;
    uint256 public constant MAX_DEVIATION_BPS = 500; // 5% max deviation

    error InsufficientOracles();
    error StalePrice(uint256 oracleIndex);
    error InvalidPrice(uint256 oracleIndex);
    error ExcessiveDeviation();

    constructor(IPriceOracle[] memory oracles_) {
        require(oracles_.length >= 3, "Need at least 3 oracles");
        oracles = oracles_;
    }

    function getAggregatedPrice() external view returns (int256) {
        uint256 oracleCount = oracles.length;
        if (oracleCount < 3) {
            revert InsufficientOracles();
        }

        int256[] memory prices = new int256[](oracleCount);

        // Fetch and validate all oracle prices
        for (uint256 i = 0; i < oracleCount; i++) {
            (uint80 roundId, int256 answer, , uint256 updatedAt, uint80 answeredInRound) = oracles[i].latestRoundData();

            // Validate staleness
            if (updatedAt < block.timestamp - STALENESS_THRESHOLD) {
                revert StalePrice(i);
            }

            // Validate round
            require(answeredInRound >= roundId, "Invalid round");

            // Validate price
            if (answer <= 0) {
                revert InvalidPrice(i);
            }

            prices[i] = answer;
        }

        // Calculate median price
        int256 medianPrice = _calculateMedian(prices);

        // Check deviation from median
        for (uint256 i = 0; i < oracleCount; i++) {
            uint256 deviation = _calculateDeviation(prices[i], medianPrice);
            if (deviation > MAX_DEVIATION_BPS) {
                revert ExcessiveDeviation();
            }
        }

        return medianPrice;
    }

    function _calculateMedian(int256[] memory values) internal pure returns (int256) {
        uint256 length = values.length;
        _quickSort(values, 0, int256(length - 1));

        if (length % 2 == 0) {
            return (values[length / 2 - 1] + values[length / 2]) / 2;
        } else {
            return values[length / 2];
        }
    }

    function _quickSort(int256[] memory arr, int256 left, int256 right) internal pure {
        if (left >= right) return;

        int256 pivot = arr[uint256(left + (right - left) / 2)];
        int256 i = left;
        int256 j = right;

        while (i <= j) {
            while (arr[uint256(i)] < pivot) i++;
            while (arr[uint256(j)] > pivot) j--;
            if (i <= j) {
                (arr[uint256(i)], arr[uint256(j)]) = (arr[uint256(j)], arr[uint256(i)]);
                i++;
                j--;
            }
        }

        if (left < j) _quickSort(arr, left, j);
        if (i < right) _quickSort(arr, i, right);
    }

    function _calculateDeviation(int256 price, int256 median) internal pure returns (uint256) {
        int256 diff = price > median ? price - median : median - price;
        return uint256((diff * 10000) / median);
    }
}
