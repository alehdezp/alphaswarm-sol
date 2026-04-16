// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IPriceFeed {
    function latestPrice() external view returns (uint256 price, uint256 timestamp);
    function decimals() external view returns (uint8);
}
