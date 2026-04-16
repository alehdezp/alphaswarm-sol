// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Access control using string/hash comparison.
contract AccessGateStringCompare {
    string public role = "ADMIN";

    function privileged() external view returns (bool) {
        require(keccak256(bytes(role)) == keccak256(bytes("ADMIN")), "no role");
        return true;
    }
}
