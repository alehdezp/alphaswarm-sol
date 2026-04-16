// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Unprotected initialization vulnerability
contract UninitializedOwner {
    address public owner;
    bool public initialized;

    // CRITICAL: anyone can call initialize and become owner
    function initialize(address _owner) external {
        require(!initialized, "already initialized");
        owner = _owner;
        initialized = true;
    }

    function privilegedAction() external {
        require(msg.sender == owner, "not owner");
        // do something privileged
    }
}
