// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IChainlinkSingle {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract OracleSingleSourceMultipleCalls {
    IChainlinkSingle public oracle;

    constructor(IChainlinkSingle oracle_) {
        oracle = oracle_;
    }

    function doubleRead() external view returns (int256) {
        (, int256 a, , , ) = oracle.latestRoundData();
        (, int256 b, , , ) = oracle.latestRoundData();
        return (a + b) / 2;
    }
}
