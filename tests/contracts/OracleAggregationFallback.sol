// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOracleFallback {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract OracleAggregationFallback {
    IOracleFallback public oracleA;
    IOracleFallback public oracleB;

    constructor(IOracleFallback a, IOracleFallback b) {
        oracleA = a;
        oracleB = b;
    }

    function aggregate() external view returns (int256) {
        (, int256 answerA, , , ) = oracleA.latestRoundData();
        (, int256 answerB, , , ) = oracleB.latestRoundData();
        return (answerA + answerB) / 2;
    }
}
