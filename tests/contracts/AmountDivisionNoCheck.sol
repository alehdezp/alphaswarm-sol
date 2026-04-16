// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract AmountDivisionNoCheck {
    function ratio(uint256 amount, uint256 amountTotal) external pure returns (uint256) {
        return amount / amountTotal;
    }

    function ratioChecked(uint256 amount, uint256 amountTotal) external pure returns (uint256) {
        require(amountTotal > 0, "total");
        return amount / amountTotal;
    }
}
