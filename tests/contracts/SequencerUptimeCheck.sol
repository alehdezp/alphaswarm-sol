// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ISequencerUptime {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

contract SequencerUptimeCheck {
    ISequencerUptime public sequencer;
    uint256 public constant GRACE_PERIOD = 3600;

    constructor(ISequencerUptime sequencer_) {
        sequencer = sequencer_;
    }

    function check() external view {
        (, int256 answer, , uint256 updatedAt, ) = sequencer.latestRoundData();
        require(answer == 0, "sequencer down");
        require(block.timestamp - updatedAt > GRACE_PERIOD, "grace");
    }
}
