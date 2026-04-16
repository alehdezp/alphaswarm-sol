// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MEVTimestampDependence
 * @notice Demonstrates timestamp manipulation vulnerabilities for MEV extraction
 *
 * Functions that rely on block.timestamp for critical logic
 * can be manipulated by validators/miners within ~15 second window.
 *
 * Timestamp Manipulation for MEV:
 * 1. Validator can set block.timestamp within consensus rules (~15s drift)
 * 2. If timestamp determines pricing, fees, or access, validator can optimize
 * 3. Validator chooses timestamp that maximizes their MEV extraction
 * 4. On L2s with centralized sequencers, manipulation window may be larger
 *
 * Examples:
 * - Time-weighted pricing can be skewed
 * - Deadline checks can be bypassed
 * - Time-based unlocks can be delayed/accelerated
 * - Dutch auctions can be manipulated
 *
 * Related: Timeboost on Arbitrum (April 2025), revert-based MEV on L2s
 */
contract MEVTimestampDependence {
    uint256 public startPrice;
    uint256 public endPrice;
    uint256 public startTime;
    uint256 public duration;

    constructor(uint256 _startPrice, uint256 _endPrice, uint256 _duration) {
        startPrice = _startPrice;
        endPrice = _endPrice;
        startTime = block.timestamp;
        duration = _duration;
    }

    // VULNERABLE: Dutch auction price depends on block.timestamp
    // Validator can choose timestamp to get optimal price
    function getCurrentPrice() public view returns (uint256) {
        if (block.timestamp >= startTime + duration) {
            return endPrice;
        }

        // Price decreases linearly over time
        uint256 elapsed = block.timestamp - startTime;
        uint256 priceDecrease = (startPrice - endPrice) * elapsed / duration;

        // VULNERABLE: Validator controls block.timestamp within limits
        // Can delay block to get lower price or accelerate to keep price high
        return startPrice - priceDecrease;
    }

    // VULNERABLE: Time-based access control
    function timeLockedWithdraw(uint256 unlockTime) external view returns (bool) {
        // VULNERABLE: Validator can delay block to prevent withdrawal
        // or accelerate to allow early withdrawal
        require(block.timestamp >= unlockTime, "still locked");
        return true;
    }

    // VULNERABLE: Time-weighted average price calculation
    function calculateTWAP(uint256 price0, uint256 price1, uint256 time0) external view returns (uint256) {
        uint256 time1 = block.timestamp;
        uint256 timeElapsed = time1 - time0;

        // VULNERABLE: timeElapsed can be manipulated by validator
        // Choosing block timestamp affects the TWAP calculation
        return (price0 + price1) / 2; // Simplified
    }

    // VULNERABLE: Rebasing based on time
    function rebase() external view returns (uint256) {
        uint256 timeSinceLastRebase = block.timestamp - startTime;

        // VULNERABLE: Validator timing affects rebase amount
        return timeSinceLastRebase * 100; // Simplified rebase calculation
    }
}
