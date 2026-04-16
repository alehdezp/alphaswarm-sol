// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ArrayLengthValidation {
    uint256 public total;

    // Vulnerable: no length check between arrays.
    function batchUpdate(address[] calldata accounts, uint256[] calldata amounts) external {
        for (uint256 i = 0; i < accounts.length; i++) {
            total += amounts[i];
        }
    }

    // Safe: enforces length match.
    function batchUpdateSafe(address[] calldata accounts, uint256[] calldata amounts) external {
        require(accounts.length == amounts.length, "length");
        for (uint256 i = 0; i < accounts.length; i++) {
            total += amounts[i];
        }
    }

    // Vulnerable: index access without bounds check.
    function atUnsafe(uint256[] calldata values, uint256 index) external pure returns (uint256) {
        return values[index];
    }

    // Safe: validates index bounds.
    function atSafe(uint256[] calldata values, uint256 index) external pure returns (uint256) {
        require(index < values.length, "index");
        return values[index];
    }
}
