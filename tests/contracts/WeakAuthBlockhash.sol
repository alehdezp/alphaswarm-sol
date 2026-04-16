// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication based on blockhash.
contract WeakAuthBlockhash {
    function privileged(bytes32 expected) external view returns (bool) {
        require(blockhash(block.number - 1) == expected, "no match");
        return true;
    }
}
