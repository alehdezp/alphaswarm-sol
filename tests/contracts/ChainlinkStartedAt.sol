// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IChainlinkStartedAtFeed {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract ChainlinkStartedAt {
    IChainlinkStartedAtFeed public oracle;

    constructor(IChainlinkStartedAtFeed oracle_) {
        oracle = oracle_;
    }

    function priceNoStartedAtCheck() external view returns (int256) {
        (, int256 answer, , , ) = oracle.latestRoundData();
        return answer;
    }

    function priceWithStartedAtCheck() external view returns (int256) {
        (, int256 answer, uint256 startedAt, , ) = oracle.latestRoundData();
        require(startedAt > 0, "started");
        return answer;
    }
}
