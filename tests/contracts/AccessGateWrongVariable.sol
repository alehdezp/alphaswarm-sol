// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Access control compares wrong variable.
contract AccessGateWrongVariable {
    address public owner;
    address public admin;
    uint256 public value;

    constructor() {
        owner = msg.sender;
        admin = msg.sender;
    }

    function setValue(address caller, uint256 newValue) external {
        require(caller == owner, "not owner");
        value = newValue;
    }
}
