// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Single owner can drain funds without timelock or multisig.
contract SinglePointOfFailure {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function drain(address payable to, uint256 amount) external {
        require(msg.sender == owner, "not owner");
        to.transfer(amount);
    }
}
