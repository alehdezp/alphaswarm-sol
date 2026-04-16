// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Public payable entrypoint without access control.
contract PublicPayableNoGate {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }
}
