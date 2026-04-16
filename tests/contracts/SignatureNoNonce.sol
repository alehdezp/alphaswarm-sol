// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SignatureNoNonce {
    function recover(bytes32 h, uint8 v, bytes32 r, bytes32 s) external pure returns (address) {
        return ecrecover(h, v, r, s);
    }
}
