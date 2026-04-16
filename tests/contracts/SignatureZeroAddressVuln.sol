// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureZeroAddressVuln
 * @notice Vulnerable: Missing zero address check on ecrecover result
 * @dev Critical vulnerability: ecrecover returns address(0) on invalid signature
 * If not checked, address(0) can be used to bypass signature verification
 * Real-world impact: Anyone can execute functions on behalf of address(0)
 * Reference: Common pitfall in signature verification
 */
contract SignatureZeroAddressVuln {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SignatureZeroAddressVuln")),
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

        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(owner, value, nonce, deadline))
            )
        );

        address signer = ecrecover(digest, v, r, s);

        // Vulnerable: Not checking signer != address(0)
        // If signature is invalid, ecrecover returns address(0)
        // This allows anyone to pass owner=address(0) and bypass verification
        require(signer == owner, "wrong signer");

        nonces[owner] = nonce + 1;
        // Execute action on behalf of owner
    }
}
