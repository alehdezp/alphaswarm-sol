// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IChainlinkDecimalsFeed {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
    function decimals() external view returns (uint8);
}

contract ChainlinkDecimals {
    IChainlinkDecimalsFeed public oracle;

    constructor(IChainlinkDecimalsFeed oracle_) {
        oracle = oracle_;
    }

    function priceAssume8Decimals() external view returns (uint256) {
        (, int256 answer, , , ) = oracle.latestRoundData();
        return uint256(answer) * 1e8;
    }

    function priceWithDecimals() external view returns (uint256) {
        (, int256 answer, , , ) = oracle.latestRoundData();
        uint8 decimals = oracle.decimals();
        return uint256(answer) * (10 ** uint256(decimals));
    }
}
