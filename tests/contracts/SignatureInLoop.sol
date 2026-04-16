// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureInLoop
 * @notice Vulnerable: Signature verification in unbounded loop (DoS risk)
 * @dev Verifying signatures in loops can cause:
 * 1. High gas consumption
 * 2. DoS if loop bound controlled by attacker
 * 3. Block gas limit issues for large batches
 * ecrecover is expensive (~3000 gas), multiplied by loop iterations
 */
contract SignatureInLoop {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    struct Operation {
        address owner;
        uint256 value;
        uint256 nonce;
        uint256 deadline;
    }

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SignatureInLoop")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    // Vulnerable: Verifying signatures in loop
    function batchExecute(
        Operation[] calldata operations,
        uint8[] calldata vs,
        bytes32[] calldata rs,
        bytes32[] calldata ss
    ) external {
        // Vulnerable: Loop bound controlled by caller
        for (uint256 i = 0; i < operations.length; i++) {
            Operation calldata op = operations[i];
            require(block.timestamp <= op.deadline, "expired");

            bytes32 digest = keccak256(
                abi.encodePacked(
                    "\x19\x01",
                    DOMAIN_SEPARATOR,
                    keccak256(abi.encode(op.owner, op.value, op.nonce, op.deadline))
                )
            );

            // Vulnerable: ecrecover in loop
            address signer = ecrecover(digest, vs[i], rs[i], ss[i]);
            require(signer != address(0), "invalid signature");
            require(signer == op.owner, "wrong signer");

            nonces[op.owner] = op.nonce + 1;
            // Execute operation
        }
    }
}
