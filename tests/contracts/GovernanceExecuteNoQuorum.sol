// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Governance execution without quorum enforcement.
contract GovernanceExecuteNoQuorum {
    uint256 public quorumBps = 2000;

    function execute(uint256 proposalId) external {
        proposalId;
    }

    function quorum() external view returns (uint256) {
        return quorumBps;
    }
}
