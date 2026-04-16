// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Multisig signer removal without minimum signer check.
contract MultisigSignerRemoveNoMinCheck {
    address public owner;
    address[] public owners;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function removeSigner(uint256 index) external onlyOwner {
        owners[index] = owners[owners.length - 1];
        owners.pop();
    }
}
