// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title L2OraclePartialProtection
 * @notice Test contract for oracle-007: Staleness Check Without Sequencer Uptime Check (L2 Risk)
 *
 * This contract simulates PARTIAL PROTECTION scenarios on L2 networks where oracle reads
 * implement staleness checks (good!) but MISS sequencer uptime validation (incomplete!).
 *
 * Pattern Purpose (oracle-007):
 * Detect functions that have staleness checks (better than oracle-003) BUT are still
 * vulnerable on L2 networks due to missing sequencer uptime validation.
 *
 * Test Coverage:
 * - TRUE POSITIVES: Oracle reads WITH staleness check BUT WITHOUT sequencer check (vulnerable on L2)
 * - TRUE NEGATIVES: Oracle reads WITH BOTH checks (oracle-006) OR missing BOTH (oracle-003)
 * - EDGE CASES: View functions, internal helpers, various check implementations
 * - VARIATIONS: Different staleness check patterns, naming conventions, visibility levels
 */

interface AggregatorV3Interface {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

contract L2OraclePartialProtection {
    AggregatorV3Interface public priceFeed;
    AggregatorV3Interface public sequencerUptimeFeed;

    uint256 public constant GRACE_PERIOD_TIME = 1 hours;
    uint256 public stalenessThreshold = 1 hours;

    mapping(address => uint256) public deposits;
    mapping(address => uint256) public borrowedAmount;
    mapping(address => uint256) public collateralRatio;

    uint256 public storedPrice;

    constructor(address _priceFeed, address _sequencerUptimeFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
        sequencerUptimeFeed = AggregatorV3Interface(_sequencerUptimeFeed);
    }

    // =========================================================================
    // TRUE POSITIVES - Staleness check present, sequencer check MISSING
    // =========================================================================

    /**
     * TP1: Standard staleness check WITHOUT sequencer check (PARTIAL PROTECTION)
     * SHOULD BE FLAGGED by oracle-007
     */
    function liquidateUser(address user) external {
        // VULNERABLE: Has staleness check (good) but missing sequencer check (bad on L2)
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        // Missing: sequencer uptime + grace period check

        // Liquidation logic - vulnerable to post-sequencer-restart stale prices
        uint256 collateralValue = deposits[user] * uint256(price);
        uint256 debt = borrowedAmount[user];

        require(collateralValue < debt, "Position healthy");
        deposits[user] = 0;
    }

    /**
     * TP2: Borrowing with staleness check only (PARTIAL PROTECTION)
     * SHOULD BE FLAGGED by oracle-007
     */
    function borrow(uint256 amount) external {
        // VULNERABLE: Staleness check present but no sequencer validation
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        require(price > 0, "Invalid price");

        uint256 collateralValue = deposits[msg.sender] * uint256(price);
        require(collateralValue >= amount * 2, "Insufficient collateral");

        borrowedAmount[msg.sender] += amount;
    }

    /**
     * TP3: Swap with staleness check but missing sequencer check
     * SHOULD BE FLAGGED by oracle-007
     */
    function swapAtOraclePrice(uint256 amountIn) external returns (uint256) {
        // VULNERABLE: Has updatedAt check but no sequencer uptime validation
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete round");
        require(block.timestamp - updatedAt <= 1 hours, "Stale price");

        uint256 amountOut = amountIn * uint256(price) / 1e18;
        return amountOut;
    }

    /**
     * TP4: Collateral valuation with comprehensive staleness check (STILL VULNERABLE on L2)
     * SHOULD BE FLAGGED by oracle-007
     */
    function getCollateralValue(address user) external returns (uint256) {
        // VULNERABLE: Multiple staleness checks but NO sequencer validation
        (
            uint80 roundId,
            int256 price,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        // Comprehensive staleness validation (best practice for L1)
        require(updatedAt != 0, "Incomplete round");
        require(price > 0, "Invalid price");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        require(answeredInRound >= roundId, "Stale round");
        // BUT STILL MISSING: sequencer uptime check (critical for L2)

        return deposits[user] * uint256(price);
    }

    /**
     * TP5: Minting with staleness check via helper function
     * SHOULD BE FLAGGED by oracle-007
     */
    function mintAgainstCollateral(uint256 collateralAmount) external {
        // VULNERABLE: Delegates to staleness check helper but no sequencer check
        uint256 price = _getPriceWithStalenessCheck();

        uint256 mintAmount = collateralAmount * price / 1e18;
        deposits[msg.sender] += mintAmount;
    }

    function _getPriceWithStalenessCheck() internal view returns (uint256) {
        // Has staleness check but missing sequencer validation
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        return uint256(price);
    }

    /**
     * TP6: Internal state-changing function with staleness check
     * SHOULD BE FLAGGED by oracle-007 (internal but state-changing)
     */
    function updateStoredPrice() internal {
        // VULNERABLE: Internal function with staleness check but no sequencer check
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");

        storedPrice = uint256(price);
    }

    /**
     * TP7: Alternative staleness check pattern (hardcoded threshold)
     * SHOULD BE FLAGGED by oracle-007
     */
    function calculateLoanValue(address user) external returns (uint256) {
        // VULNERABLE: Hardcoded staleness threshold, missing sequencer check
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= 3600, "Stale price"); // 1 hour hardcoded

        return borrowedAmount[user] * uint256(price);
    }

    /**
     * TP8: Staleness check with updatedAt != 0 validation
     * SHOULD BE FLAGGED by oracle-007
     */
    function setPriceBasedFee(uint256 baseAmount) external {
        // VULNERABLE: updatedAt validation but no sequencer check
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete round");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");

        deposits[msg.sender] = baseAmount * uint256(price);
    }

