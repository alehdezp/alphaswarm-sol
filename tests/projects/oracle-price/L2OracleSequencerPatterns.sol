// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title L2OracleSequencerPatterns
 * @notice Test contract for oracle-004: L2 Oracle Read Without Sequencer Uptime Check
 *
 * This contract simulates L2 (Arbitrum, Optimism, Base) oracle usage patterns with
 * varying levels of sequencer uptime validation.
 *
 * Pattern Purpose:
 * Detect functions that read oracle prices on L2 networks WITHOUT validating sequencer
 * uptime status, allowing attackers to exploit stale prices after sequencer restart.
 *
 * Test Coverage:
 * - TRUE POSITIVES: Oracle reads WITHOUT sequencer checks
 * - TRUE NEGATIVES: Oracle reads WITH proper sequencer + grace period checks
 * - EDGE CASES: View functions, internal helpers, conditional checks
 * - VARIATIONS: Different sequencer check patterns, naming conventions
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

contract L2OracleSequencerPatterns {
    AggregatorV3Interface public priceFeed;
    AggregatorV3Interface public sequencerUptimeFeed;

    uint256 public constant GRACE_PERIOD_TIME = 1 hours;
    uint256 public stalenessThreshold = 1 hours;

    mapping(address => uint256) public deposits;
    mapping(address => uint256) public borrowedAmount;

    // Chainlink L2 Sequencer Uptime Feed addresses (for reference):
    // Arbitrum One: 0xFdB631F5EE196F0ed6FAa767959853A9F217697D
    // Optimism:     0x371EAD81c9102C9BF4874A9075FFFf170F2Ee389
    // Base:         0xBCF85224fc0756B9Fa45aA7892530B47e10b6433

    constructor(address _priceFeed, address _sequencerUptimeFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
        sequencerUptimeFeed = AggregatorV3Interface(_sequencerUptimeFeed);
    }

    // =========================================================================
    // TRUE POSITIVES - Oracle reads WITHOUT sequencer uptime check
    // =========================================================================

    /**
     * TP1: Basic vulnerable pattern - no sequencer check at all
     * SHOULD BE FLAGGED by oracle-004
     */
    function liquidateUser(address user) external {
        // VULNERABLE: Oracle read without sequencer check
        (, int256 price, , , ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");

        // Liquidation logic using potentially stale L2 price
        uint256 collateralValue = deposits[user] * uint256(price);
        uint256 debt = borrowedAmount[user];

        require(collateralValue < debt, "Position healthy");

        // Execute liquidation with stale price...
        deposits[user] = 0;
    }

    /**
     * TP2: Borrowing without sequencer check
     * SHOULD BE FLAGGED by oracle-004
     */
    function borrow(uint256 amount) external {
        // VULNERABLE: No sequencer uptime check
        (, int256 price, , , ) = priceFeed.latestRoundData();

        uint256 collateralValue = deposits[msg.sender] * uint256(price);
        require(collateralValue >= amount * 2, "Insufficient collateral");

        borrowedAmount[msg.sender] += amount;
    }

    /**
     * TP3: Swap execution without sequencer check
     * SHOULD BE FLAGGED by oracle-004
     */
    function swapAtOraclePrice(uint256 amountIn) external returns (uint256) {
        // VULNERABLE: Missing sequencer validation on L2
        (, int256 price, , , ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");

        // Execute swap at potentially stale L2 oracle price
        uint256 amountOut = amountIn * uint256(price) / 1e18;
        return amountOut;
    }

    /**
     * TP4: Collateral valuation without sequencer check
     * SHOULD BE FLAGGED by oracle-004
     */
    function getCollateralValue(address user) external returns (uint256) {
        // VULNERABLE: L2 oracle read, no sequencer check
        (, int256 price, , , ) = priceFeed.latestRoundData();

        return deposits[user] * uint256(price);
    }

    /**
     * TP5: Minting based on oracle price (no sequencer check)
     * SHOULD BE FLAGGED by oracle-004
     */
    function mintAgainstCollateral(uint256 collateralAmount) external {
        // VULNERABLE: Oracle price without sequencer uptime validation
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();

        // Has staleness check BUT missing sequencer check (insufficient for L2)
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        require(price > 0, "Invalid price");

        // Mint tokens based on potentially stale L2 price
        uint256 mintAmount = collateralAmount * uint256(price) / 1e18;
        deposits[msg.sender] += mintAmount;
    }

    /**
     * TP6: Internal state-changing function without sequencer check
     * SHOULD BE FLAGGED by oracle-004 (internal but state-changing)
     */
    function updateStoredPrice() internal {
        // VULNERABLE: Internal function reads oracle without sequencer check
        (, int256 price, , , ) = priceFeed.latestRoundData();

        // Store price in state (state-changing operation)
        deposits[address(this)] = uint256(price);
    }

    /**
     * TP7: Price calculation with only answer validation
     * SHOULD BE FLAGGED by oracle-004
     */
    function calculateLoanValue(address user) external returns (uint256) {
        // VULNERABLE: Only validates answer, not sequencer uptime
        (, int256 price, , , ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");

        return borrowedAmount[user] * uint256(price);
    }

    // =========================================================================
    // TRUE NEGATIVES - Oracle reads WITH proper sequencer checks
    // =========================================================================

    /**
     * TN1: Complete sequencer + grace period check (BEST PRACTICE)
     * SHOULD NOT BE FLAGGED by oracle-004
     */
    function liquidateUserSafe(address user) external {
        // SAFE: Full sequencer uptime + grace period validation
        _checkSequencerUptime();

        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");

        // Liquidation logic with safe L2 oracle price
        uint256 collateralValue = deposits[user] * uint256(price);
        uint256 debt = borrowedAmount[user];

        require(collateralValue < debt, "Position healthy");
        deposits[user] = 0;
    }

    /**
     * TN2: Borrowing with proper L2 sequencer validation
     * SHOULD NOT BE FLAGGED by oracle-004
     */
    function borrowSafe(uint256 amount) external {
        // SAFE: Sequencer uptime check before oracle read
        _checkSequencerUptime();

        (, int256 price, , , ) = priceFeed.latestRoundData();

        uint256 collateralValue = deposits[msg.sender] * uint256(price);
        require(collateralValue >= amount * 2, "Insufficient collateral");

        borrowedAmount[msg.sender] += amount;
    }

    /**
     * TN3: Inline sequencer check (embedded in function)
     * SHOULD NOT BE FLAGGED by oracle-004
     */
    function swapWithInlineSequencerCheck(uint256 amountIn) external returns (uint256) {
        // SAFE: Inline sequencer validation
        (, int256 seqAnswer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
        require(seqAnswer == 0, "Sequencer: down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Sequencer: grace period");

        // Now safe to read oracle price on L2
        (, int256 price, , , ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");

        uint256 amountOut = amountIn * uint256(price) / 1e18;
        return amountOut;
    }

    /**
     * TN4: Price fetch with comprehensive L2 checks
     * SHOULD NOT BE FLAGGED by oracle-004
     */
    function getPriceWithSequencerCheck() public view returns (uint256) {
        // SAFE: Sequencer uptime validation
        (, int256 seqAnswer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
        require(seqAnswer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period active");

        // Get oracle price with staleness check
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(block.timestamp - updatedAt <= stalenessThreshold, "Stale price");
        require(price > 0, "Invalid price");

        return uint256(price);
    }

    /**
     * TN5: Helper function with sequencer validation (used by callers)
     * SHOULD NOT BE FLAGGED by oracle-004
     */
    function _checkSequencerUptime() internal view {
        // SAFE: Dedicated sequencer uptime validation function
        (, int256 answer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();

        // Check 1: Sequencer is up (0 = up, 1 = down)
        require(answer == 0, "Sequencer: down");

        // Check 2: Grace period after restart (CRITICAL for L2)
        require(
            block.timestamp - startedAt > GRACE_PERIOD_TIME,
            "Sequencer: grace period active"
        );
    }

    /**
     * TN6: Alternative sequencer check naming convention
     * SHOULD NOT BE FLAGGED by oracle-004
     */
    function mintWithL2Validation(uint256 collateralAmount) external {
        // SAFE: Alternative naming for sequencer check
        _validateL2SequencerStatus();

        (, int256 price, , , ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");

        uint256 mintAmount = collateralAmount * uint256(price) / 1e18;
        deposits[msg.sender] += mintAmount;
    }

    function _validateL2SequencerStatus() internal view {
        // SAFE: Sequencer validation with different naming
        (, int256 status, uint256 uptimeStart, , ) = sequencerUptimeFeed.latestRoundData();
        require(status == 0, "L2 sequencer offline");
        require(block.timestamp - uptimeStart > GRACE_PERIOD_TIME, "L2 stabilization pending");
    }

    // =========================================================================
    // EDGE CASES
    // =========================================================================

    /**
     * EDGE1: View function without sequencer check
     * SHOULD NOT BE FLAGGED by oracle-004 (view functions excluded)
     */
    function viewOraclePrice() external view returns (uint256) {
        // View function - excluded from oracle-004 pattern
        // View functions are informational only, not exploitable in transactions
        (, int256 price, , , ) = priceFeed.latestRoundData();
        return uint256(price);
    }

    /**
     * EDGE2: Pure function (can't read oracle anyway)
     * SHOULD NOT BE FLAGGED by oracle-004
     */
    function calculatePriceImpact(uint256 amount, uint256 price) external pure returns (uint256) {
        // Pure function - no oracle read, excluded by design
        return amount * price / 1e18;
    }

    /**
     * EDGE3: Private helper that reads oracle (state-changing)
     * SHOULD BE FLAGGED by oracle-004 (private is subset of internal)
     */
    function _updateInternalPrice() private {
        // VULNERABLE: Private function reads oracle without sequencer check
        (, int256 price, , , ) = priceFeed.latestRoundData();
        deposits[address(0)] = uint256(price);
    }

    /**
     * EDGE4: Conditional L2 check (address(0) for L1 deployments)
     * SHOULD NOT BE FLAGGED by oracle-004 (has conditional sequencer check)
     */
    function getPriceMultiChain() external view returns (uint256) {
        // SAFE: Conditional sequencer check for multi-chain deployments
        if (address(sequencerUptimeFeed) != address(0)) {
            // L2 deployment: check sequencer
            (, int256 answer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
            require(answer == 0, "Sequencer down");
            require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");
        }
        // L1 deployment: skip sequencer check

        (, int256 price, , , ) = priceFeed.latestRoundData();
        return uint256(price);
    }

    // =========================================================================
    // VARIATION TESTS - Different naming conventions
    // =========================================================================

    /**
     * VAR1: 'controller' naming instead of 'admin'
     * SHOULD BE FLAGGED by oracle-004
     */
    function setCollateralRatio(uint256 ratio) external {
        // VULNERABLE: Oracle read without sequencer check (different naming context)
        (, int256 price, , , ) = priceFeed.latestRoundData();

        // Update collateral ratio based on price
        deposits[address(this)] = ratio * uint256(price);
    }

    /**
     * VAR2: 'getPrice' vs 'latestRoundData' naming
     * SHOULD BE FLAGGED by oracle-004
     */
    function updatePositionValue() external {
        // VULNERABLE: Using getPrice() wrapper (still reads oracle)
        uint256 currentPrice = _getOraclePrice();

        deposits[msg.sender] = currentPrice;
    }

    function _getOraclePrice() internal view returns (uint256) {
        // Wrapper around latestRoundData (still vulnerable)
        (, int256 price, , , ) = priceFeed.latestRoundData();
        return uint256(price);
    }

    /**
     * VAR3: Sequencer check with different validation order
     * SHOULD NOT BE FLAGGED by oracle-004
     */
    function borrowWithReorderedChecks(uint256 amount) external {
        // SAFE: Sequencer check exists (even if ordered differently)
        (, int256 price, , , ) = priceFeed.latestRoundData();

        // Sequencer check AFTER oracle read (still provides protection)
        _ensureSequencerHealthy();

        uint256 collateralValue = deposits[msg.sender] * uint256(price);
        require(collateralValue >= amount * 2, "Insufficient collateral");

        borrowedAmount[msg.sender] += amount;
    }

    function _ensureSequencerHealthy() internal view {
        // SAFE: Sequencer validation exists
        (, int256 answer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer unhealthy");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Too soon after restart");
    }

    /**
     * VAR4: Grace period only (no sequencer down check)
     * SHOULD BE FLAGGED by oracle-004 (incomplete sequencer check)
     */
    function getPriceGracePeriodOnly() external view returns (uint256) {
        // VULNERABLE: Only checks grace period, not sequencer status
        (, , uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period");
        // Missing: require(answer == 0) check

        (, int256 price, , , ) = priceFeed.latestRoundData();
        return uint256(price);
    }

    /**
     * VAR5: Sequencer status check only (no grace period)
     * Pattern might flag this depending on has_sequencer_uptime_check granularity
     */
    function getPriceStatusCheckOnly() external view returns (uint256) {
        // PARTIAL: Has sequencer down check but missing grace period (suboptimal)
        (, int256 answer, , , ) = sequencerUptimeFeed.latestRoundData();
        require(answer == 0, "Sequencer down");
        // Missing: grace period check (less critical but still a gap)

        (, int256 price, , , ) = priceFeed.latestRoundData();
        return uint256(price);
    }
}
