// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BlockNumberRNG
 * @notice VULNERABLE: Uses block.number for randomness
 *
 * Vulnerabilities:
 * - block.number is entirely predictable
 * - Attackers can calculate future values
 * - No entropy from block number alone
 *
 * Related CWEs:
 * - CWE-338: Use of Cryptographically Weak PRNG
 * - CWE-330: Use of Insufficiently Random Values
 */

contract BlockNumberRNG {
    // VULNERABLE: block.number is predictable
    function predictableRandom() external view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(block.number))) % 100;
    }

    // VULNERABLE: Adding more predictable values doesn't help
    function stillPredictable() external view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(
            block.number,
            block.timestamp,
            msg.sender
        ))) % 100;
    }
}
