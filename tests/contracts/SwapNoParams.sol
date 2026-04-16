// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SwapNoParams {
    uint256 public lastAmountIn;

    function swap(uint256 amountIn) external returns (uint256) {
        lastAmountIn = amountIn;
        return amountIn;
    }
}
