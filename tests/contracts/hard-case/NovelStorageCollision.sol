// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// =============================================================================
// HARD-CASE CONTRACT: Storage Collision via Delegatecall
// =============================================================================
//
// This contract intentionally demonstrates a subtle storage collision pattern
// that is easy to miss with naive pattern matching.
//
// // - delegatecall into an untrusted library that writes to slot 0
// - slot 0 in this proxy is the admin address
// - attacker can overwrite admin by calling delegateSetOwner()
//
// This is used for discovery/novel pattern testing (Plan 13) and hard-case runs.
// =============================================================================

contract CollisionLibrary {
    // Slot 0 in the library layout.
    address public owner;

    function setOwner(address newOwner) external {
        owner = newOwner;
    }
}

contract StorageCollisionProxy {
    // Slot 0 (admin) collides with CollisionLibrary.owner during delegatecall.
    address public admin;
    // Slot 1
    address public lib;

    constructor(address initialLib) {
        admin = msg.sender;
        lib = initialLib;
    }

    function upgrade(address newLib) external {
        require(msg.sender == admin, "not admin");
        lib = newLib;
    }

    // VULNERABLE: no access control, delegates to untrusted library.
    function delegateSetOwner(address newOwner) external {
        (bool ok, ) = lib.delegatecall(
            abi.encodeWithSignature("setOwner(address)", newOwner)
        );
        require(ok, "delegatecall failed");
    }
}
