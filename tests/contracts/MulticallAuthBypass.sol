// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multicall contract that can batch protected calls.
contract MulticallAuthBypass {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function multicall(bytes[] calldata calls) external {
        for (uint256 i = 0; i < calls.length; i++) {
            (bool ok, ) = address(this).delegatecall(calls[i]);
            require(ok, "call failed");
        }
    }

    function guardedAction(uint256 value) external {
        require(msg.sender == owner, "not owner");
        value;
    }
}
