// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IDataProvider {
    function fetchLatestData() external view returns (
        uint80 roundId,
        int256 data,
        uint256 startedAt,
        uint256 lastUpdate,
        uint80 answeredInRound
    );
}

/**
 * @title OracleRenamed
 * @notice Oracle usage with non-standard naming.
 *         Tests detection of oracle vulnerabilities without "oracle", "price", "feed" names.
 *
 * Renamed: oracle -> dataSource, getPrice -> fetchQuote, latestRoundData -> fetchLatestData
 */
contract OracleRenamed {
    IDataProvider public dataSource;  // Renamed from "oracle" or "priceFeed"
    uint256 public maximumDelay;  // Renamed from "stalenessThreshold"

    constructor(address _dataSource, uint256 _maximumDelay) {
        dataSource = IDataProvider(_dataSource);
        maximumDelay = _maximumDelay;
    }

    // VULNERABLE: No staleness check
    function fetchQuoteUnsafe() external view returns (int256) {
        (,int256 data,,,) = dataSource.fetchLatestData();
        return data;
    }

    // SAFE: With staleness check
    function fetchQuoteSafe() external view returns (int256) {
        (,int256 data,,uint256 lastUpdate,) = dataSource.fetchLatestData();
        require(block.timestamp - lastUpdate <= maximumDelay, "stale data");
        return data;
    }

    // VULNERABLE: Uses oracle data for critical decision without validation
    function executeBasedOnData() external {
        (,int256 data,,,) = dataSource.fetchLatestData();
        require(data > 0, "negative data");
        // Critical operation based on potentially stale/manipulated data
    }
}
