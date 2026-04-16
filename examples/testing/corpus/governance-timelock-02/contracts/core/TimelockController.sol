// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./ProposalRegistry.sol";

/// @title TimelockController - Governance timelock with proposal lifecycle
contract TimelockController {
    ProposalRegistry public registry;
    mapping(bytes32 => uint256) public scheduledOps;
    mapping(address => bool) public executors;
    address public council;
    uint256 public minDelay;

    event OperationScheduled(bytes32 indexed id, uint256 executeAfter);
    event OperationExecuted(bytes32 indexed id);
    event OperationCancelled(bytes32 indexed id);

    constructor(address _registry, uint256 _delay) {
        registry = ProposalRegistry(_registry);
        council = msg.sender;
        minDelay = _delay;
    }

    /// @notice Schedule an operation for future execution
    /// @dev VULNERABILITY: State machine - can reschedule already-executed operations
    function scheduleOperation(
        address target,
        bytes calldata data,
        uint256 delay
    ) external returns (bytes32) {
        require(msg.sender == council, "Not council");
        require(delay >= minDelay, "Delay too short");

        bytes32 opId = keccak256(abi.encodePacked(target, data, block.timestamp));
        // Missing: check if opId was already executed
        scheduledOps[opId] = block.timestamp + delay;

        emit OperationScheduled(opId, block.timestamp + delay);
        return opId;
    }

    /// @notice Execute a scheduled operation
    /// @dev VULNERABILITY: No re-execution guard
    function executeOperation(
        bytes32 opId,
        address target,
        bytes calldata data
    ) external {
        require(executors[msg.sender] || msg.sender == council, "Not executor");
        require(scheduledOps[opId] > 0, "Not scheduled");
        require(block.timestamp >= scheduledOps[opId], "Not ready");

        // Missing: delete or mark as executed after execution
        // scheduledOps[opId] = 0; // <-- should be here

        (bool ok, ) = target.call(data);
        require(ok, "Execution failed");

        emit OperationExecuted(opId);
    }

    /// @notice Cancel a scheduled operation
    function cancelOperation(bytes32 opId) external {
        require(msg.sender == council, "Not council");
        delete scheduledOps[opId];
        emit OperationCancelled(opId);
    }

    /// @notice Add an executor
    /// @dev VULNERABILITY: Missing access control
    function addExecutor(address executor) external {
        executors[executor] = true;
    }

    /// @notice Remove an executor
    function removeExecutor(address executor) external {
        require(msg.sender == council, "Not council");
        executors[executor] = false;
    }

    /// @notice Update minimum delay
    /// @dev VULNERABILITY: Missing access control
    function setMinDelay(uint256 newDelay) external {
        minDelay = newDelay;
    }

    /// @notice Update council
    /// @dev VULNERABILITY: Missing access control
    function transferCouncil(address newCouncil) external {
        council = newCouncil;
    }
}
