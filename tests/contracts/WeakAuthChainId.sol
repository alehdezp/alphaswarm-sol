// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Weak authentication based on chain id.
contract WeakAuthChainId {
    function privileged(uint256 allowedChainId) external view returns (bool) {
        require(block.chainid == allowedChainId, "wrong chain");
        return true;
    }
}
