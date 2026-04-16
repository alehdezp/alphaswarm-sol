// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IPriceOracle {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );

    // Alternative naming
    function getCurrentPrice() external view returns (int256);
    function fetchLatestValue() external view returns (int256, uint256);
}

contract OracleTest {
    IPriceOracle public oracle;

    // Should be detected - uses standard Chainlink function
    function getPrice1() external view returns (int256) {
        (,int256 price,,,) = oracle.latestRoundData();
        return price;
    }

    // Should be detected - uses alternative naming (if READS_ORACLE is semantic)
    function getPrice2() external view returns (int256) {
        return oracle.getCurrentPrice();
    }

    // Should be detected - uses alternative naming
    function getPrice3() external view returns (int256) {
        (int256 value,) = oracle.fetchLatestValue();
        return value;
    }

    // Has staleness check
    function getPriceWithStalenessCheck() external view returns (int256) {
        (,int256 price,,uint256 updatedAt,) = oracle.latestRoundData();
        require(updatedAt > block.timestamp - 3600, "Stale price");
        return price;
    }

    // Missing staleness check
    function getPriceNoStalenessCheck() external view returns (int256) {
        (,int256 price,,,) = oracle.latestRoundData();
        return price;
    }
}
