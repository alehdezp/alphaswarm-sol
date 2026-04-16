// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IOracleL1L2 {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract CrossChainOracle {
    IOracleL1L2 public l1Oracle;
    IOracleL1L2 public l2Oracle;

    constructor(IOracleL1L2 l1Oracle_, IOracleL1L2 l2Oracle_) {
        l1Oracle = l1Oracle_;
        l2Oracle = l2Oracle_;
    }

    function crossChainPrice() external view returns (int256) {
        (, int256 answer, , , ) = l2Oracle.latestRoundData();
        return answer;
    }
}
