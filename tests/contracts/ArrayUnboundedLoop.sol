// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract ArrayUnboundedLoop {
    uint256 public total;

    function sum(uint256[] calldata values, uint256 limit) external {
        for (uint256 i = 0; i < limit; i++) {
            total += values[i];
        }
    }
}
