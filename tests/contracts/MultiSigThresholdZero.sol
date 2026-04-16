// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig with threshold set to zero.
contract MultiSigThresholdZero {
    address[] public owners;
    uint256 public threshold = 0;

    function execute(address target, bytes calldata data) external {
        (bool ok, ) = target.call(data);
        require(ok, "call failed");
    }
}
