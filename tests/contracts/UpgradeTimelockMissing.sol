// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract UpgradeTimelockMissing {
    address public impl;
    uint256 public timelockDelay;

    constructor(uint256 delay) {
        timelockDelay = delay;
    }

    function upgradeTo(address newImpl, uint256 delay) external {
        impl = newImpl;
        timelockDelay = delay;
    }
}
