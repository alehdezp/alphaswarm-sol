// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication based on extcodehash.
contract WeakAuthExtcodehash {
    function privileged(address user) external view returns (bool) {
        bytes32 codehash;
        assembly {
            codehash := extcodehash(user)
        }
        require(codehash != bytes32(0), "no code");
        return true;
    }
}
