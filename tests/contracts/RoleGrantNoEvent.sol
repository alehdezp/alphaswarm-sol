// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Role grant without event emission.
contract RoleGrantNoEvent {
    mapping(address => bool) public roles;

    function grantRole(address account) external {
        roles[account] = true;
    }
}
