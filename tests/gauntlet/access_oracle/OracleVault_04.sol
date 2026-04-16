// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleVault_04 - VULNERABLE
 * @dev L2 sequencer grace period missing - No sequencer uptime check.
 * @notice Case ID: OR-VULN-004
 *
 * VULNERABILITY: On L2 (Arbitrum/Optimism), missing sequencer uptime feed.
 * After sequencer restart, stale prices persist during grace period.
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

contract OracleVault_04 {
    AggregatorV3Interface public priceFeed;
    // Missing: AggregatorV3Interface public sequencerUptimeFeed;

    mapping(address => uint256) public balances;

    // Missing: uint256 constant GRACE_PERIOD_TIME = 3600; // 1 hour

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
        // Missing: sequencerUptimeFeed = AggregatorV3Interface(_sequencerFeed);
    }

    // VULNERABILITY: No L2 sequencer check
    // On Arbitrum/Optimism, sequencer can go down and prices become stale
    // When it comes back, there's a grace period where prices are unreliable
    function getPrice() public view returns (uint256) {
        // Missing sequencer uptime check:
        // (
        //     ,
        //     int256 answer,
        //     uint256 startedAt,
        //     ,
        //
        // ) = sequencerUptimeFeed.latestRoundData();
        //
        // bool isSequencerUp = answer == 0;
        // require(isSequencerUp, "Sequencer is down");
        //
        // uint256 timeSinceUp = block.timestamp - startedAt;
        // require(timeSinceUp > GRACE_PERIOD_TIME, "Grace period not over");

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
