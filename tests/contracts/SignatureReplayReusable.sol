// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureReplayReusable
 * @notice Vulnerable: Missing nonce tracking allows signature reuse
 * @dev Signatures can be replayed multiple times by anyone observing the transaction
 * Without nonce management, the same signature can execute the same action repeatedly
 */
contract SignatureReplayReusable {
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SignatureReplayReusable")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    function executeWithSignature(
        address owner,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");

        // Vulnerable: No nonce in digest, signature can be reused
        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(owner, value, deadline))
            )
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "invalid signature");

        // Vulnerable: No nonce state write - signature can be replayed
        // Execute action
    }
}
