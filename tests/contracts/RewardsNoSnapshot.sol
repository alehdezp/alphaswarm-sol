// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ITokenRewards {
    function balanceOf(address account) external view returns (uint256);
}

contract RewardsNoSnapshot {
    ITokenRewards public token;
    mapping(address => uint256) public rewards;

    constructor(ITokenRewards token_) {
        token = token_;
    }

    function distributeRewards(address account) external {
        uint256 balance = token.balanceOf(account);
        rewards[account] += balance / 10;
    }

    function distributeRewardsSnapshot(address account, uint256 snapshotId) external {
        require(snapshotId > 0, "snapshot");
        uint256 balance = token.balanceOf(account);
        rewards[account] += balance / 10;
    }
}
