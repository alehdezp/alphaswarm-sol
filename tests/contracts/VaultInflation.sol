// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VaultInflation {
    /// @notice Invariant: totalAssets >= totalDeposits.
    uint256 public totalAssets;
    uint256 public totalDeposits;

    function deposit(uint256 amount) external {
        totalAssets += amount;
        totalDeposits += amount;
        require(totalAssets >= totalDeposits, "invariant");
    }

    function skim(uint256 amount) external {
        totalAssets -= amount;
    }
}
