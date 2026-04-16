// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BlockTimestampManipulation
 * @notice VULNERABLE: Uses block.timestamp for critical logic
 *
 * Vulnerabilities:
 * - Miners/validators can manipulate block.timestamp +/- 15 seconds
 * - Can be used to win time-based lotteries
 * - Can manipulate auction end times
 * - Can affect time-locked vesting schedules
 *
 * Related CWEs:
 * - CWE-829: Inclusion of Functionality from Untrusted Control Sphere
 * - SWC-116: Block values as a proxy for time
 *
 * Safe uses:
 * - Approximate time checks (> 1 hour tolerance)
 * - Deadlines with grace periods
 *
 * Dangerous uses:
 * - Randomness generation
 * - Precise timing requirements
 * - Financial calculations based on exact time
 */

contract BlockTimestampManipulation {
    uint256 public lotteryEndTime;
    mapping(address => uint256) public lastRoll;

    constructor() {
        lotteryEndTime = block.timestamp + 1 days;
    }

    // VULNERABLE: Miner can manipulate to win
    function timestampLottery() external view returns (bool) {
        // Miner can adjust timestamp to make this true
        return block.timestamp % 10 == 0;
    }

    // VULNERABLE: Can manipulate cooldown
    function rollWithCooldown() external returns (uint256) {
        // Miner can adjust timestamp to bypass cooldown
        require(block.timestamp >= lastRoll[msg.sender] + 1 minutes, "Cooldown");
        lastRoll[msg.sender] = block.timestamp;

        return uint256(keccak256(abi.encodePacked(block.timestamp, msg.sender))) % 100;
    }

    // VULNERABLE: Precise timing can be gamed
    function claimIfExactTime(uint256 targetTime) external view returns (bool) {
        // Validator can adjust timestamp to match targetTime
        return block.timestamp == targetTime;
    }

    // Less vulnerable: Using block.timestamp for approximate time
    function hasVested() external view returns (bool) {
        // This is relatively safe as 1 day tolerance >> 15 seconds
        return block.timestamp >= lotteryEndTime;
    }
}
