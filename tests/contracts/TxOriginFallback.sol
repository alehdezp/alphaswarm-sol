// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// tx.origin used in fallback/receive.
contract TxOriginFallback {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    receive() external payable {
        require(tx.origin == owner, "not owner");
    }

    fallback() external payable {
        require(tx.origin == owner, "not owner");
    }
}
