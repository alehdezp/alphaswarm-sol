// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VulnerableStateInput {
    address public owner;
    uint256 public feeBps;
    mapping(address => uint256) public balances;

    constructor(uint256 initialFeeBps) {
        owner = msg.sender;
        feeBps = initialFeeBps;
    }

    // Vulnerable: attacker-controlled input directly updates ownership state.
    function setOwner(address newOwner) external {
        owner = newOwner;
    }

    // Vulnerable: attacker-controlled input directly updates a global config.
    function setFeeBps(uint256 newFeeBps) external {
        feeBps = newFeeBps;
    }

    // Vulnerable: attacker-controlled input directly updates user balances.
    function credit(address user, uint256 amount) external {
        balances[user] += amount;
    }
}
