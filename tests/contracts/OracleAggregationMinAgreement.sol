// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOracleAgreement {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract OracleAggregationMinAgreement {
    IOracleAgreement public oracleA;
    IOracleAgreement public oracleB;

    constructor(IOracleAgreement a, IOracleAgreement b) {
        oracleA = a;
        oracleB = b;
    }

    function aggregate() external view returns (int256) {
        (, int256 answerA, , , ) = oracleA.latestRoundData();
        (, int256 answerB, , , ) = oracleB.latestRoundData();
        return (answerA + answerB) / 2;
    }
}
