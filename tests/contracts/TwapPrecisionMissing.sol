// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ITwapPrecisionOracle {
    function consult(address token, uint32 secondsAgo) external view returns (uint256);
}

contract TwapPrecisionMissing {
    ITwapPrecisionOracle public oracle;

    constructor(ITwapPrecisionOracle oracle_) {
        oracle = oracle_;
    }

    function twap(address token, uint32 window) external view returns (uint256) {
        return oracle.consult(token, window);
    }
}
