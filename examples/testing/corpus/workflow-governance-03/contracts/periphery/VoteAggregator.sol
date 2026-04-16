// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title VoteAggregator - Batch voting operations
contract VoteAggregator {
    address public governor;
    address public operator;
    mapping(address => uint256) public delegatedPower;

    constructor(address _governor) {
        governor = _governor;
        operator = msg.sender;
    }

    /// @notice Batch vote on multiple proposals
    /// @dev VULNERABILITY: Unbounded loop DoS
    function batchVote(uint256[] calldata proposalIds, bool[] calldata supports) external {
        require(proposalIds.length == supports.length, "Length mismatch");
        for (uint256 i = 0; i < proposalIds.length; i++) {
            (bool ok, ) = governor.call(
                abi.encodeWithSignature(
                    "castVote(uint256,bool)",
                    proposalIds[i],
                    supports[i]
                )
            );
            require(ok, "Vote failed");
        }
    }

    /// @notice Delegate power to this contract
    function delegateTo(uint256 amount) external {
        delegatedPower[msg.sender] += amount;
    }

    /// @notice Withdraw delegated power
    /// @dev VULNERABILITY: Reentrancy via callback
    function withdrawDelegation() external {
        uint256 amount = delegatedPower[msg.sender];
        require(amount > 0, "Nothing delegated");

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");

        delegatedPower[msg.sender] = 0;
    }

    receive() external payable {}
}
