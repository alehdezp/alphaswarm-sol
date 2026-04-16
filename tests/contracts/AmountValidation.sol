// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract AmountValidation {
    uint256 public total;
    uint256 public maxAmount = 1000;

    function deposit(uint256 amount) external {
        total += amount;
    }

    function depositChecked(uint256 amount) external {
        require(amount > 0, "zero");
        require(amount <= maxAmount, "max");
        total += amount;
    }
}
