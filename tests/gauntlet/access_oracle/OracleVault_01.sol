// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleVault_01 - VULNERABLE
 * @dev Oracle staleness - No timestamp validation on price feed.
 * @notice Case ID: OR-VULN-001
 *
 * VULNERABILITY: Uses Chainlink price without checking updatedAt timestamp.
 * Stale prices can be exploited during oracle downtime.
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

contract OracleVault_01 {
    AggregatorV3Interface public priceFeed;
    mapping(address => uint256) public balances;

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    // VULNERABILITY: No staleness check on oracle price
    // If oracle is down or stale, outdated price is used
    function getPrice() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            ,  // updatedAt is ignored - VULNERABLE

        ) = priceFeed.latestRoundData();

        // Missing: require(updatedAt >= block.timestamp - STALENESS_THRESHOLD);
        require(answer > 0, "Invalid price");
        return uint256(answer);
    }

    function deposit() external payable {
        uint256 price = getPrice();
        uint256 shares = (msg.value * 1e18) / price;
        balances[msg.sender] += shares;
    }

    function withdraw(uint256 shares) external {
        require(balances[msg.sender] >= shares, "Insufficient balance");
        uint256 price = getPrice();
        uint256 amount = (shares * price) / 1e18;
        balances[msg.sender] -= shares;
        payable(msg.sender).transfer(amount);
    }
}
