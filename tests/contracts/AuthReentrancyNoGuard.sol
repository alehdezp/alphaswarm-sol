// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Privileged external call without reentrancy protection.
contract AuthReentrancyNoGuard {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function emergencyCall(address target, bytes calldata data) external {
        require(msg.sender == owner, "only owner");
        (bool ok, ) = target.call(data);
        require(ok, "call failed");
    }
}
