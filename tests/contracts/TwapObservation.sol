// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ITwapPool {
    function observe(uint32[] calldata secondsAgos) external view returns (int56[] memory, uint160[] memory);
    function observationCardinality() external view returns (uint16);
}

contract TwapObservation {
    ITwapPool public pool;

    constructor(ITwapPool pool_) {
        pool = pool_;
    }

    function twapNoObservation(uint32 secondsAgo) external view returns (int56) {
        uint32[] memory secondsAgos = new uint32[](1);
        secondsAgos[0] = secondsAgo;
        (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);
        return tickCumulatives[0];
    }

    function twapChecked(uint32 secondsAgo) external view returns (int56) {
        uint16 cardinality = pool.observationCardinality();
        require(cardinality > 1, "obs");
        uint32[] memory secondsAgos = new uint32[](1);
        secondsAgos[0] = secondsAgo;
        (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);
        return tickCumulatives[0];
    }
}
