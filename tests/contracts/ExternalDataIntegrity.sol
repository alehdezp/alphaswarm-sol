// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract ExternalDataIntegrity {
    bytes32 public lastPayloadHash;

    function submit(bytes calldata payload) external {
        lastPayloadHash = keccak256(payload);
    }
}
