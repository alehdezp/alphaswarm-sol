// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title EIP712WeakDomain
 * @notice Vulnerable: Weak domain separator construction
 * @dev Domain separator should include all of: name, version, chainId, verifyingContract
 * Missing fields weaken domain separation and enable signature replay
 * Common mistakes: missing version, missing chainId, using encodePacked
 */
contract EIP712WeakDomain {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    bytes32 public constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    constructor() {
        // Vulnerable: Weak domain separator
        // Missing version field
        // Using encodePacked instead of encode
        // Could enable cross-version replay if contract is upgraded
        DOMAIN_SEPARATOR = keccak256(
            abi.encodePacked(
                "EIP712Domain",
                "EIP712WeakDomain",
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

        bytes32 structHash = keccak256(
            abi.encode(PERMIT_TYPEHASH, owner, spender, value, nonce, deadline)
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
