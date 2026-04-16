// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication based on block.number.
contract WeakAuthBlockNumber {
    function privileged(uint256 minBlock) external view returns (bool) {
        require(block.number >= minBlock, "too early");
        return true;
    }
}
