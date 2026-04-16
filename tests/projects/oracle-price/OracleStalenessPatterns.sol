// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

/**
 * @title OracleStalenessPatterns
 * @notice Test contract for oracle-001: Oracle Read With Staleness Check (Safe Pattern)
 * @dev This tests the SAFE PATTERN - functions that properly check staleness
 *
 * Pattern Logic:
 *   - has_operation: READS_ORACLE
 *   - has_staleness_check: true
 *
 * Property Detection:
 *   - READS_ORACLE: Triggered by calls to latestRoundData, getPrice, consult
 *   - has_staleness_check: Detects "updatedAt", "answeredInRound", "roundId" in require
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

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function price0CumulativeLast() external view returns (uint256);
    function price1CumulativeLast() external view returns (uint256);
}

contract OracleStalenessPatterns {
    AggregatorV3Interface public priceFeed;
    AggregatorV3Interface public sequencerUptimeFeed;
    IUniswapV2Pair public uniswapPair;

    uint256 public constant STALENESS_THRESHOLD = 1 hours;
    uint256 public constant MAX_STALENESS = 3600; // 1 hour in seconds
    uint256 public stalenessThreshold = 1 hours;

    address public owner;

    constructor(address _priceFeed, address _sequencerFeed, address _uniswapPair) {
        priceFeed = AggregatorV3Interface(_priceFeed);
        sequencerUptimeFeed = AggregatorV3Interface(_sequencerFeed);
        uniswapPair = IUniswapV2Pair(_uniswapPair);
        owner = msg.sender;
    }

    // =============================================================================
    // TRUE POSITIVES: Oracle reads WITH staleness checks (SAFE PATTERN)
    // =============================================================================

    /// @notice TP1: Standard updatedAt check with block.timestamp comparison
    /// @dev Pattern should MATCH: has READS_ORACLE + has_staleness_check
    function getPriceWithStalenessCheck() public view returns (uint256) {
        (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        // STALENESS CHECK: updatedAt validation
        require(updatedAt != 0, "Oracle: incomplete round");
        require(block.timestamp - updatedAt <= STALENESS_THRESHOLD, "Oracle: stale price");
        require(answer > 0, "Oracle: invalid price");

        return uint256(answer);
    }

    /// @notice TP2: answeredInRound staleness check (Chainlink-specific)
    /// @dev Pattern should MATCH: has answeredInRound check
    function getPriceWithRoundCheck() public view returns (uint256) {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        // STALENESS CHECK: answeredInRound >= roundId
        require(answeredInRound >= roundId, "Oracle: stale round");
        require(updatedAt != 0, "Oracle: incomplete round");

        return uint256(answer);
    }

    /// @notice TP3: Both updatedAt and answeredInRound checks (best practice)
    /// @dev Pattern should MATCH: has both staleness checks
    function getPriceWithCompleteChecks() public view returns (uint256) {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        // COMPLETE STALENESS CHECKS
        require(updatedAt != 0, "Incomplete round");
        require(answer > 0, "Invalid price");
        require(block.timestamp - updatedAt <= STALENESS_THRESHOLD, "Stale price");
        require(answeredInRound >= roundId, "Stale round");

        return uint256(answer);
    }

    /// @notice TP4: Staleness check with different naming (maxAge variable)
    /// @dev Pattern should MATCH: variation with different naming
    function getPriceWithMaxAge() public view returns (uint256) {
        uint256 maxAge = 3600;

        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        // STALENESS CHECK: different naming pattern
        require(block.timestamp - updatedAt < maxAge, "Price too old");

        return uint256(answer);
    }

    /// @notice TP5: Staleness check using configurable threshold
    /// @dev Pattern should MATCH: uses state variable threshold
    function getPriceWithConfigurableThreshold() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        // STALENESS CHECK: configurable threshold
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");

        return uint256(answer);
    }

    /// @notice TP6: Staleness check with if-revert pattern
    /// @dev Pattern should MATCH: if statement instead of require
    function getPriceWithIfRevert() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        // STALENESS CHECK: if-revert pattern
        if (block.timestamp - updatedAt > STALENESS_THRESHOLD) {
            revert("Stale price");
        }

        return uint256(answer);
    }

    /// @notice TP7: Staleness check in internal helper function
    /// @dev Pattern should MATCH: internal function with staleness check
    function getPriceViaHelper() public view returns (uint256) {
        return _getPriceWithStalenessCheck();
    }

    function _getPriceWithStalenessCheck() internal view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        require(block.timestamp - updatedAt <= STALENESS_THRESHOLD, "Stale");
        return uint256(answer);
    }

    /// @notice TP8: Sequencer uptime check (L2 pattern)
    /// @dev Pattern should MATCH: L2 sequencer validation includes updatedAt
    function getPriceWithSequencerCheck() public view returns (uint256) {
        // Check sequencer uptime
        (
            ,
            int256 sequencerAnswer,
            uint256 startedAt,
            ,

        ) = sequencerUptimeFeed.latestRoundData();

        require(sequencerAnswer == 0, "Sequencer down");
        require(block.timestamp - startedAt > 3600, "Grace period");

        // Get price with staleness check
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        // STALENESS CHECKS
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= STALENESS_THRESHOLD, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        return uint256(answer);
    }

    /// @notice TP9: Multiple oracle reads with staleness checks
    /// @dev Pattern should MATCH: both oracle reads have staleness checks
    function getAveragePriceWithChecks() public view returns (uint256) {
        // First oracle
        (
            ,
            int256 answer1,
            ,
            uint256 updatedAt1,

        ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt1 <= STALENESS_THRESHOLD, "Oracle1 stale");

        // Second oracle (simulate another feed)
        (
            ,
            int256 answer2,
            ,
            uint256 updatedAt2,

        ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt2 <= STALENESS_THRESHOLD, "Oracle2 stale");

        return (uint256(answer1) + uint256(answer2)) / 2;
    }

    /// @notice TP10: TWAP oracle with blockTimestampLast check
    /// @dev Pattern should MATCH: TWAP staleness validation
    function getTWAPPriceWithStalenessCheck() public view returns (uint256) {
        (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast) = uniswapPair.getReserves();

        // STALENESS CHECK: blockTimestampLast validation
        require(block.timestamp - blockTimestampLast <= STALENESS_THRESHOLD, "TWAP stale");

        return uint256(reserve0) * 1e18 / uint256(reserve1);
    }

    // =============================================================================
    // TRUE NEGATIVES: Oracle reads WITHOUT staleness checks (should NOT match)
    // =============================================================================

    /// @notice TN1: Oracle read without any staleness check
    /// @dev Pattern should NOT MATCH: missing has_staleness_check
    function getPriceUnchecked() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();

        // NO STALENESS CHECK - vulnerable
        return uint256(answer);
    }

    /// @notice TN2: Oracle read with only answer validation (no staleness)
    /// @dev Pattern should NOT MATCH: only checks answer > 0, no updatedAt
    function getPriceOnlyAnswerCheck() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();

        // Only answer check, NO STALENESS CHECK
        require(answer > 0, "Invalid price");

        return uint256(answer);
    }

    /// @notice TN3: Oracle read with unrelated require statements
    /// @dev Pattern should NOT MATCH: requires don't check staleness
    function getPriceWithUnrelatedChecks() public view returns (uint256) {
        require(msg.sender == owner, "Not owner");

        (
            ,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();

        require(answer > 1000, "Price too low"); // Business logic, not staleness

        return uint256(answer);
    }

    /// @notice TN4: No oracle read at all
    /// @dev Pattern should NOT MATCH: no READS_ORACLE operation
    function getPriceFromStorage() public view returns (uint256) {
        // No oracle call, just returns stored value
        return stalenessThreshold; // Not a price, just for testing
    }

    // =============================================================================
    // EDGE CASES
    // =============================================================================

    /// @notice EDGE1: View function with staleness check
    /// @dev Pattern should MATCH: view functions can have safe patterns too
    function viewPriceWithStaleness() external view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        require(block.timestamp - updatedAt <= STALENESS_THRESHOLD, "Stale");
        return uint256(answer);
    }

    /// @notice EDGE2: Pure function (no oracle access)
    /// @dev Pattern should NOT MATCH: no oracle read
    function calculatePrice(uint256 a, uint256 b) external pure returns (uint256) {
        return a * b;
    }

    /// @notice EDGE3: Oracle read in modifier (staleness check in modifier)
    /// @dev Pattern should MATCH if modifier analysis includes staleness check
    modifier withFreshPrice() {
        (
            ,
            ,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= STALENESS_THRESHOLD, "Stale");
        _;
    }

    function getPriceWithModifier() public view withFreshPrice returns (uint256) {
        (
            ,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();
        return uint256(answer);
    }

    /// @notice EDGE4: Staleness check with custom error
    /// @dev Pattern should MATCH: custom error instead of string
    error StalePrice(uint256 updatedAt, uint256 threshold);

    function getPriceWithCustomError() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        // STALENESS CHECK with custom error
        if (block.timestamp - updatedAt > STALENESS_THRESHOLD) {
            revert StalePrice(updatedAt, STALENESS_THRESHOLD);
        }

        return uint256(answer);
    }

    // =============================================================================
    // VARIATIONS: Different coding styles and naming conventions
    // =============================================================================

    /// @notice VAR1: Different variable naming (ts instead of updatedAt)
    /// @dev Pattern should MATCH: variation in naming
    function getPriceVariation1() public view returns (uint256) {
        (
            ,
            int256 price,
            ,
            uint256 ts, // timestamp

        ) = priceFeed.latestRoundData();

        require(block.timestamp - ts <= MAX_STALENESS, "Old data");
        return uint256(price);
    }

    /// @notice VAR2: Different operator (< instead of <=)
    /// @dev Pattern should MATCH: variation in comparison operator
    function getPriceVariation2() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        require(block.timestamp - updatedAt < STALENESS_THRESHOLD + 1, "Stale");
        return uint256(answer);
    }

    /// @notice VAR3: Hardcoded staleness threshold (no constant)
    /// @dev Pattern should MATCH: direct numeric comparison
    function getPriceVariation3() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        require(block.timestamp - updatedAt <= 3600, "Stale"); // 1 hour
        return uint256(answer);
    }

    /// @notice VAR4: Multiple staleness checks (redundant but safe)
    /// @dev Pattern should MATCH: multiple validations
    function getPriceVariation4() public view returns (uint256) {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        // Multiple staleness checks
        require(updatedAt > 0, "No data");
        require(block.timestamp - updatedAt <= STALENESS_THRESHOLD, "Too old");
        require(answeredInRound >= roundId, "Stale round");
        require(updatedAt > block.timestamp - 7200, "Very stale"); // 2 hours

        return uint256(answer);
    }

    /// @notice VAR5: Inverted staleness check (age < threshold)
    /// @dev Pattern should MATCH: mathematically equivalent check
    function getPriceVariation5() public view returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        uint256 age = block.timestamp - updatedAt;
        require(age < STALENESS_THRESHOLD, "Stale");

        return uint256(answer);
    }

    // =============================================================================
    // FALSE POSITIVE PREVENTION
    // =============================================================================

    /// @notice FP1: Function mentions "updatedAt" but doesn't check staleness
    /// @dev Pattern should NOT MATCH: updatedAt in event, not in require
    event PriceUpdated(uint256 price, uint256 updatedAt);

    function getPriceEmitsEvent() public returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        emit PriceUpdated(uint256(answer), updatedAt); // Not a staleness check

        return uint256(answer);
    }

    /// @notice FP2: Function sets updatedAt but doesn't validate it
    /// @dev Pattern should NOT MATCH: assignment, not validation
    uint256 public lastUpdatedAt;

    function getPriceStoresTimestamp() public returns (uint256) {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        lastUpdatedAt = updatedAt; // Storage, not validation

        return uint256(answer);
    }

    /// @notice FP3: Function checks roundId but not staleness
    /// @dev Pattern should MATCH: roundId is a staleness indicator
    function getPriceOnlyRoundIdCheck() public view returns (uint256) {
        (
            uint80 roundId,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();

        require(roundId > 0, "Invalid round");

        return uint256(answer);
    }

    // =============================================================================
    // ORACLE-003 VULNERABLE PATTERNS: Non-view functions WITHOUT staleness checks
    // =============================================================================

    /// @notice VULN1: State-changing liquidation WITHOUT staleness check - HIGH RISK
    /// @dev Pattern oracle-003 should MATCH: reads oracle, state-changing, no staleness check
    mapping(address => uint256) public collateralValue;

    function liquidateUser(address user) public {
        (
            ,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();

        // VULNERABLE: Uses oracle price for liquidation WITHOUT staleness check
        uint256 userCollateral = collateralValue[user];
        uint256 price = uint256(answer);

        // Business logic using potentially stale price
        if (userCollateral * price < 1000 ether) {
            // Execute liquidation with stale price
            collateralValue[user] = 0;
        }
    }

    /// @notice VULN2: State-changing borrow WITHOUT staleness check - HIGH RISK
    /// @dev Pattern oracle-003 should MATCH: reads oracle, state-changing, no staleness check
    mapping(address => uint256) public borrowedAmount;

    function borrow(uint256 collateralAmount) public {
        (
            ,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();

        // VULNERABLE: Uses oracle price for borrow limit WITHOUT staleness check
        uint256 price = uint256(answer);
        uint256 maxBorrow = (collateralAmount * price * 80) / 100; // 80% LTV

        borrowedAmount[msg.sender] = maxBorrow;
    }

    /// @notice VULN3: Internal state-changing function WITHOUT staleness check
    /// @dev Pattern oracle-003 should MATCH: internal, reads oracle, state-changing, no staleness check
    uint256 public storedPrice;

    function updateStoredPrice() internal {
        (
            ,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();

        // VULNERABLE: Stores oracle price WITHOUT staleness check
        storedPrice = uint256(answer);
    }

    function triggerPriceUpdate() public {
        updateStoredPrice();
    }

    /// @notice VULN4: Swap function WITHOUT staleness check - MEDIUM RISK
    /// @dev Pattern oracle-003 should MATCH: reads oracle, state-changing, no staleness check
    mapping(address => uint256) public tokenBalance;

    function swapAtOraclePrice(uint256 amount) public {
        (
            ,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();

        // VULNERABLE: Uses oracle price for swap WITHOUT staleness check
        uint256 price = uint256(answer);

        // Only validates answer > 0, no staleness validation
        require(answer > 0, "Invalid price");

        tokenBalance[msg.sender] = amount * price;
    }

    /// @notice VULN5: Fee calculation WITHOUT staleness check
    /// @dev Pattern oracle-003 should MATCH: reads oracle, state-changing, no staleness check
    uint256 public accruedFees;

    function calculateFees(uint256 amount) public {
        (
            ,
            int256 answer,
            ,
            ,

        ) = priceFeed.latestRoundData();

        // VULNERABLE: Uses oracle price for fees WITHOUT staleness check
        uint256 price = uint256(answer);

        // Unrelated checks only
        require(amount > 0, "Invalid amount");
        require(msg.sender != address(0), "Invalid sender");

        accruedFees += (amount * price) / 100;
    }

    /// @notice SAFE1: State-changing with staleness check - should NOT match oracle-003
    /// @dev Pattern oracle-003 should NOT MATCH: has staleness check
    function liquidateUserSafe(address user) public {
        (
            ,
            int256 answer,
            ,
            uint256 updatedAt,

        ) = priceFeed.latestRoundData();

        // SAFE: Staleness check present
        require(block.timestamp - updatedAt <= STALENESS_THRESHOLD, "Stale price");
        require(answer > 0, "Invalid price");

        uint256 userCollateral = collateralValue[user];
        uint256 price = uint256(answer);

        if (userCollateral * price < 1000 ether) {
            collateralValue[user] = 0;
        }
    }

    /// @notice SAFE2: State-changing with roundId check - should NOT match oracle-003
    /// @dev Pattern oracle-003 should NOT MATCH: has staleness check via roundId
    function borrowSafe(uint256 collateralAmount) public {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        // SAFE: answeredInRound staleness check
        require(answeredInRound >= roundId, "Stale round");
        require(updatedAt != 0, "Incomplete round");

        uint256 price = uint256(answer);
        uint256 maxBorrow = (collateralAmount * price * 80) / 100;

        borrowedAmount[msg.sender] = maxBorrow;
    }
}
