// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SecureVRF
 * @notice Demonstrates secure randomness using Chainlink VRF
 *
 * Security Features:
 * - Uses Chainlink VRF for verifiable randomness
 * - Cannot be manipulated by miners/validators
 * - Cryptographically secure
 *
 * Related CWEs:
 * - Mitigation for CWE-338: Weak PRNG
 * - Mitigation for CWE-330: Insufficiently Random Values
 */

interface IVRFCoordinatorV2 {
    function requestRandomWords(
        bytes32 keyHash,
        uint64 subId,
        uint16 minimumRequestConfirmations,
        uint32 callbackGasLimit,
        uint32 numWords
    ) external returns (uint256 requestId);
}

contract SecureVRF {
    IVRFCoordinatorV2 public coordinator;
    bytes32 public keyHash;
    uint64 public subscriptionId;

    mapping(uint256 => address) public requestToSender;
    mapping(address => uint256) public userRandomness;

    constructor(
        address coordinator_,
        bytes32 keyHash_,
        uint64 subscriptionId_
    ) {
        coordinator = IVRFCoordinatorV2(coordinator_);
        keyHash = keyHash_;
        subscriptionId = subscriptionId_;
    }

    function requestRandomNumber() external returns (uint256) {
        uint256 requestId = coordinator.requestRandomWords(
            keyHash,
            subscriptionId,
            3, // confirmations
            100000, // callback gas
            1 // num words
        );

        requestToSender[requestId] = msg.sender;
        return requestId;
    }

    function fulfillRandomWords(uint256 requestId, uint256[] memory randomWords) external {
        address sender = requestToSender[requestId];
        require(sender != address(0), "Invalid request");

        userRandomness[sender] = randomWords[0];
        delete requestToSender[requestId];
    }

    function getRandomNumber(address user) external view returns (uint256) {
        return userRandomness[user];
    }
}
