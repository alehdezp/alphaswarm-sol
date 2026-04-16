// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Reinitializer without guard or access control.
contract ReinitializerNoGuard {
    address public owner;

    function reinitialize(address newOwner) external {
        owner = newOwner;
    }
}
