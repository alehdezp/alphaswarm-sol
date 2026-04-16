// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Timelock admin function without access control.
contract TimelockAdminNoGate {
    uint256 public timelockDelay = 1 days;

    function setTimelockDelay(uint256 newDelay) external {
        timelockDelay = newDelay;
    }
}
