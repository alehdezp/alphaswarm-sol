// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./ProposalRegistry_safe.sol";

/// @title TimelockController (SAFE VARIANT)
contract TimelockController_safe {
    ProposalRegistry_safe public registry;
    mapping(bytes32 => uint256) public scheduledOps;
    mapping(bytes32 => bool) public executedOps;
    mapping(address => bool) public executors;
    address public council;
    uint256 public minDelay;

    modifier onlyCouncil() { require(msg.sender == council, "Not council"); _; }

    event OperationScheduled(bytes32 indexed id, uint256 executeAfter);
    event OperationExecuted(bytes32 indexed id);

    constructor(address _registry, uint256 _delay) {
        registry = ProposalRegistry_safe(_registry);
        council = msg.sender;
        minDelay = _delay;
    }

    function scheduleOperation(address target, bytes calldata data, uint256 delay) external onlyCouncil returns (bytes32) {
        require(delay >= minDelay, "Delay too short");
        bytes32 opId = keccak256(abi.encodePacked(target, data, block.timestamp));
        require(!executedOps[opId], "Already executed"); // FIXED
        scheduledOps[opId] = block.timestamp + delay;
        emit OperationScheduled(opId, block.timestamp + delay);
        return opId;
    }

    function executeOperation(bytes32 opId, address target, bytes calldata data) external {
        require(executors[msg.sender] || msg.sender == council, "Not executor");
        require(scheduledOps[opId] > 0, "Not scheduled");
        require(!executedOps[opId], "Already executed"); // FIXED
        require(block.timestamp >= scheduledOps[opId], "Not ready");
        executedOps[opId] = true; // FIXED
        delete scheduledOps[opId];
        (bool ok, ) = target.call(data);
        require(ok, "Execution failed");
        emit OperationExecuted(opId);
    }

    function addExecutor(address executor) external onlyCouncil { executors[executor] = true; } // FIXED
    function removeExecutor(address executor) external onlyCouncil { executors[executor] = false; }
    function setMinDelay(uint256 newDelay) external onlyCouncil { minDelay = newDelay; } // FIXED
    function transferCouncil(address newCouncil) external onlyCouncil { // FIXED
        require(newCouncil != address(0));
        council = newCouncil;
    }
}
