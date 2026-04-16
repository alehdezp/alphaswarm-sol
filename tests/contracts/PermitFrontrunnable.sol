// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PermitFrontrunnable
 * @notice Vulnerable: Permit implementation susceptible to front-running
 * @dev Without proper checks, permit can be front-run:
 * 1. User signs permit for spender A
 * 2. Attacker sees transaction, front-runs with their own permit using same signature
 * 3. User's permit fails due to nonce increment
 * While this is a known EIP-2612 limitation, additional protections can help
 */
contract PermitFrontrunnable {
    mapping(address => uint256) public nonces;
    mapping(address => mapping(address => uint256)) public allowance;
    bytes32 public immutable DOMAIN_SEPARATOR;

    bytes32 public constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("PermitFrontrunnable")),
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

        // Vulnerable: No protection against front-running
        // Spender can be changed by front-runner
        allowance[owner][spender] = value;
    }

    function transferFrom(address from, address to, uint256 amount) external {
        require(allowance[from][msg.sender] >= amount, "insufficient allowance");
        allowance[from][msg.sender] -= amount;
        // Transfer logic
    }
}
