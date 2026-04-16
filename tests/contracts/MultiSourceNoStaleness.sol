// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOracleMultiStale {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract MultiSourceNoStaleness {
    IOracleMultiStale public oracleA;
    IOracleMultiStale public oracleB;

    constructor(IOracleMultiStale a, IOracleMultiStale b) {
        oracleA = a;
        oracleB = b;
    }

    function price() external view returns (int256) {
        (, int256 answerA, , , ) = oracleA.latestRoundData();
        (, int256 answerB, , , ) = oracleB.latestRoundData();
        return (answerA + answerB) / 2;
    }
}
