// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract AmountPrecision {
    uint256 public precision = 1e18;

    function quoteNoGuard(uint256 amount, uint256 price) external pure returns (uint256) {
        return amount / price;
    }

    function quoteWithPrecision(uint256 amount, uint256 price) external view returns (uint256) {
        require(precision > 0, "precision");
        return (amount * precision) / price;
    }
}
