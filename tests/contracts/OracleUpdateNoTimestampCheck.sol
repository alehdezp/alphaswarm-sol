// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract OracleUpdateNoTimestampCheck {
    uint256 public price;

    function setPrice(uint256 newPrice) external {
        price = newPrice;
    }
}
