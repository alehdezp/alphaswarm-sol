// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Read-only reentrancy vulnerability
contract ReadOnlyReentrancy {
    mapping(address => uint256) public balances;
    uint256 public totalDeposits;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    // Vulnerable: reads state that can be inconsistent during external call
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount;
        totalDeposits -= amount;
    }

    // Can return inconsistent data during reentrancy
    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }
}
