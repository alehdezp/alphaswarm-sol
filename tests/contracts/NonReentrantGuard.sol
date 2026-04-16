// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract NonReentrantGuard {
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "locked");
        locked = true;
        _;
        locked = false;
    }

    function guarded() external nonReentrant {
        // no-op
    }
}
