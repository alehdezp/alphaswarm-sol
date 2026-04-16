// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureOffChainMismatch
 * @notice Vulnerable: Mismatch between off-chain signing and on-chain verification
 * @dev Common issues:
 * 1. Off-chain uses different encoding than on-chain
 * 2. Parameter order mismatch
 * 3. Type confusion (uint256 vs uint vs bytes32)
 * 4. Missing EIP-712 structure in signing library
 * This leads to signature verification always failing or succeeding incorrectly
 */
contract SignatureOffChainMismatch {
    mapping(address => uint256) public nonces;

    function executeWithSignature(
        address owner,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");

        uint256 nonce = nonces[owner];

        // Vulnerable: Inconsistent hashing with potential off-chain implementation
        // Off-chain might use: keccak256(abi.encode(owner, value, deadline, nonce))
        // On-chain uses different order or encoding
        bytes32 digest = keccak256(
            abi.encodePacked(
                owner,
                deadline, // Wrong order compared to what might be signed off-chain
                value,
                nonce
            )
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "wrong signer");

        nonces[owner] = nonce + 1;
        // Execute action
    }

    // Alternative function showing type confusion
    function executeWithTypeConfusion(
        address owner,
        uint128 smallValue, // Using uint128 but signing with uint256
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");

        // Vulnerable: Type size mismatch
        // Off-chain signs uint256, on-chain expects uint128
        bytes32 digest = keccak256(abi.encodePacked(owner, smallValue, deadline));

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "wrong signer");

        // Execute action
    }
}
