// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BlockhashWeakRNG
 * @notice VULNERABLE: Uses blockhash for randomness (predictable)
 *
 * Vulnerabilities:
 * - blockhash is predictable by miners/validators
 * - Only stores last 256 blocks, returns 0 for older blocks
 * - Can be manipulated by withholding blocks
 *
 * Related CWEs:
 * - CWE-338: Use of Cryptographically Weak Pseudo-Random Number Generator (PRNG)
 * - CWE-330: Use of Insufficiently Random Values
 *
 * Real-world impact:
 * - SmartBillions lottery hack (2018)
 * - Multiple gambling contract exploits
 *
 * Secure alternatives:
 * - Chainlink VRF
 * - Commit-reveal schemes
 * - External randomness beacons
 */

contract BlockhashWeakRNG {
    mapping(address => uint256) public tickets;

    // VULNERABLE: blockhash is predictable
    function rollDice() external view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(blockhash(block.number - 1)))) % 6 + 1;
    }

    // VULNERABLE: Can be gamed by miners
    function lottery() external view returns (bool) {
        uint256 random = uint256(keccak256(abi.encodePacked(
            blockhash(block.number - 1),
            block.timestamp,
            msg.sender
        )));
        return random % 100 < 10; // 10% win chance
    }

    // VULNERABLE: blockhash returns 0 for blocks > 256 ago
    function rollDiceOldBlock(uint256 blockNumber) external view returns (uint256) {
        require(blockNumber < block.number, "Future block");
        // Will return 0 if blockNumber is > 256 blocks ago
        return uint256(blockhash(blockNumber)) % 6 + 1;
    }
}
