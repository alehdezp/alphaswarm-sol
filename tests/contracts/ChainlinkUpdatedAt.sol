// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IChainlinkUpdatedAtFeed {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract ChainlinkUpdatedAt {
    IChainlinkUpdatedAtFeed public oracle;
    uint256 public maxDelay = 1 hours;

    constructor(IChainlinkUpdatedAtFeed oracle_) {
        oracle = oracle_;
    }

    function priceNoUpdatedAt() external view returns (int256) {
        (, int256 answer, , , ) = oracle.latestRoundData();
        return answer;
    }

    function priceWithUpdatedAt() external view returns (int256) {
        (, int256 answer, , uint256 updatedAt, ) = oracle.latestRoundData();
        require(block.timestamp - updatedAt <= maxDelay, "updated");
        return answer;
    }
}
