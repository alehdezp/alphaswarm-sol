// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title EIP712IncorrectHash
 * @notice Vulnerable: Incorrect EIP-712 hash construction
 * @dev Multiple violations of EIP-712 standard:
 * - Missing EIP-191 prefix "\x19\x01"
 * - Incorrect encoding (using encodePacked instead of encode for struct)
 * - Missing proper type hash
 * These errors break signature verification and domain separation
 */
contract EIP712IncorrectHash {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("EIP712IncorrectHash")),
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

        // Vulnerable: Incorrect hash construction
        // Missing "\x19\x01" prefix
        // Using encodePacked instead of encode for struct hash
        // Missing type hash
        bytes32 digest = keccak256(
            abi.encodePacked(
                DOMAIN_SEPARATOR,
                owner,
                spender,
                value,
                nonce,
                deadline
            )
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "wrong signer");

        // Execute permit action
    }
}
