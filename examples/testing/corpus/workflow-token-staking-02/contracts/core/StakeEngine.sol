// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IStakeEngine.sol";
import "../libraries/RewardCalc.sol";

/// @title StakeEngine - Token staking with time-weighted rewards
contract StakeEngine is IStakeEngine {
    using RewardCalc for uint256;

    struct StakeInfo {
        uint256 amount;
        uint256 startTime;
        uint256 rewardDebt;
    }

    mapping(address => StakeInfo) public stakes;
    uint256 public totalStaked;
    uint256 public rewardRate; // rewards per second per token
    address public admin;
    bool public paused;

    constructor(uint256 _rewardRate) {
        admin = msg.sender;
        rewardRate = _rewardRate;
    }

    /// @notice Stake tokens
    function stake() external payable override {
        require(msg.value > 0, "Zero stake");
        require(!paused, "Paused");

        StakeInfo storage info = stakes[msg.sender];
        if (info.amount > 0) {
            uint256 pending = info.amount.pendingReward(
                info.startTime, rewardRate
            );
            info.rewardDebt += pending;
        }
        info.amount += msg.value;
        info.startTime = block.timestamp;
        totalStaked += msg.value;

        emit Staked(msg.sender, msg.value);
    }

    /// @notice Unstake and claim rewards
    /// @dev VULNERABILITY: Reentrancy via external call before state update
    function unstake(uint256 amount) external override {
        StakeInfo storage info = stakes[msg.sender];
        require(info.amount >= amount, "Insufficient stake");

        uint256 reward = info.amount.pendingReward(info.startTime, rewardRate)
            + info.rewardDebt;
        uint256 payout = amount + reward;

        // External call before state update
        (bool ok, ) = msg.sender.call{value: payout}("");
        require(ok, "Unstake failed");

        info.amount -= amount;
        info.rewardDebt = 0;
        info.startTime = block.timestamp;
        totalStaked -= amount;

        emit Unstaked(msg.sender, amount, reward);
    }

    /// @notice View pending rewards
    function pendingRewards(address user) external view override returns (uint256) {
        StakeInfo memory info = stakes[user];
        return info.amount.pendingReward(info.startTime, rewardRate) + info.rewardDebt;
    }

    /// @notice Pause staking
    /// @dev VULNERABILITY: No access control on pause
    function togglePause() external {
        paused = !paused;
    }

    /// @notice Update reward rate
    /// @dev VULNERABILITY: No access control - anyone can change reward rate
    function setRewardRate(uint256 newRate) external {
        rewardRate = newRate;
    }

    /// @notice Emergency withdraw (forfeits rewards)
    /// @dev VULNERABILITY: Missing access control + reentrancy
    function emergencyWithdraw() external {
        StakeInfo storage info = stakes[msg.sender];
        uint256 amount = info.amount;

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");

        info.amount = 0;
        info.rewardDebt = 0;
        totalStaked -= amount;
    }

    receive() external payable {}
}
