// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Delegatecall that relies on msg.sender context without access control.
contract DelegatecallContextSensitive {
    address public lastCaller;

    function execute(address target, bytes calldata data) external returns (bytes memory) {
        lastCaller = msg.sender;
        (bool ok, bytes memory result) = target.delegatecall(data);
        require(ok, "delegatecall failed");
        return result;
    }
}
