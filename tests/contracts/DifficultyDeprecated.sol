// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DifficultyDeprecated
 * @notice VULNERABLE: Uses deprecated block.difficulty (now PREVRANDAO)
 *
 * Context:
 * - Pre-merge: block.difficulty was proof-of-work difficulty
 * - Post-merge: block.difficulty is now PREVRANDAO (not random!)
 * - PREVRANDAO is predictable by validators
 *
 * Vulnerabilities:
 * - Treating PREVRANDAO as random is dangerous
 * - Validators know PREVRANDAO in advance
 * - Can be used to game lotteries/randomness
 *
 * Related CWEs:
 * - CWE-338: Use of Cryptographically Weak PRNG
 * - CWE-477: Use of Obsolete Function
 *
 * Note: In Solidity 0.8.18+, block.difficulty is aliased to block.prevrandao
 */

contract DifficultyDeprecated {
    // VULNERABLE: Post-merge, this is PREVRANDAO (not random)
    function randomFromDifficulty() external view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(block.difficulty))) % 100;
    }

    // VULNERABLE: PREVRANDAO is known to validator
    function randomFromPrevrandao() external view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(block.prevrandao))) % 100;
    }
}
