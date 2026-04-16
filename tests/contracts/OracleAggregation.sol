// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IChainlinkOracleAgg {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract OracleAggregation {
    IChainlinkOracleAgg public oracleA;
    IChainlinkOracleAgg public oracleB;

    constructor(IChainlinkOracleAgg oracleA_, IChainlinkOracleAgg oracleB_) {
        oracleA = oracleA_;
        oracleB = oracleB_;
    }

    function aggregatePrice() external view returns (int256) {
        (, int256 answerA, , , ) = oracleA.latestRoundData();
        (, int256 answerB, , , ) = oracleB.latestRoundData();
        return (answerA + answerB) / 2;
    }
}
