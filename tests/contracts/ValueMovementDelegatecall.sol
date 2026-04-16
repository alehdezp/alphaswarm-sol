// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ValueMovementDelegatecall {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function delegateAny(address target, bytes calldata data) external {
        target.delegatecall(data);
    }

    function delegateWithSender(address target, bytes calldata data) external {
        require(msg.sender == owner, "not owner");
        target.delegatecall(data);
    }

    function upgradeDelegate(address implementation, bytes calldata data) external {
        require(msg.sender == owner, "not owner");
        implementation.delegatecall(data);
    }
}
