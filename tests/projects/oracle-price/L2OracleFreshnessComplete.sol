// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title L2OracleFreshnessComplete
 * @notice Test contract for oracle-006: L2 Oracle With Complete Freshness Validation (Safe Pattern)
 * @dev This pattern identifies GOLD STANDARD L2 oracle integration:
 *      - Oracle reads WITH BOTH staleness check AND sequencer uptime check
 *      - This is a SAFE PATTERN (info severity)
 *      - True Positives = Functions with BOTH checks (production-grade)
 *      - True Negatives = Functions missing one or both checks (incomplete)
 */

interface AggregatorV3Interface {
    function latestRoundData()
        external
        view
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        );
}

contract L2OracleFreshnessComplete {
    AggregatorV3Interface public priceFeed;
    AggregatorV3Interface public sequencerUptimeFeed;

    uint256 public constant GRACE_PERIOD_TIME = 1 hours;
    uint256 public stalenessThreshold = 1 hours;
    uint256 public storedPrice;

    // =============================================================================
    // TRUE POSITIVES - Functions WITH BOTH staleness AND sequencer checks (SAFE)
    // =============================================================================

    /// @notice TP1: Standard production-grade L2 oracle integration
    /// @dev BOTH sequencer uptime check AND staleness check present (gold standard)
    function getPriceProductionGrade() public view returns (uint256) {
        // LAYER 1: Sequencer uptime check
        (
            /*uint80 roundId*/,
            int256 answer,
            uint256 startedAt,
            /*uint256 updatedAt*/,
            /*uint80 answeredInRound*/
        ) = sequencerUptimeFeed.latestRoundData();

        require(answer == 0, "Sequencer: down");
        require(
            block.timestamp - startedAt > GRACE_PERIOD_TIME,
            "Sequencer: grace period"
        );

        // LAYER 2: Staleness check
        (
            uint80 roundId,
            int256 price,
            /*uint256 startedAt*/,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        require(updatedAt != 0, "Oracle: incomplete round");
        require(
            block.timestamp - updatedAt <= stalenessThreshold,
            "Oracle: stale price"
        );
        require(answeredInRound >= roundId, "Oracle: stale round");

        return uint256(price);
    }

    /// @notice TP2: Inline sequencer check with both validations
    /// @dev Both checks present inline, no helper delegation
    function getPriceInlineChecks() public view returns (uint256) {
        // Sequencer check inline
        (,int256 seqAnswer, uint256 seqStartedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(seqAnswer == 0, "Sequencer down");
        require(block.timestamp - seqStartedAt > GRACE_PERIOD_TIME, "Grace period");

        // Staleness check inline
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        return uint256(price);
    }

    /// @notice TP3: Critical operation (liquidation) with both checks
    /// @dev Production-grade liquidation with full L2 validation
    function liquidateUserSafe(address user) external returns (bool) {
        // Sequencer validation
        (,int256 ans, uint256 started,,) = sequencerUptimeFeed.latestRoundData();
        require(ans == 0, "Sequencer down");
        require(block.timestamp - started > GRACE_PERIOD_TIME, "Grace period");

        // Staleness validation
        (uint80 rId, int256 price,, uint256 upAt, uint80 ansRound) = priceFeed.latestRoundData();
        require(upAt != 0, "Incomplete");
        require(block.timestamp - upAt <= stalenessThreshold, "Stale");
        require(ansRound >= rId, "Stale round");

        // Liquidation logic
        uint256 collateralValue = uint256(price);
        require(collateralValue > 0, "Invalid price");

        return true;
    }

    /// @notice TP4: Borrow operation with both checks
    /// @dev BOTH layers of validation before critical borrow
    function borrowSafe(uint256 amount) external returns (bool) {
        // Layer 1: Sequencer
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer: down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Sequencer: grace");

        // Layer 2: Staleness
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Oracle: incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Oracle: stale");
        require(answeredInRound >= roundId, "Oracle: stale round");

        // Borrow logic
        require(amount > 0, "Invalid amount");
        return true;
    }

    /// @notice TP5: Swap with complete L2 validation
    /// @dev MEV-sensitive operation with gold standard checks
    function swapWithCompleteValidation(uint256 amountIn) external returns (uint256) {
        // Sequencer uptime + grace period
        (,int256 seqStatus, uint256 seqStart,,) = sequencerUptimeFeed.latestRoundData();
        require(seqStatus == 0, "Seq down");
        require(block.timestamp - seqStart > GRACE_PERIOD_TIME, "Grace period");

        // Oracle staleness
        (uint80 rid, int256 oraclePrice,, uint256 upAt, uint80 aRound) = priceFeed.latestRoundData();
        require(upAt != 0, "Incomplete");
        require(block.timestamp - upAt <= stalenessThreshold, "Stale");
        require(aRound >= rid, "Stale round");

        return uint256(oraclePrice) * amountIn;
    }

    /// @notice TP6: Alternative naming - controller instead of owner
    /// @dev Tests variation in naming conventions
    function getCollateralValueComplete(address token) public view returns (uint256) {
        // Validate sequencer
        (,int256 sequencerAnswer, uint256 sequencerStartedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(sequencerAnswer == 0, "Sequencer offline");
        require(block.timestamp - sequencerStartedAt > GRACE_PERIOD_TIME, "Sequencer grace");

        // Validate oracle
        (uint80 roundId, int256 answer,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Oracle incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Oracle stale");
        require(answeredInRound >= roundId, "Oracle stale round");

        return uint256(answer);
    }

    /// @notice TP7: Multiple oracle reads with both checks
    /// @dev Aggregates multiple oracle sources, all with full validation
    function getAveragePriceWithFullValidation() public view returns (uint256) {
        // Sequencer check (once for all oracle reads)
        (,int256 ans, uint256 start,,) = sequencerUptimeFeed.latestRoundData();
        require(ans == 0, "Seq down");
        require(block.timestamp - start > GRACE_PERIOD_TIME, "Grace");

        // Oracle 1 with staleness
        (uint80 rid1, int256 p1,, uint256 up1, uint80 ar1) = priceFeed.latestRoundData();
        require(up1 != 0, "Inc1");
        require(block.timestamp - up1 <= stalenessThreshold, "Stale1");
        require(ar1 >= rid1, "StaleR1");

        // Oracle 2 with staleness (would be different feed in practice)
        (uint80 rid2, int256 p2,, uint256 up2, uint80 ar2) = priceFeed.latestRoundData();
        require(up2 != 0, "Inc2");
        require(block.timestamp - up2 <= stalenessThreshold, "Stale2");
        require(ar2 >= rid2, "StaleR2");

        return (uint256(p1) + uint256(p2)) / 2;
    }

    /// @notice TP8: State-changing internal function with both checks
    /// @dev Internal function that writes state, has both validations
    function updateStoredPriceSafe() internal {
        // Sequencer validation
        (,int256 seqAnswer, uint256 seqStartedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(seqAnswer == 0, "Sequencer down");
        require(block.timestamp - seqStartedAt > GRACE_PERIOD_TIME, "Grace period");

        // Staleness validation
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        storedPrice = uint256(price);
    }

    /// @notice TP9: Multi-chain compatible with conditional sequencer check
    /// @dev Has BOTH checks, but sequencer check is conditional for L1/L2 compatibility
    function getPriceMultiChain() public view returns (uint256) {
        // Conditional sequencer check (address(0) for L1 deployments)
        if (address(sequencerUptimeFeed) != address(0)) {
            (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
            require(answer == 0, "Sequencer down");
            require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");
        }

        // Staleness check (always present for L1 + L2)
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        return uint256(price);
    }

    /// @notice TP10: Reordered checks (staleness before sequencer)
    /// @dev Both checks present, but different ordering (still safe)
    function getPriceReorderedChecks() public view returns (uint256) {
        // Staleness check first (non-standard but valid)
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        // Sequencer check second (works but less gas-efficient)
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");

        return uint256(price);
    }

    // =============================================================================
    // TRUE NEGATIVES - Missing one or both checks (INCOMPLETE/VULNERABLE)
    // =============================================================================

    /// @notice TN1: ONLY staleness check, missing sequencer check (L2 VULNERABLE)
    /// @dev Should NOT match oracle-006 - missing sequencer uptime check
    function getPriceOnlyStalenessCheck() public view returns (uint256) {
        // Staleness check present ✅
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        // Sequencer check MISSING ❌

        return uint256(price);
    }

    /// @notice TN2: ONLY sequencer check, missing staleness check (VULNERABLE)
    /// @dev Should NOT match oracle-006 - missing staleness validation
    function getPriceOnlySequencerCheck() public view returns (uint256) {
        // Sequencer check present ✅
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");

        // Staleness check MISSING ❌
        (,int256 price,,,) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");  // Only answer validation, no staleness

        return uint256(price);
    }

    /// @notice TN3: NO checks at all (CRITICALLY VULNERABLE)
    /// @dev Should NOT match oracle-006 - missing both checks
    function getPriceUnchecked() public view returns (uint256) {
        // No sequencer check ❌
        // No staleness check ❌
        (,int256 price,,,) = priceFeed.latestRoundData();
        return uint256(price);
    }

    /// @notice TN4: Liquidation without sequencer check (L2 VULNERABLE)
    /// @dev Should NOT match oracle-006 - missing sequencer validation
    function liquidateUserNoSequencer(address user) external returns (bool) {
        // Staleness check present ✅
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        // Sequencer check MISSING ❌

        uint256 collateralValue = uint256(price);
        require(collateralValue > 0, "Invalid");
        return true;
    }

    /// @notice TN5: Borrow without staleness check (VULNERABLE)
    /// @dev Should NOT match oracle-006 - missing staleness validation
    function borrowNoStaleness(uint256 amount) external returns (bool) {
        // Sequencer check present ✅
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");

        // Staleness check MISSING ❌
        (,int256 price,,,) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");

        require(amount > 0, "Invalid amount");
        return true;
    }

    /// @notice TN6: No oracle read at all
    /// @dev Should NOT match oracle-006 - no oracle interaction
    function getPriceFromStorage() public view returns (uint256) {
        return storedPrice;  // No oracle read, no checks needed
    }

    /// @notice TN7: Sequencer status check only, missing grace period
    /// @dev Should NOT match oracle-006 - missing grace period validation
    function getPriceSequencerStatusOnly() public view returns (uint256) {
        // Sequencer status check (no grace period) ⚠️
        (,int256 answer,,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        // Missing: block.timestamp - startedAt > GRACE_PERIOD_TIME

        // Staleness check present ✅
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        return uint256(price);
    }

    /// @notice TN8: Partial staleness check (updatedAt only, missing roundId check)
    /// @dev Should NOT match if pattern requires answeredInRound check
    function getPricePartialStaleness() public view returns (uint256) {
        // Sequencer check present ✅
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");

        // Partial staleness check (missing answeredInRound validation) ⚠️
        (,int256 price,, uint256 updatedAt,) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        // Missing: require(answeredInRound >= roundId)

        return uint256(price);
    }

    // =============================================================================
    // EDGE CASES
    // =============================================================================

    /// @notice EDGE1: View function with both checks
    /// @dev View functions should still match if they have both checks
    function viewPriceWithBothChecks() public view returns (uint256) {
        // Sequencer check
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");

        // Staleness check
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        return uint256(price);
    }

    /// @notice EDGE2: Pure function (no oracle access)
    /// @dev Should NOT match - no oracle read
    function calculatePrice(uint256 amount, uint256 rate) public pure returns (uint256) {
        return amount * rate;
    }

    /// @notice EDGE3: Private function with both checks
    /// @dev Private functions should match if state-changing and have both checks
    function _getPricePrivate() private view returns (uint256) {
        // Sequencer check
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");

        // Staleness check
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");

        return uint256(price);
    }

    /// @notice EDGE4: Both checks delegated to helpers
    /// @dev Tests if pattern can detect checks in helper functions
    function getPriceViaHelpers() public view returns (uint256) {
        _checkSequencerUptime();
        return _getPriceWithStalenessCheck();
    }

    function _checkSequencerUptime() internal view {
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");
    }

    function _getPriceWithStalenessCheck() internal view returns (uint256) {
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale");
        require(answeredInRound >= roundId, "Stale round");
        return uint256(price);
    }

    // =============================================================================
    // VARIATIONS - Different implementations and naming
    // =============================================================================

    /// @notice VAR1: Different variable naming (ts instead of updatedAt)
    /// @dev Tests if pattern is resilient to variable naming changes
    function getPriceVariation1() public view returns (uint256) {
        // Sequencer check
        (,int256 ans, uint256 start,,) = sequencerUptimeFeed.latestRoundData();
        require(ans == 0, "Down");
        require(block.timestamp - start > GRACE_PERIOD_TIME, "Grace");

        // Staleness with different variable names
        (uint80 rid, int256 p,, uint256 ts, uint80 aRound) = priceFeed.latestRoundData();
        require(ts != 0, "Inc");
        require(block.timestamp - ts <= stalenessThreshold, "Stale");
        require(aRound >= rid, "StaleR");

        return uint256(p);
    }

    /// @notice VAR2: Hardcoded thresholds instead of constants
    /// @dev Tests pattern with inline threshold values
    function getPriceVariation2() public view returns (uint256) {
        // Sequencer with hardcoded grace period
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > 3600, "Grace period");  // Hardcoded 1 hour

        // Staleness with hardcoded threshold
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(block.timestamp - updatedAt <= 3600, "Stale");  // Hardcoded 1 hour
        require(answeredInRound >= roundId, "Stale round");

        return uint256(price);
    }

    /// @notice VAR3: Alternative comparison operators
    /// @dev Tests < vs <= variations
    function getPriceVariation3() public view returns (uint256) {
        // Sequencer check
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp > startedAt + GRACE_PERIOD_TIME, "Grace");  // > instead of -

        // Staleness check
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(updatedAt != 0, "Incomplete");
        require(updatedAt + stalenessThreshold >= block.timestamp, "Stale");  // Inverted
        require(answeredInRound >= roundId, "Stale round");

        return uint256(price);
    }

    /// @notice VAR4: Compact checks (single require with &&)
    /// @dev Tests if pattern detects combined require statements
    function getPriceVariation4() public view returns (uint256) {
        // Compact sequencer check
        (,int256 answer, uint256 startedAt,,) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0 && block.timestamp - startedAt > GRACE_PERIOD_TIME, "Sequencer");

        // Compact staleness check
        (uint80 roundId, int256 price,, uint256 updatedAt, uint80 answeredInRound) = priceFeed.latestRoundData();
        require(
            updatedAt != 0 &&
            block.timestamp - updatedAt <= stalenessThreshold &&
            answeredInRound >= roundId,
            "Oracle"
        );

        return uint256(price);
    }
}
