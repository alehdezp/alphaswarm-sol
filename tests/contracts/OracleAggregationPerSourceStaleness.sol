// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOraclePerSourceStale {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract OracleAggregationPerSourceStaleness {
    IOraclePerSourceStale public oracleA;
    IOraclePerSourceStale public oracleB;

    constructor(IOraclePerSourceStale a, IOraclePerSourceStale b) {
        oracleA = a;
        oracleB = b;
    }

    function aggregate() external view returns (int256) {
        (, int256 answerA, , uint256 updatedAt, ) = oracleA.latestRoundData();
        (, int256 answerB, , , ) = oracleB.latestRoundData();
        require(updatedAt > 0, "updated");
        return (answerA + answerB) / 2;
    }
}
