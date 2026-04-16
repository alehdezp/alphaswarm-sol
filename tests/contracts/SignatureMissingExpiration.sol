// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureMissingExpiration
 * @notice Vulnerable: Complete absence of expiration mechanism
 * @dev Without deadline/expiration:
 * 1. Signatures valid forever (until nonce increments)
 * 2. MEV bots can hold and execute at optimal time for them
 * 3. Market condition changes make signature undesirable
 * 4. User has no way to invalidate old signatures
 * Similar to Uniswap Router without deadline parameter
 */
contract SignatureMissingExpiration {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SignatureMissingExpiration")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    // Vulnerable: No deadline parameter at all
    function executeWithSignature(
        address owner,
        uint256 value,
        uint256 nonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // Vulnerable: No expiration check whatsoever
        // Signature valid indefinitely

        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(owner, value, nonce))
            )
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "wrong signer");

        nonces[owner] = nonce + 1;
        // Execute action - could be days/weeks/months after signing
    }

    // Vulnerable: Has deadline parameter but doesn't check it
    function executeWithUnusedDeadline(
        address owner,
        uint256 value,
        uint256 nonce,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // Vulnerable: deadline parameter exists but is not validated
        // Worse than not having it - gives false sense of security

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
        // Execute without checking block.timestamp <= deadline
    }
}
