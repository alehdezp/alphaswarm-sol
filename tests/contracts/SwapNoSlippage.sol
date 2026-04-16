// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SwapNoSlippage {
    function swap(uint256 amountIn, uint256 amountOutMin, uint256 deadline) external view returns (uint256) {
        uint256 amountOut = amountIn;
        return amountOut;
    }
}
