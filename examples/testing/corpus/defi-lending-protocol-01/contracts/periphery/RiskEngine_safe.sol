// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title RiskEngine (SAFE VARIANT)
contract RiskEngine_safe {
    address public facility;
    address public governance;
    uint256 public maxSystemLeverage;
    mapping(address => bool) public whitelistedOracles;
    address[] public oracleRegistry;
    uint256 public constant MAX_ORACLES = 50;

    modifier onlyGovernance() { require(msg.sender == governance, "Not governance"); _; }

    constructor(address _facility) {
        facility = _facility;
        governance = msg.sender;
        maxSystemLeverage = 500;
    }

    function registerOracle(address oracleAddr) external onlyGovernance { // FIXED
        require(oracleRegistry.length < MAX_ORACLES, "Too many oracles");
        whitelistedOracles[oracleAddr] = true;
        oracleRegistry.push(oracleAddr);
    }

    function checkSystemLeverage(uint256 totalAssets, uint256 totalDebt) external view returns (bool) {
        if (totalAssets == 0) return false;
        return (totalDebt * 100) / totalAssets <= maxSystemLeverage;
    }

    function emergencyFreeze() external onlyGovernance {
        (bool ok, ) = facility.call(abi.encodeWithSignature("toggleSystemState()"));
        require(ok, "Freeze failed");
    }

    function purgeOracles() external onlyGovernance {
        uint256 len = oracleRegistry.length;
        for (uint256 i = 0; i < len; i++) { // Bounded by MAX_ORACLES
            whitelistedOracles[oracleRegistry[i]] = false;
        }
        delete oracleRegistry;
    }
}
