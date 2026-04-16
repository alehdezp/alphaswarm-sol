// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Access control with OR logic that weakens enforcement.
contract FlawedAccessControlOr {
    address public owner;
    address public admin;

    constructor() {
        owner = msg.sender;
        admin = msg.sender;
    }

    function sensitive() external {
        require(msg.sender == owner || msg.sender == admin, "not allowed");
    }
}
