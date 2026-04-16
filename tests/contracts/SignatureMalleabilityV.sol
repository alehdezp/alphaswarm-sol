// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureMalleabilityV
 * @notice Vulnerable: Missing v-value validation
 * @dev v parameter should be 27 or 28 for standard ECDSA signatures
 * While ecrecover accepts other values, proper validation ensures signature canonicality
 * EIP-2 specifies v should be restricted to 27 or 28
 */
contract SignatureMalleabilityV {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SignatureMalleabilityV")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    function executeWithSignature(
        address owner,
        uint256 value,
        uint256 nonce,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");

        // Vulnerable: No v-value validation (should be 27 or 28)

        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(owner, value, nonce, deadline))
            )
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "wrong signer");

        nonces[owner] = nonce + 1;
        // Execute action
    }
}
