// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig signer changes without non-zero validation.
contract MultisigSignerChangeNoValidation {
    address public owner;
    address[] public owners;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function addSigner(address newSigner) external onlyOwner {
        owners.push(newSigner);
    }
}
