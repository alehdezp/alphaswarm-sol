// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title RiskEngine - Monitors system-level risk parameters
contract RiskEngine {
    address public facility;
    address public governance;
    uint256 public maxSystemLeverage;

    mapping(address => bool) public whitelistedOracles;
    address[] public oracleRegistry;

    constructor(address _facility) {
        facility = _facility;
        governance = msg.sender;
        maxSystemLeverage = 500; // 5x
    }

    /// @notice Register an oracle source
    /// @dev VULNERABILITY: Missing access control on oracle registration
    function registerOracle(address oracleAddr) external {
        whitelistedOracles[oracleAddr] = true;
        oracleRegistry.push(oracleAddr);
    }

    /// @notice Check system leverage
    function checkSystemLeverage(uint256 totalAssets, uint256 totalDebt)
        external
        view
        returns (bool)
    {
        if (totalAssets == 0) return false;
        return (totalDebt * 100) / totalAssets <= maxSystemLeverage;
    }

    /// @notice Emergency freeze facility
    function emergencyFreeze() external {
        require(msg.sender == governance, "Not governance");
        (bool ok, ) = facility.call(
            abi.encodeWithSignature("toggleSystemState()")
        );
        require(ok, "Freeze failed");
    }

    /// @notice Deregister all oracles
    /// @dev VULNERABILITY: Unbounded loop
    function purgeOracles() external {
        require(msg.sender == governance, "Not governance");
        for (uint256 i = 0; i < oracleRegistry.length; i++) {
            whitelistedOracles[oracleRegistry[i]] = false;
        }
        delete oracleRegistry;
    }
}
