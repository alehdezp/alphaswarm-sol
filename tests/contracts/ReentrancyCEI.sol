// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Correctly implemented CEI (Checks-Effects-Interactions) pattern
contract ReentrancyCEI {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // SAFE: follows CEI pattern - state updated before external call
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount; // Effect before interaction
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
    }
}
