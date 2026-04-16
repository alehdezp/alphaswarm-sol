// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ValueMovementExternalCalls {
    mapping(address => bool) public allowedTargets;

    function uncheckedCall(address target, bytes calldata data) external {
        target.call(data);
    }

    function checkedCall(address target, bytes calldata data) external {
        (bool success, ) = target.call(data);
        require(success, "call failed");
    }

    function callWithGas(address target, bytes calldata data) external {
        target.call{gas: 2300}(data);
    }

    function decodeReturn(address target) external {
        (bool success, bytes memory returndata) = target.call("");
        require(success, "call failed");
        abi.decode(returndata, (uint256));
    }

    function forward(address target, bytes calldata data) external payable {
        (bool ok, ) = target.call{value: msg.value}(data);
        require(ok, "call failed");
    }

    function allowedCall(address target, bytes calldata data) external {
        require(allowedTargets[target], "not allowed");
        target.call(data);
    }
}
