// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SignatureWithNonce {
    mapping(address => uint256) public nonces;
    bytes32 public DOMAIN_SEPARATOR;

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encodePacked(address(this)));
    }

    function permit(
        address owner,
        uint256 value,
        uint256 nonce,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");
        bytes32 digest = keccak256(abi.encodePacked(DOMAIN_SEPARATOR, block.chainid, owner, value, nonce, deadline));
        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "bad sig");
        nonces[owner] = nonce + 1;
    }
}
