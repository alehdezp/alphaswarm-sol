// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Timelock delay set to zero.
contract TimelockDelayZero {
    uint256 public timelockDelay = 0;

    function execute(bytes calldata data) external {
        data;
    }
}
