// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOracleMultiDecimals {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract MultiSourceNoDecimals {
    IOracleMultiDecimals public oracleA;
    IOracleMultiDecimals public oracleB;

    constructor(IOracleMultiDecimals a, IOracleMultiDecimals b) {
        oracleA = a;
        oracleB = b;
    }

    function price() external view returns (int256) {
        (, int256 answerA, , , ) = oracleA.latestRoundData();
        (, int256 answerB, , , ) = oracleB.latestRoundData();
        return (answerA + answerB) / 2;
    }
}
