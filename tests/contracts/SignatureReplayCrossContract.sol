// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureReplayCrossContract
 * @notice Vulnerable: Missing domain separator allows cross-contract signature replay
 * @dev Real-world example: Li.Fi - signatures valid for one contract could be used on another
 * Without a unique domain separator per contract, signatures are not bound to specific contract
 */
contract SignatureReplayCrossContract {
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

        // Vulnerable: No domain separator at all
        bytes32 digest = keccak256(abi.encodePacked(owner, value, nonce, deadline, block.chainid));

        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "invalid signature");

        nonces[owner] = nonce + 1;
        // Execute action
    }
}
