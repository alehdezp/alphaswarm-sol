// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Partial access control on privileged operations
contract PartialAccessControl {
    address public owner;
    address public admin;
    uint256 public fee;
    uint256 public maxSupply;

    constructor() {
        owner = msg.sender;
        admin = msg.sender;
    }

    // Properly protected
    function setOwner(address newOwner) external {
        require(msg.sender == owner, "not owner");
        owner = newOwner;
    }

    // Partially protected: checks one role but writes to multiple privileged vars
    function updateSettings(address newAdmin, uint256 newFee) external {
        require(msg.sender == owner, "not owner");
        admin = newAdmin; // protected
        fee = newFee;     // protected but only by owner check
    }

    // CRITICAL: writes privileged state without any access control
    function dangerousUpdate(address newAdmin) external {
        admin = newAdmin; // Anyone can call this and become admin!
    }
}
