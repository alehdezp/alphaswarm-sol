// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication based on extcodesize.
contract WeakAuthExtcodesize {
    function privileged(address user) external view returns (bool) {
        uint256 size;
        assembly {
            size := extcodesize(user)
        }
        require(size == 0, "not EOA");
        return true;
    }
}
