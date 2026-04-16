// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleVault_02 - VULNERABLE
 * @dev Oracle decimal mismatch - Assumes 18 decimals but oracle returns 8.
 * @notice Case ID: OR-VULN-002
 *
 * VULNERABILITY: Oracle returns 8 decimals but contract assumes 18.
 * This 10^10 difference causes massive over/under-valuation.
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

contract OracleVault_02 {
    AggregatorV3Interface public priceFeed;  // Returns 8 decimals
    mapping(address => uint256) public balances;

    // VULNERABILITY: Hardcoded 18 decimals assumption
    uint256 constant PRICE_DECIMALS = 18;  // Wrong! Oracle returns 8

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    function getPrice() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        require(updatedAt >= block.timestamp - 1 hours, "Stale price");
        require(answer > 0, "Invalid price");
        return uint256(answer);
    }

    // VULNERABILITY: Decimal mismatch in value calculation
    // Oracle returns 8 decimals, but we assume 18 decimals
    function calculateValue(uint256 amount) public view returns (uint256) {
        uint256 price = getPrice();
        // Missing: uint8 decimals = priceFeed.decimals();
        // Missing: price = price * 10**(18 - decimals);

        // This assumes price is 18 decimals but it's actually 8
        // Result is 10^10 times smaller than expected
        return (amount * price) / (10 ** PRICE_DECIMALS);
    }

    function deposit() external payable {
        uint256 value = calculateValue(msg.value);
        balances[msg.sender] += value;
    }

    function withdraw(uint256 shares) external {
        require(balances[msg.sender] >= shares, "Insufficient balance");
        balances[msg.sender] -= shares;
        uint256 price = getPrice();
        uint256 amount = (shares * (10 ** PRICE_DECIMALS)) / price;
        payable(msg.sender).transfer(amount);
    }
}
