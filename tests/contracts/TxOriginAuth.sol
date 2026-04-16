// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TxOriginAuth {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function privileged() external {
        require(tx.origin == owner, "auth");
    }
}
