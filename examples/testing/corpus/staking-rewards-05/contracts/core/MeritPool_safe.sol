// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title MeritPool (SAFE VARIANT)
contract MeritPool_safe {
    struct Participant { uint256 staked; uint256 merit; uint256 lastClaim; }

    mapping(address => Participant) public participants;
    mapping(bytes32 => bool) public processedClaims;
    uint256 public totalStaked;
    uint256 public rewardPool;
    address public arbiter;
    address public signer;
    uint256 public epochDuration;
    bool private _locked;

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyArbiter() { require(msg.sender == arbiter, "Not arbiter"); _; }

    event Enrolled(address indexed user, uint256 amount);
    event MeritAssigned(address indexed user, uint256 score);
    event RewardsClaimed(address indexed user, uint256 amount);

    constructor(address _signer, uint256 _epoch) {
        arbiter = msg.sender; signer = _signer; epochDuration = _epoch;
    }

    function enroll() external payable {
        require(msg.value >= 0.01 ether, "Minimum not met");
        participants[msg.sender].staked += msg.value;
        totalStaked += msg.value;
        emit Enrolled(msg.sender, msg.value);
    }

    function claimMeritReward(uint256 amount, uint256 merit, uint256 nonce, uint256 deadline, bytes calldata signature) external nonReentrant {
        require(block.timestamp <= deadline, "Expired"); // FIXED: deadline
        bytes32 messageHash = keccak256(abi.encodePacked(msg.sender, amount, merit, nonce, block.chainid, deadline)); // FIXED: nonce+chainId
        bytes32 ethHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash));
        require(!processedClaims[messageHash], "Already claimed"); // FIXED: replay prevention
        address recovered = _recover(ethHash, signature);
        require(recovered == signer, "Invalid signature");
        processedClaims[messageHash] = true;
        participants[msg.sender].merit = merit;
        rewardPool -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Claim failed");
        emit RewardsClaimed(msg.sender, amount);
    }

    function disenroll() external nonReentrant { // FIXED
        Participant storage p = participants[msg.sender];
        uint256 amount = p.staked;
        require(amount > 0, "Not enrolled");
        p.staked = 0;
        totalStaked -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Disenroll failed");
    }

    function assignMerit(address user, uint256 score) external onlyArbiter { // FIXED
        participants[user].merit = score;
        emit MeritAssigned(user, score);
    }

    function rotateSigner(address newSigner) external onlyArbiter { // FIXED
        require(newSigner != address(0));
        signer = newSigner;
    }

    function fundRewards() external payable { rewardPool += msg.value; }

    function _recover(bytes32 hash, bytes calldata sig) internal pure returns (address) {
        require(sig.length == 65, "Invalid signature length");
        bytes32 r; bytes32 s; uint8 v;
        assembly { r := calldataload(sig.offset) s := calldataload(add(sig.offset, 32)) v := byte(0, calldataload(add(sig.offset, 64))) }
        return ecrecover(hash, v, r, s);
    }
}
