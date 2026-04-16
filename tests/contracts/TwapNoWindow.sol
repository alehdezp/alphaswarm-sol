// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ITwapOracleNoWindow {
    function consult(address token, uint256 amountIn) external view returns (uint256 amountOut);
}

contract TwapNoWindow {
    ITwapOracleNoWindow public oracle;

    constructor(ITwapOracleNoWindow oracle_) {
        oracle = oracle_;
    }

    function price(address token, uint256 amountIn) external view returns (uint256) {
        return oracle.consult(token, amountIn);
    }
}
