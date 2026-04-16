// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig configuration changes without access control.
contract MultisigConfigNoGate {
    address[] public owners;
    uint256 public threshold;

    function setThreshold(uint256 newThreshold) external {
        threshold = newThreshold;
    }

    function addSigner(address newSigner) external {
        owners.push(newSigner);
    }
}
