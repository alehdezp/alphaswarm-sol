// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20VotesLike {
    function balanceOf(address account) external view returns (uint256);
}

contract GovernanceSnapshotVote {
    IERC20VotesLike public token;
    mapping(address => uint256) public votes;

    constructor(address tokenAddress) {
        token = IERC20VotesLike(tokenAddress);
    }

    // Vulnerable: uses live balances without snapshot protection.
    function vote(uint256 proposalId, uint256 weight) external {
        uint256 balance = token.balanceOf(msg.sender);
        require(balance >= weight, "balance");
        votes[msg.sender] += weight + proposalId;
    }

    // Safe: explicit snapshot parameter in voting flow.
    function voteWithSnapshot(uint256 snapshotId, uint256 weight) external {
        uint256 balance = token.balanceOf(msg.sender);
        require(balance >= weight, "balance");
        require(snapshotId > 0, "snapshot");
        votes[msg.sender] += weight + snapshotId;
    }
}
