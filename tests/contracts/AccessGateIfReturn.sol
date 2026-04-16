// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Access control using if-return instead of revert.
contract AccessGateIfReturn {
    address public owner;
    uint256 public value;

    constructor() {
        owner = msg.sender;
    }

    function setValue(uint256 newValue) external {
        if (msg.sender != owner) {
            return;
        }
        value = newValue;
    }
}
