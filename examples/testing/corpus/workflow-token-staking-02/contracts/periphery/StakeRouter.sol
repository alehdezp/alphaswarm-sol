// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IStakeEngine.sol";

/// @title StakeRouter - Multi-pool staking router
contract StakeRouter {
    IStakeEngine[] public pools;
    address public governance;
    mapping(address => bool) public approvedPools;

    constructor() {
        governance = msg.sender;
    }

    /// @notice Add a staking pool
    /// @dev VULNERABILITY: Missing access control
    function addPool(address pool) external {
        pools.push(IStakeEngine(pool));
        approvedPools[pool] = true;
    }

    /// @notice Stake across multiple pools equally
    function multiStake() external payable {
        require(pools.length > 0, "No pools");
        uint256 perPool = msg.value / pools.length;
        for (uint256 i = 0; i < pools.length; i++) {
            pools[i].stake{value: perPool}();
        }
    }

    /// @notice Remove pool
    function removePool(uint256 index) external {
        require(msg.sender == governance, "Not governance");
        require(index < pools.length, "Invalid index");
        approvedPools[address(pools[index])] = false;
        pools[index] = pools[pools.length - 1];
        pools.pop();
    }

    receive() external payable {}
}
