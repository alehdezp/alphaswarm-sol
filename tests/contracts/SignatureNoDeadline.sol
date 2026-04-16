// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureNoDeadline
 * @notice Vulnerable: Missing deadline/expiration check enables griefing and MEV attacks
 * @dev Real-world example: Uniswap Router - deadlines prevent stale transactions from executing
 * Signatures without expiration can be held and executed at unfavorable times
 */
contract SignatureNoDeadline {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SignatureNoDeadline")),
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
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // Vulnerable: No deadline check - signatures never expire

        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(owner, value, nonce))
            )
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "invalid signature");

        nonces[owner] = nonce + 1;
        // Execute action - could be at unfavorable time for signer
    }
}
