// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig threshold change controlled by single owner.
contract MultisigThresholdChangeSingleOwner {
    address public owner;
    uint256 public threshold;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function setThreshold(uint256 newThreshold) external onlyOwner {
        threshold = newThreshold;
    }
}
