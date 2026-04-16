// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ICrossChainFeed {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract CrossChainConsistency {
    ICrossChainFeed public l1Oracle;
    ICrossChainFeed public l2Oracle;

    constructor(ICrossChainFeed l1, ICrossChainFeed l2) {
        l1Oracle = l1;
        l2Oracle = l2;
    }

    function l2Price() external view returns (int256) {
        (, int256 answer, , , ) = l2Oracle.latestRoundData();
        return answer;
    }
}
