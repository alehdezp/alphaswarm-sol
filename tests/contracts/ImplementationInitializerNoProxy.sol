// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Implementation contract with unguarded initializer.
contract VaultImplementation {
    address public owner;

    function initialize(address newOwner) external {
        owner = newOwner;
    }
}
