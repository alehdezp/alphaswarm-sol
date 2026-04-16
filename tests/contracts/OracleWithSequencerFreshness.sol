// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ISequencerFeed {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

interface IChainlinkFeed {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

contract OracleWithSequencerFreshness {
    ISequencerFeed public sequencer;
    IChainlinkFeed public oracle;
    uint256 public constant GRACE_PERIOD = 3600;

    constructor(ISequencerFeed sequencer_, IChainlinkFeed oracle_) {
        sequencer = sequencer_;
        oracle = oracle_;
    }

    function getPrice() external view returns (int256) {
        (, int256 answer, , uint256 updatedAt, ) = sequencer.latestRoundData();
        require(answer == 0, "sequencer down");
        require(block.timestamp - updatedAt > GRACE_PERIOD, "grace");

        (uint80 roundId, int256 price, , uint256 oracleUpdatedAt, uint80 answeredInRound) = oracle.latestRoundData();
        require(oracleUpdatedAt >= block.timestamp - 1 hours, "stale");
        require(answeredInRound >= roundId, "bad round");
        return price;
    }
}
