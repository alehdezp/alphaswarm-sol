// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig execution with nonce parameter but no state update.
contract MultisigExecuteNonceNoUpdate {
    uint256 public nonce;

    function execute(address target, bytes calldata data, uint256 nonceParam) external {
        nonceParam;
        (bool ok, ) = target.call(data);
        require(ok, "call failed");
    }
}
