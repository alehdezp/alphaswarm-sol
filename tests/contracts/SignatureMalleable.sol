// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureMalleable
 * @notice Vulnerable: Combined signature malleability issues
 * @dev Missing both v and s validation makes signatures fully malleable
 * Attackers can create alternative valid signatures without private key
 * This combines multiple malleability vectors
 */
contract SignatureMalleable {
    mapping(address => uint256) public nonces;

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

        // Vulnerable: No v validation
        // Vulnerable: No s validation
        // Vulnerable: No zero address check on signer

        bytes32 digest = keccak256(abi.encodePacked(owner, value, nonce, deadline, block.chainid));

        address signer = ecrecover(digest, v, r, s);
        // Vulnerable: Not checking signer != address(0)
        require(signer == owner, "wrong signer");

        nonces[owner] = nonce + 1;
        // Execute action
    }
}
