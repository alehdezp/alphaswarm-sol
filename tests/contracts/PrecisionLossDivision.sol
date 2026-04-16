// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract PrecisionLossDivision {
    uint256 public price = 3;
    uint256 public precision = 1e18;

    // Vulnerable: division without precision guard.
    function quote(uint256 amount) external view returns (uint256) {
        return amount / price;
    }

    // Safe: precision guard included in math.
    function quoteWithPrecision(uint256 amount) external view returns (uint256) {
        require(precision > 0, "precision");
        return amount * precision / price;
    }
}
