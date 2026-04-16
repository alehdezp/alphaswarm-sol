// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AbiDecodeCalldataLength {
    // Vulnerable: decodes without checking calldata length.
    function decodeUnsafe(bytes calldata data) external pure returns (uint256 value) {
        value = abi.decode(data, (uint256));
    }

    // Safe: validates calldata length before decoding.
    function decodeSafe(bytes calldata data) external pure returns (uint256 value) {
        require(data.length >= 32, "length");
        value = abi.decode(data, (uint256));
    }
}
