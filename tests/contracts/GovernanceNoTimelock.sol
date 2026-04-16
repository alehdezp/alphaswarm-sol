// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Governance contract without a timelock.
contract GovernanceNoTimelock {
    uint256 public proposalCount;
    uint256 public quorum;

    function propose() external {
        proposalCount += 1;
    }

    function setQuorum(uint256 value) external {
        quorum = value;
    }
}
