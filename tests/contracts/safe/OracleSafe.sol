// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title OracleSafe
 * @notice Safe implementations of oracle patterns.
 * @dev These contracts demonstrate proper oracle data validation.
 */

interface IChainlinkOracle {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}

interface ISequencerUptime {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

/**
 * @title ChainlinkOracleSafe
 * @notice Safe: Complete Chainlink oracle validation
 */
contract ChainlinkOracleSafe {
    IChainlinkOracle public priceFeed;
    uint256 public constant STALENESS_THRESHOLD = 1 hours;

    constructor(address _priceFeed) {
        priceFeed = IChainlinkOracle(_priceFeed);
    }

    // SAFE: All Chainlink validations
    function getPrice() external view returns (uint256) {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        // Check for stale data
        require(updatedAt > 0, "Round not complete");
        require(block.timestamp - updatedAt < STALENESS_THRESHOLD, "Stale price");

        // Check for valid round
        require(answeredInRound >= roundId, "Stale round");

        // Check for positive price
        require(answer > 0, "Invalid price");

        return uint256(answer);
    }
}

/**
 * @title L2OracleSafe
 * @notice Safe: L2 oracle with sequencer uptime check
 */
contract L2OracleSafe {
    IChainlinkOracle public priceFeed;
    ISequencerUptime public sequencerUptimeFeed;
    uint256 public constant STALENESS_THRESHOLD = 1 hours;
    uint256 public constant GRACE_PERIOD = 3600; // 1 hour after sequencer comes back

    constructor(address _priceFeed, address _sequencerFeed) {
        priceFeed = IChainlinkOracle(_priceFeed);
        sequencerUptimeFeed = ISequencerUptime(_sequencerFeed);
    }

    // SAFE: Check sequencer uptime before using price
    function getPrice() external view returns (uint256) {
        // Check sequencer status first
        (
            ,
            int256 sequencerAnswer,
            uint256 sequencerStartedAt,
            ,
        ) = sequencerUptimeFeed.latestRoundData();

        // Sequencer is down if answer == 1
        require(sequencerAnswer == 0, "Sequencer is down");

        // Ensure grace period has passed since sequencer came back up
        require(block.timestamp - sequencerStartedAt > GRACE_PERIOD, "Grace period not over");

        // Now get the price
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        require(updatedAt > 0, "Round not complete");
        require(block.timestamp - updatedAt < STALENESS_THRESHOLD, "Stale price");
        require(answeredInRound >= roundId, "Stale round");
        require(answer > 0, "Invalid price");

        return uint256(answer);
    }
}

/**
 * @title MultiOracleSafe
 * @notice Safe: Multiple oracle sources with deviation check
 */
contract MultiOracleSafe {
    IChainlinkOracle public primaryOracle;
    IChainlinkOracle public secondaryOracle;
    uint256 public constant MAX_DEVIATION = 300; // 3%
    uint256 public constant STALENESS_THRESHOLD = 1 hours;

    constructor(address _primary, address _secondary) {
        primaryOracle = IChainlinkOracle(_primary);
        secondaryOracle = IChainlinkOracle(_secondary);
    }

    // SAFE: Cross-validate multiple oracles
    function getPrice() external view returns (uint256) {
        uint256 primaryPrice = _getValidPrice(primaryOracle);
        uint256 secondaryPrice = _getValidPrice(secondaryOracle);

        // Check deviation between oracles
        uint256 deviation = primaryPrice > secondaryPrice
            ? ((primaryPrice - secondaryPrice) * 10000) / primaryPrice
            : ((secondaryPrice - primaryPrice) * 10000) / secondaryPrice;

        require(deviation <= MAX_DEVIATION, "Oracle deviation too high");

        // Return average
        return (primaryPrice + secondaryPrice) / 2;
    }

    function _getValidPrice(IChainlinkOracle oracle) internal view returns (uint256) {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = oracle.latestRoundData();

        require(updatedAt > 0, "Round not complete");
        require(block.timestamp - updatedAt < STALENESS_THRESHOLD, "Stale price");
        require(answeredInRound >= roundId, "Stale round");
        require(answer > 0, "Invalid price");

        return uint256(answer);
    }
}

/**
 * @title TwapOracleSafe
 * @notice Safe: TWAP oracle with proper window validation
 */
contract TwapOracleSafe {
    uint256 public constant TWAP_WINDOW = 30 minutes;
    uint256 public constant MIN_OBSERVATIONS = 2;

    struct Observation {
        uint256 timestamp;
        uint256 cumulativePrice;
    }

    Observation[] public observations;

    function recordObservation(uint256 cumulativePrice) external {
        observations.push(Observation({
            timestamp: block.timestamp,
            cumulativePrice: cumulativePrice
        }));
    }

    // SAFE: TWAP with minimum window and observation count
    function getTwapPrice() external view returns (uint256) {
        require(observations.length >= MIN_OBSERVATIONS, "Not enough observations");

        Observation memory oldest = observations[0];
        Observation memory newest = observations[observations.length - 1];

        uint256 timeElapsed = newest.timestamp - oldest.timestamp;
        require(timeElapsed >= TWAP_WINDOW, "TWAP window too short");

        uint256 priceDiff = newest.cumulativePrice - oldest.cumulativePrice;
        return priceDiff / timeElapsed;
    }
}

/**
 * @title OracleUpdateSafe
 * @notice Safe: Oracle update with rate limiting and validation
 */
contract OracleUpdateSafe {
    uint256 public price;
    uint256 public lastUpdateTime;
    address public updater;

    uint256 public constant MIN_UPDATE_INTERVAL = 5 minutes;
    uint256 public constant MAX_DEVIATION = 1000; // 10%

    constructor(address _updater) {
        updater = _updater;
    }

    modifier onlyUpdater() {
        require(msg.sender == updater, "Not updater");
        _;
    }

    // SAFE: Rate-limited with deviation check
    function updatePrice(uint256 newPrice) external onlyUpdater {
        require(newPrice > 0, "Invalid price");

        // Rate limit
        require(block.timestamp - lastUpdateTime >= MIN_UPDATE_INTERVAL, "Too soon");

        // Deviation check (skip for first update)
        if (price > 0) {
            uint256 deviation = newPrice > price
                ? ((newPrice - price) * 10000) / price
                : ((price - newPrice) * 10000) / price;
            require(deviation <= MAX_DEVIATION, "Deviation too high");
        }

        price = newPrice;
        lastUpdateTime = block.timestamp;
    }
}

/**
 * @title OracleCircuitBreakerSafe
 * @notice Safe: Oracle with circuit breaker for extreme conditions
 */
contract OracleCircuitBreakerSafe {
    IChainlinkOracle public priceFeed;
    uint256 public lastValidPrice;
    bool public circuitBroken;

    uint256 public constant STALENESS_THRESHOLD = 1 hours;
    uint256 public constant MAX_PRICE_CHANGE = 5000; // 50%

    constructor(address _priceFeed) {
        priceFeed = IChainlinkOracle(_priceFeed);
    }

    // SAFE: Circuit breaker for abnormal conditions
    function getPrice() external view returns (uint256) {
        require(!circuitBroken, "Circuit breaker active");

        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        require(updatedAt > 0, "Round not complete");
        require(block.timestamp - updatedAt < STALENESS_THRESHOLD, "Stale price");
        require(answeredInRound >= roundId, "Stale round");
        require(answer > 0, "Invalid price");

        return uint256(answer);
    }

    function checkAndUpdateCircuitBreaker() external {
        (, int256 answer, , , ) = priceFeed.latestRoundData();
        if (answer <= 0) {
            circuitBroken = true;
            return;
        }

        uint256 currentPrice = uint256(answer);
        if (lastValidPrice > 0) {
            uint256 change = currentPrice > lastValidPrice
                ? ((currentPrice - lastValidPrice) * 10000) / lastValidPrice
                : ((lastValidPrice - currentPrice) * 10000) / lastValidPrice;

            if (change > MAX_PRICE_CHANGE) {
                circuitBroken = true;
                return;
            }
        }

        lastValidPrice = currentPrice;
        circuitBroken = false;
    }
}
