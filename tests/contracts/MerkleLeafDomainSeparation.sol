// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MerkleLeafDomainSeparation {
    bytes32 public merkleRoot;

    constructor(bytes32 root) {
        merkleRoot = root;
    }

    // Vulnerable: leaf hashing without domain separation can collide with inner nodes.
    function claimUnsafe(address account, uint256 amount) external view returns (bytes32 leaf) {
        bytes32 root = merkleRoot;
        leaf = keccak256(abi.encodePacked(account, amount, root));
    }

    // Safe: domain separated leaf prefix.
    function claimSafe(address account, uint256 amount) external view returns (bytes32 leaf) {
        bytes32 root = merkleRoot;
        leaf = keccak256(abi.encodePacked(bytes1(0x00), account, amount, root));
    }
}
