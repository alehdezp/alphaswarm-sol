// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication based on balance check.
contract WeakAuthBalanceCheck {
    function privileged(address caller) external view returns (bool) {
        require(caller.balance > 0, "no balance");
        return true;
    }
}
