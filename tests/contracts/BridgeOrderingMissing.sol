// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IBridgeOrderingOracle {
    function latestAnswer() external view returns (int256);
}

contract BridgeOrderingMissing {
    IBridgeOrderingOracle public bridgeOracle;

    constructor(IBridgeOrderingOracle oracle_) {
        bridgeOracle = oracle_;
    }

    function bridgePrice() external view returns (int256) {
        return bridgeOracle.latestAnswer();
    }
}
