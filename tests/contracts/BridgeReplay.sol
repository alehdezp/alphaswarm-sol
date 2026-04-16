// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface IBridgeOracle {
    function latestAnswer() external view returns (int256);
}

contract BridgeReplay {
    IBridgeOracle public bridgeOracle;
    uint256 public expectedNonce;

    constructor(IBridgeOracle oracle_) {
        bridgeOracle = oracle_;
    }

    function bridgePrice(bytes calldata message) external view returns (int256) {
        message;
        return bridgeOracle.latestAnswer();
    }

    function bridgePriceChecked(bytes calldata message, uint256 nonce) external view returns (int256) {
        message;
        require(nonce == expectedNonce, "nonce");
        return bridgeOracle.latestAnswer();
    }
}
