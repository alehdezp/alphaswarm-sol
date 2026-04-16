// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Payable fallback/receive without access control.
contract PayableFallbackNoGate {
    uint256 public received;

    receive() external payable {
        received += msg.value;
    }

    fallback() external payable {
        received += msg.value;
    }
}
