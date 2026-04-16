// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TotalSupplyInvariant {
    /// @notice Invariant: totalSupply equals sum of balances.
    uint256 public totalSupply;
    mapping(address => uint256) public balances;

    function mint(address to, uint256 amount) external {
        balances[to] += amount;
        totalSupply += amount;
        require(totalSupply >= balances[to], "invariant");
    }

    function burn(address from, uint256 amount) external {
        balances[from] -= amount;
        totalSupply -= amount;
    }
}
