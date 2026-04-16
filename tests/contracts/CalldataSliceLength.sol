// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CalldataSliceLength {
    // Vulnerable: slices calldata without length check.
    function decodeUnsafe(bytes calldata data) external pure returns (bytes4 selector) {
        selector = bytes4(data[0:4]);
    }

    // Safe: validates length before slicing.
    function decodeSafe(bytes calldata data) external pure returns (bytes4 selector) {
        require(data.length >= 4, "length");
        selector = bytes4(data[0:4]);
    }
}
