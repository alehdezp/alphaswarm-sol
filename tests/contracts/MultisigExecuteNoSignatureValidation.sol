// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig execution without signature validation.
contract MultisigExecuteNoSignatureValidation {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function execute(address target, bytes calldata data) external onlyOwner {
        (bool ok, ) = target.call(data);
        require(ok, "call failed");
    }
}
