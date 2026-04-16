// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IStakeEngine.sol";
import "../libraries/RewardCalc.sol";

/// @title StakeEngine (SAFE VARIANT)
contract StakeEngine_safe is IStakeEngine {
    using RewardCalc for uint256;

    struct StakeInfo {
        uint256 amount;
        uint256 startTime;
        uint256 rewardDebt;
    }

    mapping(address => StakeInfo) public stakes;
    uint256 public totalStaked;
    uint256 public rewardRate;
    address public admin;
    bool public paused;
    bool private _locked;

    modifier nonReentrant() {
        require(!_locked, "Reentrancy");
        _locked = true;
        _;
        _locked = false;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    constructor(uint256 _rewardRate) {
        admin = msg.sender;
        rewardRate = _rewardRate;
    }

    function stake() external payable override {
        require(msg.value > 0, "Zero stake");
        require(!paused, "Paused");
        StakeInfo storage info = stakes[msg.sender];
        if (info.amount > 0) {
            uint256 pending = info.amount.pendingReward(info.startTime, rewardRate);
            info.rewardDebt += pending;
        }
        info.amount += msg.value;
        info.startTime = block.timestamp;
        totalStaked += msg.value;
        emit Staked(msg.sender, msg.value);
    }

    function unstake(uint256 amount) external override nonReentrant {
        StakeInfo storage info = stakes[msg.sender];
        require(info.amount >= amount, "Insufficient stake");
        uint256 reward = info.amount.pendingReward(info.startTime, rewardRate) + info.rewardDebt;
        uint256 payout = amount + reward;
        info.amount -= amount;
        info.rewardDebt = 0;
        info.startTime = block.timestamp;
        totalStaked -= amount;
        (bool ok, ) = msg.sender.call{value: payout}("");
        require(ok, "Unstake failed");
        emit Unstaked(msg.sender, amount, reward);
    }

    function pendingRewards(address user) external view override returns (uint256) {
        StakeInfo memory info = stakes[user];
        return info.amount.pendingReward(info.startTime, rewardRate) + info.rewardDebt;
    }

    function togglePause() external onlyAdmin { paused = !paused; }
    function setRewardRate(uint256 newRate) external onlyAdmin { rewardRate = newRate; }

    function emergencyWithdraw() external nonReentrant {
        StakeInfo storage info = stakes[msg.sender];
        uint256 amount = info.amount;
        info.amount = 0;
        info.rewardDebt = 0;
        totalStaked -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");
    }

    receive() external payable {}
}
