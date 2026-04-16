// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ITwapTimestampPool {
    function observe(uint32[] calldata secondsAgos) external view returns (int56[] memory, uint160[] memory);
}

contract TwapTimestampMissing {
    ITwapTimestampPool public pool;

    constructor(ITwapTimestampPool pool_) {
        pool = pool_;
    }

    function twap(uint32 secondsAgo) external view returns (int56) {
        uint32[] memory secondsAgos = new uint32[](1);
        secondsAgos[0] = secondsAgo;
        (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);
        return tickCumulatives[0];
    }
}
