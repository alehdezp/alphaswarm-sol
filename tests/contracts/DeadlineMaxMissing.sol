// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract DeadlineMaxMissing {
    uint256 public total;

    function swap(uint256 amountIn, uint256 deadline) external {
        require(deadline >= block.timestamp + 1, "deadline");
        total += amountIn;
    }
}
