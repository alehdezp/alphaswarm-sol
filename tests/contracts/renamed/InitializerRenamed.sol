// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title InitializerRenamed
 * @notice Initializer vulnerability with non-standard naming.
 *         Tests detection without relying on "initialize" name.
 *
 * Renamed: initialize -> setup, initializer modifier -> none
 */
contract InitializerRenamed {
    address public controller;  // Renamed from "owner"
    bool private hasBeenConfigured;  // Renamed from "initialized"

    // Renamed from "initialize" - VULNERABLE: no access gate, re-callable
    function setup(address _controller) external {
        require(!hasBeenConfigured, "already done");
        controller = _controller;
        hasBeenConfigured = true;
    }

    // Another variant - VULNERABLE: completely unguarded initializer-like function
    function bootstrap(address _controller) external {
        controller = _controller;
    }

    // VULNERABLE: can be called multiple times
    function reconfigure(address _controller) external {
        controller = _controller;
    }
}
