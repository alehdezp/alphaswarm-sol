// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract InitializerGuarded {
    address public owner;
    bool public initialized;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function initialize(address _owner) external onlyOwner {
        require(!initialized, "already initialized");
        owner = _owner;
        initialized = true;
    }
}
