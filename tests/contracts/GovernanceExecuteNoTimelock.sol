// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Governance execution without timelock check.
contract GovernanceExecuteNoTimelock {
    uint256 public timelockDelay = 2 days;
    uint256 public proposalCount;

    function queue(uint256 proposalId) external {
        proposalId;
        proposalCount += 1;
    }

    function executeProposal(uint256 proposalId, uint256 eta) external {
        proposalId;
        eta;
        proposalCount += 1;
    }
}
