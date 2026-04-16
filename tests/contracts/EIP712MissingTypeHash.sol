// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title EIP712MissingTypeHash
 * @notice Vulnerable: Missing type hash in EIP-712 implementation
 * @dev Type hash is required for proper EIP-712 structured data hashing
 * Without it, different function signatures could produce same hash
 * Reference: EIP-712 requires hashing of the type definition
 */
contract EIP712MissingTypeHash {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("EIP712MissingTypeHash")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");

        uint256 nonce = nonces[owner]++;

        // Vulnerable: Missing type hash
        // Should include: keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)")
        bytes32 structHash = keccak256(
            abi.encode(owner, spender, value, nonce, deadline)
        );

        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash)
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "wrong signer");

        // Execute permit action
    }
}
