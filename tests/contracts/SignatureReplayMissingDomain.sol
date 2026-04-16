// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureReplayMissingDomain
 * @notice Vulnerable: Permit-like function without domain separator
 * @dev Missing domain separator in permit function allows cross-contract replay
 * Similar to EIP-2612 permit but without proper domain binding
 */
contract SignatureReplayMissingDomain {
    mapping(address => uint256) public nonces;
    mapping(address => mapping(address => uint256)) public allowance;

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

        uint256 nonce = nonces[owner];

        // Vulnerable: No domain separator usage in permit function
        bytes32 digest = keccak256(
            abi.encodePacked(owner, spender, value, nonce, deadline, block.chainid)
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "invalid signature");

        nonces[owner]++;
        allowance[owner][spender] = value;
    }
}
