// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Cross-contract auth confusion via delegatecall.
contract CrossContractAuthConfusion {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function delegateAsOwner(address target, bytes calldata data) external {
        require(msg.sender == owner, "only owner");
        (bool ok, ) = target.delegatecall(data);
        require(ok, "call failed");
    }
}
