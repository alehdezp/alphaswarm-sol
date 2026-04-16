// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IBridgeFinalityOracle {
    function latestAnswer() external view returns (int256);
}

contract BridgeFinalityMissing {
    IBridgeFinalityOracle public bridgeOracle;

    constructor(IBridgeFinalityOracle oracle_) {
        bridgeOracle = oracle_;
    }

    function bridgePrice() external view returns (int256) {
        return bridgeOracle.latestAnswer();
    }
}
