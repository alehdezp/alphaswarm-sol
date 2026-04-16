// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SignatureChecks {
    function recoverChecked(bytes32 h, uint8 v, bytes32 r, bytes32 s) external pure returns (address) {
        require(v == 27 || v == 28, "bad v");
        require(uint256(s) <= 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0, "bad s");
        address signer = ecrecover(h, v, r, s);
        require(signer != address(0), "zero");
        return signer;
    }
}
