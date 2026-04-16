// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IStakeEngine.sol";

/// @title StakeRouter (SAFE VARIANT)
contract StakeRouter_safe {
    IStakeEngine[] public pools;
    address public governance;
    mapping(address => bool) public approvedPools;

    modifier onlyGovernance() {
        require(msg.sender == governance, "Not governance");
        _;
    }

    constructor() { governance = msg.sender; }

    function addPool(address pool) external onlyGovernance {
        pools.push(IStakeEngine(pool));
        approvedPools[pool] = true;
    }

    function multiStake() external payable {
        require(pools.length > 0, "No pools");
        uint256 perPool = msg.value / pools.length;
        for (uint256 i = 0; i < pools.length; i++) {
            pools[i].stake{value: perPool}();
        }
    }

    function removePool(uint256 index) external onlyGovernance {
        require(index < pools.length, "Invalid index");
        approvedPools[address(pools[index])] = false;
        pools[index] = pools[pools.length - 1];
        pools.pop();
    }

    receive() external payable {}
}
