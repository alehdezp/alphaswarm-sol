// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title MeritPool - Reputation-weighted staking with signature-based claims
contract MeritPool {
    struct Participant {
        uint256 staked;
        uint256 merit;
        uint256 lastClaim;
    }

    mapping(address => Participant) public participants;
    mapping(bytes32 => bool) public processedClaims;
    uint256 public totalStaked;
    uint256 public rewardPool;
    address public arbiter;
    address public signer;
    uint256 public epochDuration;

    event Enrolled(address indexed user, uint256 amount);
    event MeritAssigned(address indexed user, uint256 score);
    event RewardsClaimed(address indexed user, uint256 amount);

    constructor(address _signer, uint256 _epoch) {
        arbiter = msg.sender;
        signer = _signer;
        epochDuration = _epoch;
    }

    /// @notice Enroll in staking pool
    function enroll() external payable {
        require(msg.value >= 0.01 ether, "Minimum not met");
        participants[msg.sender].staked += msg.value;
        totalStaked += msg.value;
        emit Enrolled(msg.sender, msg.value);
    }

    /// @notice Claim rewards with signed merit proof
    /// @dev VULNERABILITY: Signature replay - no nonce or chainId (crypto-missing-chainid)
    function claimMeritReward(
        uint256 amount,
        uint256 merit,
        bytes calldata signature
    ) external {
        // Missing nonce, chainId, deadline in signed message
        bytes32 messageHash = keccak256(abi.encodePacked(msg.sender, amount, merit));
        bytes32 ethHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash));

        address recovered = _recover(ethHash, signature);
        require(recovered == signer, "Invalid signature");

        // Missing: processedClaims check (replay possible)
        participants[msg.sender].merit = merit;
        rewardPool -= amount;

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Claim failed");

        emit RewardsClaimed(msg.sender, amount);
    }

    /// @notice Withdraw stake
    /// @dev VULNERABILITY: Reentrancy - state after call
    function disenroll() external {
        Participant storage p = participants[msg.sender];
        uint256 amount = p.staked;
        require(amount > 0, "Not enrolled");

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Disenroll failed");

        p.staked = 0;
        totalStaked -= amount;
    }

    /// @notice Set merit score directly
    /// @dev VULNERABILITY: Missing access control on merit assignment
    function assignMerit(address user, uint256 score) external {
        participants[user].merit = score;
        emit MeritAssigned(user, score);
    }

    /// @notice Update signer key
    /// @dev VULNERABILITY: Missing access control
    function rotateSigner(address newSigner) external {
        signer = newSigner;
    }

    /// @notice Fund the reward pool
    function fundRewards() external payable {
        rewardPool += msg.value;
    }

    /// @dev ECDSA recovery (simplified)
    function _recover(bytes32 hash, bytes calldata sig) internal pure returns (address) {
        require(sig.length == 65, "Invalid signature length");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
        return ecrecover(hash, v, r, s);
    }
}
