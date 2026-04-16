// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title DataRegistry - Cross-module data storage
contract DataRegistry {
    mapping(bytes32 => uint256) public records;
    mapping(bytes32 => uint256) public timestamps;
    mapping(bytes32 => bool) public validity;
    address public registrar;

    constructor() {
        registrar = msg.sender;
    }

    /// @notice Store data for a module
    function recordData(bytes32 moduleId, uint256 data) external {
        records[moduleId] = data;
        timestamps[moduleId] = block.timestamp;
        validity[moduleId] = true;
    }

    /// @notice Fetch latest data
    function fetchLatest(bytes32 moduleId) external view returns (uint256, bool) {
        return (records[moduleId], validity[moduleId]);
    }

    /// @notice Invalidate record
    /// @dev VULNERABILITY: Missing access control
    function invalidateRecord(bytes32 moduleId) external {
        validity[moduleId] = false;
    }

    /// @notice Update registrar
    /// @dev VULNERABILITY: Missing access control
    function setRegistrar(address newRegistrar) external {
        registrar = newRegistrar;
    }
}
