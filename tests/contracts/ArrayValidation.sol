// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract ArrayValidation {
    uint256[] public values;

    function setAt(uint256 index, uint256 value) external {
        values[index] = value;
    }

    function setAtChecked(uint256 index, uint256 value) external {
        require(index < values.length, "bounds");
        values[index] = value;
    }

    function pick(address[] calldata recipients, uint256 index) external pure returns (address) {
        return recipients[index];
    }

    function pickChecked(address[] calldata recipients, uint256 index) external pure returns (address) {
        require(index < recipients.length, "bounds");
        return recipients[index];
    }

    function batch(address[] calldata recipients, uint256[] calldata amounts) external pure returns (uint256) {
        uint256 total;
        for (uint256 i = 0; i < recipients.length; i++) {
            total += amounts[i];
        }
        return total;
    }

    function batchChecked(address[] calldata recipients, uint256[] calldata amounts) external pure returns (uint256) {
        require(recipients.length == amounts.length, "len");
        uint256 total;
        for (uint256 i = 0; i < recipients.length; i++) {
            total += amounts[i];
        }
        return total;
    }
}
