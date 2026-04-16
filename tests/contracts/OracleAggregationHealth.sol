// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOracleHealth {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract OracleAggregationHealth {
    IOracleHealth public oracleA;
    IOracleHealth public oracleB;

    constructor(IOracleHealth a, IOracleHealth b) {
        oracleA = a;
        oracleB = b;
    }

    function aggregate() external view returns (int256) {
        (, int256 answerA, , , ) = oracleA.latestRoundData();
        (, int256 answerB, , , ) = oracleB.latestRoundData();
        return (answerA + answerB) / 2;
    }
}
