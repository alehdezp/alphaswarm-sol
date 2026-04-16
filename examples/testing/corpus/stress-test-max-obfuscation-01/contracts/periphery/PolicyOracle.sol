// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title PolicyOracle - Rate oracle for adaptive pool policies
contract PolicyOracle {
    uint256 public rate;
    uint256 public lastUpdated;
    address public updater;

    constructor(uint256 _initialRate) {
        rate = _initialRate;
        lastUpdated = block.timestamp;
        updater = msg.sender;
    }

    function currentRate() external view returns (uint256, uint256) {
        return (rate, lastUpdated);
    }

    /// @dev VULNERABILITY: Missing access control on rate update
    function adjustRate(uint256 newRate) external {
        rate = newRate;
        lastUpdated = block.timestamp;
    }
}
