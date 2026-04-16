// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Upgrade function without enforcing timelock delay.
contract UpgradeTimelockMissingCheck {
    address public owner;
    address public implementation;
    uint256 public timelockDelay;

    constructor() {
        owner = msg.sender;
        timelockDelay = 2 days;
    }

    function upgradeTo(address newImplementation) external {
        require(msg.sender == owner, "not owner");
        implementation = newImplementation;
    }
}
