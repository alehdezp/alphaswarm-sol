// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ReentrancyRenamed
 * @notice Same reentrancy vulnerability as ReentrancyClassic but with non-standard naming.
 *         Tests detection of reentrancy without relying on function name "withdraw".
 *
 * Renamed: withdraw -> removeFunds, balances -> userDeposits, deposit -> addFunds
 */
contract ReentrancyRenamed {
    // Renamed from "balances"
    mapping(address => uint256) public userDeposits;

    // Renamed from "deposit"
    function addFunds() external payable {
        userDeposits[msg.sender] += msg.value;
    }

    // Renamed from "withdraw" - VULNERABLE: external call before state update
    function removeFunds(uint256 amount) external {
        require(userDeposits[msg.sender] >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        userDeposits[msg.sender] -= amount;  // State update AFTER external call
    }
}
