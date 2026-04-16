// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title LoopDosRenamed
 * @notice DoS vulnerabilities with non-standard naming.
 *         Tests detection without relying on "loop", "array", "batch" names.
 *
 * Renamed: users -> participants, batchProcess -> handleAll
 */
contract LoopDosRenamed {
    address[] public participants;  // Renamed from "users"
    mapping(address => uint256) public credits;  // Renamed from "balances"

    function enroll(address participant) external {
        participants.push(participant);
    }

    // VULNERABLE: Unbounded loop over dynamic array
    function distributeToAll(uint256 qty) external {
        for (uint256 i = 0; i < participants.length; i++) {
            credits[participants[i]] += qty;
        }
    }

    // VULNERABLE: External call in loop
    function refundAll() external {
        for (uint256 i = 0; i < participants.length; i++) {
            uint256 amount = credits[participants[i]];
            credits[participants[i]] = 0;
            (bool ok, ) = participants[i].call{value: amount}("");
            require(ok, "transfer failed");  // Single failure stops all
        }
    }

    // VULNERABLE: Unbounded array return
    function getAllParticipants() external view returns (address[] memory) {
        return participants;
    }

    // VULNERABLE: Unbounded deletion
    function removeAllParticipants() external {
        while (participants.length > 0) {
            participants.pop();
        }
    }

    receive() external payable {
        credits[msg.sender] += msg.value;
    }
}
