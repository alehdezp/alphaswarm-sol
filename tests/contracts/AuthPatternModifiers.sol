// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Contract with various auth pattern modifiers
contract AuthPatternModifiers {
    address public owner;
    address public admin;
    mapping(address => bool) public allowlist;

    constructor() {
        owner = msg.sender;
        admin = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "not admin");
        _;
    }

    modifier onlyAllowlisted() {
        require(allowlist[msg.sender], "not allowlisted");
        _;
    }

    function setOwner(address newOwner) external onlyOwner {
        owner = newOwner;
    }

    function setAdmin(address newAdmin) external onlyOwner {
        admin = newAdmin;
    }

    function updateConfig(uint256 value) external onlyAdmin {
        // privileged operation
    }

    function restrictedAction() external onlyAllowlisted {
        // restricted operation
    }
}
