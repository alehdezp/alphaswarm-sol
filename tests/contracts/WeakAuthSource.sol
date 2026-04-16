// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication based on timestamp.
contract WeakAuthSource {
    function privileged(uint256 unlockTime) external returns (bool) {
        require(block.timestamp >= unlockTime, "too early");
        return true;
    }
}
