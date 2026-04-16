// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PermitIncorrectNonce
 * @notice Vulnerable: Incorrect nonce management in permit
 * @dev Multiple nonce-related vulnerabilities:
 * 1. Nonce not incremented atomically
 * 2. Nonce validation happens after signature check (gas waste on replay)
 * 3. No overflow protection on nonce increment
 * Proper nonce management is critical for preventing signature replay
 */
contract PermitIncorrectNonce {
    mapping(address => uint256) public nonces;
    mapping(address => mapping(address => uint256)) public allowance;
    bytes32 public immutable DOMAIN_SEPARATOR;

    bytes32 public constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("PermitIncorrectNonce")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 nonce,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");

        // Vulnerable: Using external nonce parameter instead of reading from state
        // Should be: uint256 currentNonce = nonces[owner];
        // Then verify nonce == currentNonce

        bytes32 structHash = keccak256(
            abi.encode(PERMIT_TYPEHASH, owner, spender, value, nonce, deadline)
        );

        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash)
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "wrong signer");

        // Vulnerable: Nonce check happens after expensive signature verification
        require(nonces[owner] == nonce, "invalid nonce");

        // Vulnerable: Nonce increment not in same statement as check
        nonces[owner] = nonce + 1;

        allowance[owner][spender] = value;
    }
}
