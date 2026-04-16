// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Role grant/revoke without access control.
contract RoleGrantRevokeNoGate {
    mapping(address => bool) public roles;

    function grantRole(address account) external {
        roles[account] = true;
    }

    function revokeRole(address account) external {
        roles[account] = false;
    }
}
