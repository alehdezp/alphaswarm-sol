// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title CommitRevealRNG
 * @notice Demonstrates commit-reveal scheme for randomness
 *
 * Security Features:
 * - Users commit to a secret value (hash)
 * - Users reveal the secret after commitment window
 * - Prevents front-running and manipulation
 * - Both parties must participate honestly
 *
 * Limitations:
 * - Requires multiple transactions
 * - Last revealer can grief by not revealing
 * - Better for multiplayer games than single-player
 *
 * Related CWEs:
 * - Mitigation for CWE-338: Weak PRNG
 */

contract CommitRevealRNG {
    struct Commitment {
        bytes32 commitHash;
        uint256 commitTime;
        bool revealed;
        uint256 revealedValue;
    }

    mapping(address => Commitment) public commitments;
    uint256 public constant REVEAL_PERIOD = 10 minutes;

    event Committed(address indexed user, bytes32 commitHash);
    event Revealed(address indexed user, uint256 value);

    // Phase 1: Commit to hash of (secret + nonce)
    function commit(bytes32 commitHash) external {
        require(commitments[msg.sender].commitTime == 0, "Already committed");

        commitments[msg.sender] = Commitment({
            commitHash: commitHash,
            commitTime: block.timestamp,
            revealed: false,
            revealedValue: 0
        });

        emit Committed(msg.sender, commitHash);
    }

    // Phase 2: Reveal the secret
    function reveal(uint256 secret, uint256 nonce) external {
        Commitment storage c = commitments[msg.sender];
        require(c.commitTime > 0, "Not committed");
        require(!c.revealed, "Already revealed");
        require(block.timestamp >= c.commitTime + 1 minutes, "Too early");
        require(block.timestamp < c.commitTime + REVEAL_PERIOD, "Too late");

        bytes32 hash = keccak256(abi.encodePacked(secret, nonce));
        require(hash == c.commitHash, "Invalid reveal");

        c.revealed = true;
        c.revealedValue = secret;

        emit Revealed(msg.sender, secret);
    }

    // Generate combined randomness from multiple participants
    function getCombinedRandom(address[] calldata participants) external view returns (uint256) {
        require(participants.length >= 2, "Need multiple participants");

        bytes memory combined;
        for (uint256 i = 0; i < participants.length; i++) {
            Commitment memory c = commitments[participants[i]];
            require(c.revealed, "Not all revealed");
            combined = abi.encodePacked(combined, c.revealedValue);
        }

        return uint256(keccak256(combined));
    }
}
