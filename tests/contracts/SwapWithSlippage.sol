// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SwapWithSlippage {
    function swap(uint256 amountIn, uint256 amountOutMin, uint256 deadline) external view returns (uint256) {
        require(block.timestamp <= deadline, "expired");
        uint256 amountOut = amountIn;
        require(amountOut >= amountOutMin, "slippage");
        return amountOut;
    }
}
