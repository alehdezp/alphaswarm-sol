// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureArbitrary
 * @notice Vulnerable: Arbitrary signature verification without proper binding
 * @dev Multiple issues:
 * 1. Message hash not bound to specific function or contract context
 * 2. No replay protection (nonce/deadline)
 * 3. Generic signature can be reused for different purposes
 * Similar to raw ecrecover usage without proper message construction
 */
contract SignatureArbitrary {
    mapping(bytes32 => bool) public executed;

    function executeWithArbitrarySignature(
        bytes32 messageHash,
        address expectedSigner,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // Vulnerable: Accepting arbitrary message hash without construction
        // No way to ensure what was actually signed
        address signer = ecrecover(messageHash, v, r, s);

        require(signer != address(0), "invalid signature");
        require(signer == expectedSigner, "wrong signer");

        // Vulnerable: Using messageHash as replay protection is weak
        // Attacker can observe any signed message and use it here
        require(!executed[messageHash], "already executed");
        executed[messageHash] = true;

        // Execute arbitrary action
    }
}
