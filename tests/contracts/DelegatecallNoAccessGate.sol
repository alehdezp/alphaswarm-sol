// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Dangerous delegatecall without access control
contract DelegatecallNoAccessGate {
    address public implementation;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // CRITICAL: delegatecall without access control allows anyone to execute arbitrary code
    function execute(address target, bytes calldata data) external returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success, "delegatecall failed");
        return result;
    }

    // Properly protected delegatecall
    function safeExecute(address target, bytes calldata data) external returns (bytes memory) {
        require(msg.sender == owner, "not owner");
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success, "delegatecall failed");
        return result;
    }
}
