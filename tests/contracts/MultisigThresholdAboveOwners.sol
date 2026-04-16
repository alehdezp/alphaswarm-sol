// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig threshold change without owner count validation.
contract MultisigThresholdAboveOwners {
    address public owner;
    address[] public owners;
    uint256 public threshold;

    constructor() {
        owner = msg.sender;
        owners.push(msg.sender);
        threshold = 1;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function setThreshold(uint256 newThreshold) external onlyOwner {
        threshold = newThreshold;
    }
}
