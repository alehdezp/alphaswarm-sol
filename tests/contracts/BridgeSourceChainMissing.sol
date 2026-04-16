// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IBridgeSourceOracle {
    function latestAnswer() external view returns (int256);
}

contract BridgeSourceChainMissing {
    IBridgeSourceOracle public bridgeOracle;

    constructor(IBridgeSourceOracle oracle_) {
        bridgeOracle = oracle_;
    }

    function bridgePrice() external view returns (int256) {
        return bridgeOracle.latestAnswer();
    }
}
