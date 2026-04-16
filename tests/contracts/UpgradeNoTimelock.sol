// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Upgrade function without timelock protection.
contract UpgradeNoTimelock {
    address public implementation;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function upgradeTo(address newImplementation) external {
        require(msg.sender == owner, "not owner");
        implementation = newImplementation;
    }
}
