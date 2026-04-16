// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Arbitrary delegatecall - extremely dangerous
contract ArbitraryDelegatecall {
    address public implementation;
    address public owner;
    mapping(address => uint256) public balances;

    constructor() {
        owner = msg.sender;
    }

    // CRITICAL: allows arbitrary delegatecall with user-controlled target
    function proxy(address target, bytes calldata data) external payable returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success, "delegatecall failed");
        return result;
    }

    // CRITICAL: even with owner check, arbitrary delegatecall is dangerous
    function ownerProxy(address target, bytes calldata data) external payable returns (bytes memory) {
        require(msg.sender == owner, "not owner");
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success, "delegatecall failed");
        return result;
    }
}
