// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication based on msg.value.
contract WeakAuthMsgValue {
    function privileged() external payable returns (bool) {
        require(msg.value > 0, "no value");
        return true;
    }
}
