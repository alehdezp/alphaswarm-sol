// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IChainlinkOracle {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

contract OracleNoStaleness {
    IChainlinkOracle public oracle;

    constructor(IChainlinkOracle oracle_) {
        oracle = oracle_;
    }

    function getPrice() external view returns (int256) {
        (, int256 answer, , , ) = oracle.latestRoundData();
        return answer;
    }
}
