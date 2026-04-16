// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ICollateralOracle {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract CollateralOracleNoStaleness {
    ICollateralOracle public oracle;

    constructor(ICollateralOracle oracle_) {
        oracle = oracle_;
    }

    function collateralValue(uint256 amount) external view returns (uint256) {
        (, int256 answer, , , ) = oracle.latestRoundData();
        return amount * uint256(answer);
    }
}
