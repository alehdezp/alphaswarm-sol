// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SignatureValidity {
    function recoverValid(
        bytes32 h,
        uint8 v,
        bytes32 r,
        bytes32 s,
        uint256 deadline
    ) external view returns (address) {
        require(block.timestamp <= deadline, "expired");
        address signer = ecrecover(h, v, r, s);
        require(signer != address(0), "zero");
        return signer;
    }
}
