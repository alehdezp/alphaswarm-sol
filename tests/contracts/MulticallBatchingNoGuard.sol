// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multicall batching without reentrancy guard.
contract MulticallBatchingNoGuard {
    function multicall(address target, bytes[] calldata calls) external {
        for (uint256 i = 0; i < calls.length; i++) {
            (bool ok, ) = target.call(calls[i]);
            require(ok, "call failed");
        }
    }
}
