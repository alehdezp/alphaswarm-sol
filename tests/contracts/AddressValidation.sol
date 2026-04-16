// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract AddressValidation {
    function callTarget(address target, bytes calldata data) external returns (bytes memory) {
        (bool ok, bytes memory result) = target.call(data);
        require(ok, "call failed");
        return result;
    }

    function callTargetChecked(address target, bytes calldata data) external returns (bytes memory) {
        require(target.code.length > 0, "no code");
        require(target != address(this), "self");
        (bool ok, bytes memory result) = target.call(data);
        require(ok, "call failed");
        return result;
    }
}
