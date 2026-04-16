// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CustomAccessGate {
    address public admin;
    uint256 public feeBps;

    constructor() {
        admin = msg.sender;
    }

    function setFee(uint256 newFee) external {
        require(msg.sender == admin, "not admin");
        feeBps = newFee;
    }
}
