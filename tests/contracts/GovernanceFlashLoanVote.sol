// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20GovVotes {
    function balanceOf(address account) external view returns (uint256);
}

// Governance vote reads live balance from token (flash-loan risk).
contract GovernanceFlashLoanVote {
    IERC20GovVotes public token;

    constructor(address tokenAddress) {
        token = IERC20GovVotes(tokenAddress);
    }

    function vote(uint256 proposalId) external {
        uint256 votingPower = token.balanceOf(msg.sender);
        require(votingPower > 0, "no voting power");
        proposalId;
    }
}
