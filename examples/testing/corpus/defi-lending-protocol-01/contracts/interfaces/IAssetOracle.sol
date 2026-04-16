// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IAssetOracle {
    function getLatestValue() external view returns (uint256 value, uint256 updatedAt);
    function precision() external view returns (uint8);
}
