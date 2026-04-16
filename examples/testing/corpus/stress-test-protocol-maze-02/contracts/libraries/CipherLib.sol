// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title CipherLib - Byte manipulation utilities
library CipherLib {
    /// @notice Extract operation code from encoded data
    function extractOpCode(bytes memory data) internal pure returns (bytes4) {
        require(data.length >= 4, "Data too short");
        bytes4 opCode;
        assembly {
            opCode := mload(add(data, 32))
        }
        return opCode;
    }

    /// @notice Compute deterministic ID
    function computeId(bytes memory data, uint256 nonce) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(data, nonce));
    }
}
