// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Role-based access control pattern
contract RoleBasedAccess {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    mapping(bytes32 => mapping(address => bool)) public roles;
    uint256 public totalSupply;
    bool public paused;

    constructor() {
        roles[ADMIN_ROLE][msg.sender] = true;
    }

    modifier onlyRole(bytes32 role) {
        require(roles[role][msg.sender], "missing role");
        _;
    }

    function grantRole(bytes32 role, address account) external onlyRole(ADMIN_ROLE) {
        roles[role][account] = true;
    }

    function mint(uint256 amount) external onlyRole(MINTER_ROLE) {
        totalSupply += amount;
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        paused = true;
    }
}
