// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title PolicyOracle (SAFE VARIANT)
contract PolicyOracle_safe {
    uint256 public rate;
    uint256 public lastUpdated;
    address public updater;

    modifier onlyUpdater() { require(msg.sender == updater, "Not updater"); _; }

    constructor(uint256 _initialRate) { rate = _initialRate; lastUpdated = block.timestamp; updater = msg.sender; }

    function currentRate() external view returns (uint256, uint256) { return (rate, lastUpdated); }

    function adjustRate(uint256 newRate) external onlyUpdater {
        rate = newRate;
        lastUpdated = block.timestamp;
    }
}
