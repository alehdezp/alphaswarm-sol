// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IStakeEngine {
    function stake() external payable;
    function unstake(uint256 amount) external;
    function pendingRewards(address user) external view returns (uint256);
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount, uint256 reward);
}
