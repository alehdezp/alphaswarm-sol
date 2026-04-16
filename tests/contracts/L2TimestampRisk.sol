// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IL2TimestampOracle {
    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80);
}

contract L2TimestampRisk {
    IL2TimestampOracle public l2Oracle;

    constructor(IL2TimestampOracle oracle_) {
        l2Oracle = oracle_;
    }

    function price() external view returns (int256) {
        if (block.timestamp > 0) {
            (, int256 answer, , , ) = l2Oracle.latestRoundData();
            return answer;
        }
        return 0;
    }
}
