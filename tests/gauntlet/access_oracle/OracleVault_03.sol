// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleVault_03 - VULNERABLE
 * @dev Single oracle source - No fallback if primary oracle fails.
 * @notice Case ID: OR-VULN-003
 *
 * VULNERABILITY: Single Chainlink feed with no fallback.
 * If oracle is compromised or deprecated, entire protocol is at risk.
 */

interface AggregatorV3Interface {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}

contract OracleVault_03 {
    // VULNERABILITY: Single oracle source, no fallback
    AggregatorV3Interface public priceFeed;
    mapping(address => uint256) public balances;

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    // VULNERABILITY: No fallback oracle, no circuit breaker
    // If this oracle fails, the entire protocol is stuck
    function getLatestPrice() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        require(updatedAt >= block.timestamp - 1 hours, "Stale price");
        require(answer > 0, "Invalid price");

        // Missing: try fallbackOracle.latestRoundData() catch { ... }
        // Missing: require(deviation < MAX_DEVIATION, "Price deviation");

        return uint256(answer);
    }

    function deposit() external payable {
        uint256 price = getLatestPrice();
        uint256 shares = (msg.value * 1e18) / price;
        balances[msg.sender] += shares;
    }

    function withdraw(uint256 shares) external {
        require(balances[msg.sender] >= shares, "Insufficient balance");
        uint256 price = getLatestPrice();
        uint256 amount = (shares * price) / 1e18;
        balances[msg.sender] -= shares;
        payable(msg.sender).transfer(amount);
    }
}
