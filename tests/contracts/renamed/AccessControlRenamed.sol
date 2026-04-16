// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AccessControlRenamed
 * @notice Same access control vulnerability as NoAccessGate but with non-standard naming.
 *         Tests detection of missing access control without relying on "owner"/"admin" names.
 *
 * Renamed: owner -> controller, setOwner -> updateController
 */
contract AccessControlRenamed {
    // Renamed from "owner"
    address public controller;

    constructor() {
        controller = msg.sender;
    }

    // Renamed from "setOwner" - VULNERABLE: no access gate
    function updateController(address newController) external {
        controller = newController;
    }

    // Additional vulnerable function - no access gate
    function configureSystem(uint256 value) external {
        // Writes to privileged state without auth
    }
}
