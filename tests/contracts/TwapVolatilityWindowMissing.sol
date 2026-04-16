// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ITwapVolOracle {
    function consult(address token, uint32 secondsAgo) external view returns (uint256);
}

contract TwapVolatilityWindowMissing {
    ITwapVolOracle public oracle;

    constructor(ITwapVolOracle oracle_) {
        oracle = oracle_;
    }

    function twap(address token, uint32 window) external view returns (uint256) {
        return oracle.consult(token, window);
    }
}
