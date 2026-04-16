// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Governance execution without voting period enforcement.
contract GovernanceExecuteNoVotePeriod {
    uint256 public proposalCount;

    function execute(uint256 proposalId) external {
        proposalId;
        proposalCount += 1;
    }

    function vote(uint256 proposalId) external {
        proposalId;
    }
}
