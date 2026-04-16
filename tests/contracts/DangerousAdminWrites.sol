// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Admin-named function that mutates privileged state.
contract DangerousAdminWrites {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function updateOwner(address newOwner) external onlyOwner {
        owner = newOwner;
    }
}
