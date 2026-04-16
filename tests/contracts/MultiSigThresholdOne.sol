// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig with threshold set to one.
contract MultiSigThresholdOne {
    address[] public owners;
    uint256 public threshold = 1;

    function execute(address target, bytes calldata data) external {
        (bool ok, ) = target.call(data);
        require(ok, "call failed");
    }
}
