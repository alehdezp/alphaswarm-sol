// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract DeadlineFutureMissing {
    uint256 public total;

    function swap(uint256 amountIn, uint256 deadline) external {
        total += amountIn;
        deadline;
    }
}
