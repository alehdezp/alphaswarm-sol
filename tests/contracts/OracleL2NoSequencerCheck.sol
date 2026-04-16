// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ISequencerFeedRef {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

interface IChainlinkFeedRef {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

contract OracleL2NoSequencerCheck {
    ISequencerFeedRef public sequencer;
    IChainlinkFeedRef public oracle;

    constructor(ISequencerFeedRef sequencer_, IChainlinkFeedRef oracle_) {
        sequencer = sequencer_;
        oracle = oracle_;
    }

    function getPrice() external view returns (int256) {
        (uint80 roundId, int256 price, , uint256 updatedAt, uint80 answeredInRound) = oracle.latestRoundData();
        require(updatedAt >= block.timestamp - 1 hours, "stale");
        require(answeredInRound >= roundId, "bad round");
        return price;
    }
}
