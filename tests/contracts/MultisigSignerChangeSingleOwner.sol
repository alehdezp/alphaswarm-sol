// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig signer change controlled by single owner.
contract MultisigSignerChangeSingleOwner {
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
