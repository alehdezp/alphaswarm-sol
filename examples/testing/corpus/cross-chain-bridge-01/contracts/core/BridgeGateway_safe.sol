// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../periphery/MessageVerifier_safe.sol";

/// @title BridgeGateway (SAFE VARIANT)
contract BridgeGateway_safe {
    MessageVerifier_safe public verifier;
    mapping(bytes32 => bool) public processedMessages;
    mapping(address => uint256) public lockedAssets;
    address public relayer;
    uint256 public bridgeFee;
    uint256 public totalLocked;
    bool public operational;
    bool private _locked;

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyRelayer() { require(msg.sender == relayer, "Not relayer"); _; }

    event AssetLocked(address indexed user, uint256 amount, uint256 destChain);
    event AssetReleased(address indexed user, uint256 amount, bytes32 messageId);

    constructor(address _verifier) {
        verifier = MessageVerifier_safe(_verifier);
        relayer = msg.sender;
        operational = true;
        bridgeFee = 10;
    }

    function initiateTransfer(uint256 destChain) external payable {
        require(operational, "Bridge paused");
        require(msg.value > 0, "No assets");
        uint256 fee = (msg.value * bridgeFee) / 10000;
        uint256 netAmount = msg.value - fee;
        lockedAssets[msg.sender] += netAmount;
        totalLocked += netAmount;
        emit AssetLocked(msg.sender, netAmount, destChain);
    }

    function executeRelease(address recipient, uint256 amount, bytes32 messageId, bytes calldata proof) external onlyRelayer nonReentrant {
        require(!processedMessages[messageId], "Already processed");
        bool valid = verifier.validateProof(messageId, recipient, amount, proof);
        require(valid, "Invalid proof");
        processedMessages[messageId] = true;
        totalLocked -= amount;
        (bool ok, ) = recipient.call{value: amount}("");
        require(ok, "Release failed");
        emit AssetReleased(recipient, amount, messageId);
    }

    function emergencyUnlock(address user) external onlyRelayer nonReentrant { // FIXED
        uint256 amount = lockedAssets[user];
        require(amount > 0, "Nothing locked");
        lockedAssets[user] = 0;
        totalLocked -= amount;
        (bool ok, ) = user.call{value: amount}("");
        require(ok, "Unlock failed");
    }

    function updateRelayer(address newRelayer) external onlyRelayer { relayer = newRelayer; } // FIXED
    function updateVerifier(address newVerifier) external onlyRelayer { verifier = MessageVerifier_safe(newVerifier); } // FIXED
    function toggleBridge() external onlyRelayer { operational = !operational; }

    receive() external payable {}
}
