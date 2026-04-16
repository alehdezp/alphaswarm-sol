// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IChainlinkRoundCompleteness {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract ChainlinkRoundCompleteness {
    IChainlinkRoundCompleteness public oracle;

    constructor(IChainlinkRoundCompleteness oracle_) {
        oracle = oracle_;
    }

    function priceNoRoundCheck() external view returns (int256) {
        (, int256 answer, , , ) = oracle.latestRoundData();
        return answer;
    }

    function priceWithRoundCheck() external view returns (int256) {
        (uint80 roundId, int256 answer, , , uint80 answeredInRound) = oracle.latestRoundData();
        require(answeredInRound >= roundId, "round");
        return answer;
    }
}
