// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fallback without access control.
contract FallbackNoAuth {
    uint256 public calls;

    fallback() external {
        calls += 1;
    }
}
