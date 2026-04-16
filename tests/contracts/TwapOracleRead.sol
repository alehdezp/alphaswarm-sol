// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ITwapOracle {
    function consult(address token, uint256 amountIn) external view returns (uint256 amountOut);
}

contract TwapOracleRead {
    ITwapOracle public oracle;

    constructor(ITwapOracle oracle_) {
        oracle = oracle_;
    }

    function price(address token, uint256 amountIn) external view returns (uint256) {
        return oracle.consult(token, amountIn);
    }
}
