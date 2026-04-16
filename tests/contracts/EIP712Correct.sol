// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title EIP712Correct
 * @notice Safe: Proper EIP-712 typed structured data hashing implementation
 * @dev Reference: https://eips.ethereum.org/EIPS/eip-712
 * Implements all required components:
 * - Proper domain separator with all fields
 * - Type hash computation
 * - Structured data encoding
 * - EIP-191 prefix ("\x19\x01")
 */
contract EIP712Correct {
    mapping(address => uint256) public nonces;

    bytes32 public immutable DOMAIN_SEPARATOR;
    bytes32 public constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("EIP712Correct")),
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
        require(owner != address(0), "invalid owner");

        uint256 nonce = nonces[owner]++;

        // Safe: Proper EIP-712 structured data hashing
        bytes32 structHash = keccak256(
            abi.encode(PERMIT_TYPEHASH, owner, spender, value, nonce, deadline)
        );

        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash)
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "wrong signer");

        // Safe: Proper v and s validation
        require(v == 27 || v == 28, "invalid v");
        require(uint256(s) <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0, "invalid s");

        // Execute permit action
    }
}
