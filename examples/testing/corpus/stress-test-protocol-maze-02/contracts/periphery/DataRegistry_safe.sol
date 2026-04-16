// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title DataRegistry (SAFE VARIANT)
contract DataRegistry_safe {
    mapping(bytes32 => uint256) public records;
    mapping(bytes32 => uint256) public timestamps;
    mapping(bytes32 => bool) public validity;
    address public registrar;

    modifier onlyRegistrar() { require(msg.sender == registrar, "Not registrar"); _; }

    constructor() { registrar = msg.sender; }

    function recordData(bytes32 moduleId, uint256 data) external onlyRegistrar {
        records[moduleId] = data; timestamps[moduleId] = block.timestamp; validity[moduleId] = true;
    }

    function fetchLatest(bytes32 moduleId) external view returns (uint256, bool) {
        return (records[moduleId], validity[moduleId]);
    }

    function invalidateRecord(bytes32 moduleId) external onlyRegistrar { validity[moduleId] = false; } // FIXED
    function setRegistrar(address nr) external onlyRegistrar { registrar = nr; } // FIXED
}
