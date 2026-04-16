// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Upgrade function without access control.
contract UpgradeNoAccessControl {
    address public implementation;

    function upgradeTo(address newImplementation) external {
        implementation = newImplementation;
    }
}
