// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOracleWithUpdatedAt {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract OracleStalenessThreshold {
    IOracleWithUpdatedAt public oracle;
    uint256 public maxDelay = 1 hours;

    constructor(IOracleWithUpdatedAt oracle_) {
        oracle = oracle_;
    }

    function priceNoThreshold() external view returns (int256) {
        (, int256 answer, , uint256 updatedAt, ) = oracle.latestRoundData();
        require(updatedAt > 0, "updated");
        return answer;
    }

    function priceWithThreshold() external view returns (int256) {
        (, int256 answer, , uint256 updatedAt, ) = oracle.latestRoundData();
        require(block.timestamp - updatedAt <= maxDelay, "stale");
        return answer;
    }
}
