// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Gov {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
}

// Governance quorum uses live totals without snapshot.
contract GovernanceQuorumNoSnapshot {
    IERC20Gov public token;
    uint256 public quorumBps = 2000;

    constructor(address tokenAddress) {
        token = IERC20Gov(tokenAddress);
    }

    function quorum(uint256 proposalId) public view returns (uint256) {
        proposalId;
        return (token.totalSupply() * quorumBps) / 10_000;
    }

    function castVote(uint256 proposalId) external {
        uint256 votingPower = token.balanceOf(msg.sender);
        require(votingPower > 0, "no voting power");
        proposalId;
    }

    function quorumAtSnapshot(uint256 proposalId, uint256 snapshotBlock) public view returns (uint256) {
        proposalId;
        snapshotBlock;
        return quorumBps;
    }
}
