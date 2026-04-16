// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ISequencerFeed {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract SequencerGraceMissing {
    ISequencerFeed public sequencer;
    ISequencerFeed public oracle;

    constructor(ISequencerFeed sequencer_, ISequencerFeed oracle_) {
        sequencer = sequencer_;
        oracle = oracle_;
    }

    function price() external view returns (int256) {
        (, int256 sequencerStatus, , , ) = sequencer.latestRoundData();
        require(sequencerStatus == 0, "sequencer");
        (, int256 priceAnswer, , , ) = oracle.latestRoundData();
        return priceAnswer;
    }
}
