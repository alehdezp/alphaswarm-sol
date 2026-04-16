// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Vulnerable: callers can assign themselves privileged roles.
contract PrivilegeEscalation {
    mapping(address => bool) public admins;

    function grantAdmin() external {
        admins[msg.sender] = true;
    }

    function adminAction() external {
        require(admins[msg.sender], "not admin");
    }
}
