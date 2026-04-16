// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract DurationValidation {
    uint256 public maxLock = 30 days;

    function lock(uint256 duration) external pure returns (uint256) {
        return duration + 1;
    }

    function lockChecked(uint256 duration) external view returns (uint256) {
        require(duration >= 1 days, "min");
        require(duration <= maxLock, "max");
        return duration + 1;
    }
}