    /**
     * TP9: answeredInRound staleness check (but missing sequencer check)
     * SHOULD BE FLAGGED by oracle-007
     */
    function updateCollateralRatio(uint256 ratio) external {
        // VULNERABLE: Has answeredInRound check but no sequencer validation
        (
            uint80 roundId,
            int256 price,
            ,
            ,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();
        require(answeredInRound >= roundId, "Stale round");
        require(price > 0, "Invalid price");

        collateralRatio[msg.sender] = ratio * uint256(price);
    }

    /**
     * TP10: Public wrapper calling internal staleness check
     * SHOULD BE FLAGGED by oracle-007
     */
    function mintTokens(uint256 collateralAmount) public returns (uint256) {
        // VULNERABLE: Calls internal staleness check, no sequencer validation
        uint256 price = _getStalenessCheckedPrice();

        uint256 mintAmount = collateralAmount * price / 1e18;
        deposits[msg.sender] += mintAmount;
        return mintAmount;
    }

    function _getStalenessCheckedPrice() private view returns (uint256) {
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        return uint256(price);
    }

    // =========================================================================
    // TRUE NEGATIVES - COMPLETE protection (oracle-006) or NO checks (oracle-003)
    // =========================================================================

    /**
     * TN1: COMPLETE L2 protection - BOTH staleness AND sequencer checks
     * SHOULD NOT BE FLAGGED by oracle-007 (this is oracle-006 - gold standard)
     */
    function liquidateUserSafe(address user) external {
        // SAFE: Both staleness AND sequencer checks present
        _checkSequencerUptime(); // Sequencer + grace period

        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");

        // Now safe to use price on L2
        uint256 collateralValue = deposits[user] * uint256(price);
        uint256 debt = borrowedAmount[user];

        require(collateralValue < debt, "Position healthy");
        deposits[user] = 0;
    }

    function _checkSequencerUptime() internal view {
        (, int256 answer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer: down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Sequencer: grace period");
    }

    /**
     * TN2: NO checks at all (this is oracle-003 territory, not oracle-007)
     * SHOULD NOT BE FLAGGED by oracle-007 (requires staleness check to match)
     */
    function borrowUnchecked(uint256 amount) external {
        // NO checks at all - oracle-003 should flag this, not oracle-007
        (, int256 price, , , ) = priceFeed.latestRoundData();

        uint256 collateralValue = deposits[msg.sender] * uint256(price);
        borrowedAmount[msg.sender] += amount;
    }

    /**
     * TN3: Inline BOTH checks (complete L2 protection)
     * SHOULD NOT BE FLAGGED by oracle-007
     */
    function swapWithCompleteChecks(uint256 amountIn) external returns (uint256) {
        // SAFE: Inline sequencer check
        (, int256 seqAnswer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
        require(seqAnswer == 0, "Sequencer: down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Sequencer: grace period");

        // SAFE: Staleness check
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");

        return amountIn * uint256(price) / 1e18;
    }

    /**
     * TN4: Only answer validation (no staleness, no sequencer)
     * SHOULD NOT BE FLAGGED by oracle-007 (missing staleness check)
     */
    function calculateValueUnsafe(address user) external returns (uint256) {
        // NO CHECKS except answer > 0 - oracle-003 should flag this
        (, int256 price, , , ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");

        return deposits[user] * uint256(price);
    }

    /**
     * TN5: Comprehensive validation (oracle-006 pattern)
     * SHOULD NOT BE FLAGGED by oracle-007
     */
    function getPriceProductionGrade() external view returns (uint256) {
        // SAFE: Sequencer uptime check
        (, int256 seqAnswer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
        require(seqAnswer == 0, "Sequencer: down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");

        // SAFE: Comprehensive staleness checks
        (
            uint80 roundId,
            int256 price,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        require(updatedAt != 0, "Incomplete round");
        require(price > 0, "Invalid price");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        require(answeredInRound >= roundId, "Stale round");

        return uint256(price);
    }

    // =========================================================================
    // EDGE CASES
    // =========================================================================

    /**
     * EDGE1: View function with staleness check only
     * SHOULD NOT BE FLAGGED by oracle-007 (view functions excluded)
     */
    function viewPriceWithStaleness() external view returns (uint256) {
        // View function - excluded by pattern (is_view = true)
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        return uint256(price);
    }

    /**
     * EDGE2: Pure function (can't read oracle)
     * SHOULD NOT BE FLAGGED by oracle-007
     */
    function calculatePriceImpact(uint256 amount, uint256 price) external pure returns (uint256) {
        // Pure function - no oracle read
        return amount * price / 1e18;
    }

    /**
     * EDGE3: Private function with staleness check only
     * SHOULD BE FLAGGED by oracle-007 (private but state-changing)
     */
    function _updatePricePrivate() private {
        // VULNERABLE: Private function with staleness check, no sequencer check
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");

        storedPrice = uint256(price);
    }

    /**
     * EDGE4: Internal view helper with staleness check
     * SHOULD NOT BE FLAGGED by oracle-007 (internal + view = read-only)
     */
    function _getPriceView() internal view returns (uint256) {
        // Internal view - excluded (is_view = true)
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        return uint256(price);
    }

    /**
     * EDGE5: Staleness check with zero address sequencer feed (multi-chain)
     * SHOULD BE FLAGGED by oracle-007 (L2 deployment should have sequencer feed)
     */
    function getPriceConditional() external view returns (uint256) {
        // VULNERABLE on L2: Staleness check but conditional sequencer skipped
        // If sequencerUptimeFeed is address(0), this behaves like oracle-007
        if (address(sequencerUptimeFeed) != address(0)) {
            // Has sequencer check - would be safe
            (, int256 answer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
            require(answer == 0, "Sequencer down");
            require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");
        }

        // Staleness check present
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");

        return uint256(price);
    }

    // =========================================================================
    // VARIATION TESTS - Different staleness check patterns
    // =========================================================================

    /**
     * VAR1: Hardcoded staleness threshold (3600 seconds)
     * SHOULD BE FLAGGED by oracle-007
     */
    function getPriceHardcodedThreshold() external returns (uint256) {
        // VULNERABLE: Hardcoded threshold, missing sequencer
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= 3600, "Stale price");

        deposits[msg.sender] = uint256(price);
        return uint256(price);
    }

    /**
     * VAR2: Alternative comparison operator (>=)
     * SHOULD BE FLAGGED by oracle-007
     */
    function getPriceAltOperator() external returns (uint256) {
        // VULNERABLE: Alternative operator, missing sequencer
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(updatedAt >= block.timestamp - stalenessThreshold, "Stale price");

        deposits[msg.sender] = uint256(price);
        return uint256(price);
    }

    /**
     * VAR3: Staleness check with age variable
     * SHOULD BE FLAGGED by oracle-007
     */
    function getPriceWithAge() external returns (uint256) {
        // VULNERABLE: Uses age variable, missing sequencer
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        uint256 age = block.timestamp - updatedAt;
        require(age <= stalenessThreshold, "Stale price");

        deposits[msg.sender] = uint256(price);
        return uint256(price);
    }

    /**
     * VAR4: Different naming for oracle call
     * SHOULD BE FLAGGED by oracle-007
     */
    function updatePrice() external {
        // VULNERABLE: Different naming, staleness check present, no sequencer
        uint256 freshPrice = _fetchFreshPrice();
        storedPrice = freshPrice;
    }

    function _fetchFreshPrice() internal view returns (uint256) {
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        return uint256(price);
    }

    /**
     * VAR5: Multiple staleness checks (updatedAt + answeredInRound)
     * SHOULD BE FLAGGED by oracle-007
     */
    function getPriceDoubleCheck() external returns (uint256) {
        // VULNERABLE: Multiple staleness checks, still missing sequencer
        (
            uint80 roundId,
            int256 price,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale updatedAt");
        require(answeredInRound >= roundId, "Stale answeredInRound");

        deposits[msg.sender] = uint256(price);
        return uint256(price);
    }

    /**
     * VAR6: Staleness check in require with multiple conditions
     * SHOULD BE FLAGGED by oracle-007
     */
    function getPriceCompactCheck() external returns (uint256) {
        // VULNERABLE: Compact staleness check, missing sequencer
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(
            price > 0 && block.timestamp - updatedAt <= stalenessThreshold,
            "Invalid or stale price"
        );

        deposits[msg.sender] = uint256(price);
        return uint256(price);
    }
}
