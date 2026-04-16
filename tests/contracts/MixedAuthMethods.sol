// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Contract mixing msg.sender and tx.origin for auth
contract MixedAuthMethods {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // Correct: uses msg.sender
    function goodAuth() external {
        require(msg.sender == owner, "not owner");
    }

    // Dangerous: uses tx.origin (phishing vulnerable)
    function badAuth() external {
        require(tx.origin == owner, "not owner");
    }

    // Mixed: uses both (confusing and potentially dangerous)
    function mixedAuth() external {
        require(msg.sender == owner || tx.origin == owner, "not authorized");
    }
}
