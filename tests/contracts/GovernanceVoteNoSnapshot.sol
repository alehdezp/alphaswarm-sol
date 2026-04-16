// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Votes {
    function balanceOf(address account) external view returns (uint256);
}

// Voting uses live balances without a snapshot.
contract GovernanceVoteNoSnapshot {
    IERC20Votes public token;
    mapping(uint256 => uint256) public votes;

    constructor(address tokenAddress) {
        token = IERC20Votes(tokenAddress);
    }

    function castVote(uint256 proposalId) external {
        uint256 votingPower = token.balanceOf(msg.sender);
        require(votingPower > 0, "no voting power");
        votes[proposalId] += votingPower;
    }

    function castVoteWithSnapshot(uint256 proposalId, uint256 snapshotBlock) external {
        snapshotBlock;
        votes[proposalId] += 1;
    }
}
