// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Access control bypass via constructor
contract ConstructorAccessBypass {
    address public owner;
    address public treasury;

    // CRITICAL: treasury set in constructor without validation
    // Deployer can set arbitrary treasury address
    constructor(address _treasury) {
        owner = msg.sender;
        treasury = _treasury;
    }

    // Protected function but treasury was set unsafely
    function setTreasury(address newTreasury) external {
        require(msg.sender == owner, "not owner");
        treasury = newTreasury;
    }

    function withdraw() external {
        require(msg.sender == treasury, "not treasury");
        // withdrawal logic
    }
}
