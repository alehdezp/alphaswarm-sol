// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// State write before external call (safe pattern)
contract StateWriteBeforeCall {
    mapping(address => uint256) public balances;
    uint256 public totalWithdrawn;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: writes state before external call (checks-effects-interactions)
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");

        // Effects: update state first
        balances[msg.sender] -= amount;
        totalWithdrawn += amount;

        // Interactions: external call last
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
    }
}
