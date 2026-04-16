// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Unprotected initializer without guard or access control.
contract UnprotectedInitializer {
    address public owner;
    address public impl;

    function initialize(address newOwner) external {
        owner = newOwner;
    }

    function upgradeTo(address newImpl) external {
        impl = newImpl;
    }
}
