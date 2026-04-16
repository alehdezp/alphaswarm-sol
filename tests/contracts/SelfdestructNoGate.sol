// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Public selfdestruct without access control.
contract SelfdestructNoGate {
    function destroy() external {
        selfdestruct(payable(msg.sender));
    }
}
