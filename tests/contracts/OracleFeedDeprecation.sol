// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IChainlinkFeed {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract OracleFeedDeprecation {
    IChainlinkFeed public oracle;

    constructor(IChainlinkFeed oracle_) {
        oracle = oracle_;
    }

    function readPrice() external view returns (int256) {
        (, int256 answer, , , ) = oracle.latestRoundData();
        return answer;
    }
}
