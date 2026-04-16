// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleVault_06 - SAFE
 * @dev Multi-oracle aggregation with fallback and L2 sequencer check.
 * @notice Case ID: OR-SAFE-002
 *
 * SAFE: Primary + fallback oracles, median aggregation, sequencer uptime check.
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

interface IUniswapV3Pool {
    function observe(uint32[] calldata secondsAgos) external view returns (
        int56[] memory tickCumulatives,
        uint160[] memory secondsPerLiquidityCumulativeX128s
    );
}

contract OracleVault_06 {
    // SAFE: Multiple oracle sources
    AggregatorV3Interface public primaryOracle;
    AggregatorV3Interface public fallbackOracle;
    AggregatorV3Interface public sequencerUptimeFeed;
    IUniswapV3Pool public twapPool;

    mapping(address => uint256) public balances;

    uint256 public constant STALENESS_THRESHOLD = 1 hours;
    uint256 public constant GRACE_PERIOD_TIME = 1 hours;
    uint256 public constant MAX_DEVIATION = 5; // 5% max deviation between sources

    constructor(
        address _primaryOracle,
        address _fallbackOracle,
        address _sequencerFeed,
        address _twapPool
    ) {
        primaryOracle = AggregatorV3Interface(_primaryOracle);
        fallbackOracle = AggregatorV3Interface(_fallbackOracle);
        sequencerUptimeFeed = AggregatorV3Interface(_sequencerFeed);
        twapPool = IUniswapV3Pool(_twapPool);
    }

    // SAFE: L2 sequencer uptime check with grace period
    function checkSequencer() internal view {
        (
            ,
            int256 answer,
            uint256 startedAt,
            ,

        ) = sequencerUptimeFeed.latestRoundData();

        // answer == 0 means sequencer is up
        bool isSequencerUp = answer == 0;
        require(isSequencerUp, "Sequencer is down");

        // SAFE: Grace period after sequencer restart
        uint256 timeSinceUp = block.timestamp - startedAt;
        require(timeSinceUp > GRACE_PERIOD_TIME, "Grace period not over");
    }

    // SAFE: Get price from single oracle with validation
    function getOraclePrice(AggregatorV3Interface oracle) internal view returns (uint256, bool) {
        try oracle.latestRoundData() returns (
            uint80 roundId,
            int256 answer,
            uint256,
            uint256 updatedAt,
            uint80 answeredInRound
        ) {
            if (updatedAt < block.timestamp - STALENESS_THRESHOLD) return (0, false);
            if (answeredInRound < roundId) return (0, false);
            if (answer <= 0) return (0, false);

            uint8 decimals = oracle.decimals();
            uint256 price = uint256(answer);
            if (decimals < 18) {
                price = price * (10 ** (18 - decimals));
            }
            return (price, true);
        } catch {
            return (0, false);
        }
    }

    // SAFE: Multi-oracle aggregation with fallback
    function getAggregatedPrice() public view returns (uint256) {
        // SAFE: Check L2 sequencer first
        checkSequencer();

        // SAFE: Try primary oracle
        (uint256 primaryPrice, bool primaryValid) = getOraclePrice(primaryOracle);

        // SAFE: Try fallback oracle
        (uint256 fallbackPrice, bool fallbackValid) = getOraclePrice(fallbackOracle);

        // SAFE: At least one oracle must be valid
        require(primaryValid || fallbackValid, "All oracles failed");

        // SAFE: If both valid, check deviation and use median
        if (primaryValid && fallbackValid) {
            uint256 deviation;
            if (primaryPrice > fallbackPrice) {
                deviation = ((primaryPrice - fallbackPrice) * 100) / fallbackPrice;
            } else {
                deviation = ((fallbackPrice - primaryPrice) * 100) / primaryPrice;
            }
            require(deviation <= MAX_DEVIATION, "Oracle prices deviate too much");

            // Return average of both prices
            return (primaryPrice + fallbackPrice) / 2;
        }

        // SAFE: Return whichever oracle is valid
        return primaryValid ? primaryPrice : fallbackPrice;
    }

    function deposit() external payable {
        uint256 price = getAggregatedPrice();
        uint256 shares = (msg.value * 1e18) / price;
        balances[msg.sender] += shares;
    }

    function withdraw(uint256 shares) external {
        require(balances[msg.sender] >= shares, "Insufficient balance");
        uint256 price = getAggregatedPrice();
        uint256 amount = (shares * price) / 1e18;
        balances[msg.sender] -= shares;
        payable(msg.sender).transfer(amount);
    }
}
