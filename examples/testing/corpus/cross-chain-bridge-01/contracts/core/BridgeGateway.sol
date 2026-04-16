// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../periphery/MessageVerifier.sol";

/// @title BridgeGateway - Cross-chain asset bridge with message verification
contract BridgeGateway {
    MessageVerifier public verifier;
    mapping(bytes32 => bool) public processedMessages;
    mapping(address => uint256) public lockedAssets;
    address public relayer;
    uint256 public bridgeFee;
    uint256 public totalLocked;
    bool public operational;

    event AssetLocked(address indexed user, uint256 amount, uint256 destChain);
    event AssetReleased(address indexed user, uint256 amount, bytes32 messageId);
    event RelayerUpdated(address indexed newRelayer);

    constructor(address _verifier) {
        verifier = MessageVerifier(_verifier);
        relayer = msg.sender;
        operational = true;
        bridgeFee = 10; // basis points
    }

    /// @notice Lock assets for cross-chain transfer
    function initiateTransfer(uint256 destChain) external payable {
        require(operational, "Bridge paused");
        require(msg.value > 0, "No assets");
        uint256 fee = (msg.value * bridgeFee) / 10000;
        uint256 netAmount = msg.value - fee;
        lockedAssets[msg.sender] += netAmount;
        totalLocked += netAmount;
        emit AssetLocked(msg.sender, netAmount, destChain);
    }

    /// @notice Release assets based on cross-chain message
    /// @dev VULNERABILITY: Cross-contract - verifier can be manipulated (B1)
    function executeRelease(
        address recipient,
        uint256 amount,
        bytes32 messageId,
        bytes calldata proof
    ) external {
        require(!processedMessages[messageId], "Already processed");

        // Cross-contract dependency: verifier.validateProof
        bool valid = verifier.validateProof(messageId, recipient, amount, proof);
        require(valid, "Invalid proof");

        processedMessages[messageId] = true;
        totalLocked -= amount;

        // VULNERABILITY: Reentrancy on release
        (bool ok, ) = recipient.call{value: amount}("");
        require(ok, "Release failed");

        emit AssetReleased(recipient, amount, messageId);
    }

    /// @notice Emergency unlock for user
    /// @dev VULNERABILITY: Missing access control + reentrancy
    function emergencyUnlock(address user) external {
        uint256 amount = lockedAssets[user];
        require(amount > 0, "Nothing locked");

        (bool ok, ) = user.call{value: amount}("");
        require(ok, "Unlock failed");

        lockedAssets[user] = 0;
        totalLocked -= amount;
    }

    /// @notice Update relayer address
    /// @dev VULNERABILITY: Missing access control
    function updateRelayer(address newRelayer) external {
        relayer = newRelayer;
        emit RelayerUpdated(newRelayer);
    }

    /// @notice Update verifier contract
    /// @dev VULNERABILITY: Missing access control - can set malicious verifier
    function updateVerifier(address newVerifier) external {
        verifier = MessageVerifier(newVerifier);
    }

    /// @notice Toggle bridge operational status
    function toggleBridge() external {
        require(msg.sender == relayer, "Not relayer");
        operational = !operational;
    }

    receive() external payable {}
}
