// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOracleLiquidation {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract LiquidationOracleStale {
    IOracleLiquidation public oracle;

    constructor(IOracleLiquidation oracle_) {
        oracle = oracle_;
    }

    function liquidate(address account, uint256 amount) external view returns (uint256) {
        account;
        (, int256 answer, , , ) = oracle.latestRoundData();
        return amount * uint256(answer);
    }
}
