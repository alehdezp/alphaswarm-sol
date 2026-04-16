// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureCompactVulnerable
 * @notice Vulnerable: Improper compact signature handling (EIP-2098)
 * @dev EIP-2098 compact signatures encode vs in the high bit of s
 * Improper handling can lead to signature malleability or verification failures
 * Compact signatures: 64 bytes (r + s with v encoded in s high bit)
 */
contract SignatureCompactVulnerable {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SignatureCompactVulnerable")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    function executeWithCompactSignature(
        address owner,
        uint256 value,
        uint256 nonce,
        uint256 deadline,
        bytes32 r,
        bytes32 vs
    ) external {
        require(block.timestamp <= deadline, "expired");

        // Vulnerable: Incorrect compact signature decoding
        // Should extract v from high bit and mask s properly
        bytes32 s = vs; // Wrong: should be vs & 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
        uint8 v = 27; // Wrong: should extract from high bit of vs

        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(owner, value, nonce, deadline))
            )
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "invalid signature");

        nonces[owner] = nonce + 1;
        // Execute action
    }
}
