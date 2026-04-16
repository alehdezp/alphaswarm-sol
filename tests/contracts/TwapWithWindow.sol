// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ITwapOracleWindow {
    function observe(uint32 secondsAgo) external view returns (int56 tickCumulative, uint160 secondsPerLiquidityCumulativeX128);
}

contract TwapWithWindow {
    ITwapOracleWindow public oracle;

    constructor(ITwapOracleWindow oracle_) {
        oracle = oracle_;
    }

    function price(uint32 secondsAgo) external view returns (int56) {
        (int56 tick, ) = oracle.observe(secondsAgo);
        return tick;
    }
}
