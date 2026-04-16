// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Callback entrypoint without access control.
contract CallbackNoAuth {
    function onCallback(address from, uint256 amount) external {
        // no auth checks
        if (from != address(0)) {
            amount;
        }
    }
}
