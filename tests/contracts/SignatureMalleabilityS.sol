// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SignatureMalleabilityS
 * @notice Vulnerable: Missing s-value validation allows signature malleability
 * @dev OpenZeppelin guidance: s must be in lower half of secp256k1 curve
 * Reference: https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/cryptography/ECDSA.sol
 * s-value malleability allows creating alternative valid signatures for the same message
 * s' = secp256k1_order - s produces another valid signature with same r, different s
 */
contract SignatureMalleabilityS {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("SignatureMalleabilityS")),
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

        // Vulnerable: No s-value validation
        // OpenZeppelin requires: s <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0

        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(owner, value, nonce, deadline))
            )
        );

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "wrong signer");

        nonces[owner] = nonce + 1;
        // Execute action
    }
}
