// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// RE-SAFE-003: Checks-Effects-Interactions Pattern
// SAFE: State update before external call
contract Vault_06 {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: follows CEI pattern
    function withdraw(uint256 amount) external {
        // Check
        require(balances[msg.sender] >= amount, "insufficient");
        // Effect - state update BEFORE external call
        balances[msg.sender] -= amount;
        // Interaction - external call AFTER state update
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
    }

    receive() external payable {}
}
