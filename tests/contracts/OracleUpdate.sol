// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract OracleUpdate {
    int256 public price;

    function setPrice(int256 newPrice) external {
        price = newPrice;
    }
}
