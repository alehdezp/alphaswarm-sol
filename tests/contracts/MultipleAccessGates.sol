// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Contract with multiple layered access controls
contract MultipleAccessGates {
    address public owner;
    bool public paused;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "paused");
        _;
    }

    // Multiple access gates: both modifier and inline check
    function criticalOperation() external onlyOwner whenNotPaused {
        require(msg.sender != address(0), "zero address");
        // privileged operation with triple protection
    }

    function setPaused(bool _paused) external onlyOwner {
        paused = _paused;
    }
}
