// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IL2Oracle {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract L2Finality {
    IL2Oracle public l2Oracle;
    uint256 public finalityDelay;
    uint256 public lastUpdate;

    constructor(IL2Oracle oracle_, uint256 finalityDelay_) {
        l2Oracle = oracle_;
        finalityDelay = finalityDelay_;
    }

    function priceNoFinality() external view returns (int256) {
        (, int256 answer, , , ) = l2Oracle.latestRoundData();
        return answer;
    }

    function priceWithFinality() external view returns (int256) {
        require(block.timestamp >= lastUpdate + finalityDelay, "finality");
        (, int256 answer, , , ) = l2Oracle.latestRoundData();
        return answer;
    }
}
