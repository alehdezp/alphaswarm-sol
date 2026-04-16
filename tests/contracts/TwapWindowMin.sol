// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ITwapConsult {
    function consult(address token, uint32 secondsAgo) external view returns (uint256);
}

contract TwapWindowMin {
    ITwapConsult public oracle;
    uint32 public minWindow = 60;

    constructor(ITwapConsult oracle_) {
        oracle = oracle_;
    }

    function twapNoMin(address token, uint32 window) external view returns (uint256) {
        return oracle.consult(token, window);
    }

    function twapWithMin(address token, uint32 window) external view returns (uint256) {
        require(window >= minWindow, "min");
        return oracle.consult(token, window);
    }
}
