// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureReplayMissingChainId
 * @notice Vulnerable: Missing chain ID validation allows cross-chain signature replay
 * @dev Real-world example: Wintermute hack - signatures valid on one chain could be replayed on another
 * Signatures can be replayed across different chains (mainnet, polygon, arbitrum, etc.)
 */
contract SignatureReplayMissingChainId {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        // Missing block.chainid in domain separator construction
        DOMAIN_SEPARATOR = keccak256(abi.encodePacked("EIP712Domain", address(this)));
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

        // Vulnerable: digest doesn't include block.chainid
        bytes32 digest = keccak256(abi.encodePacked(DOMAIN_SEPARATOR, owner, value, nonce, deadline));

        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "invalid signature");

        nonces[owner] = nonce + 1;
        // Execute action with value
    }
}
