// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AccessVault_02 - VULNERABLE
 * @dev Delegatecall target control - User-controlled address in delegatecall.
 * @notice Case ID: AC-VULN-002
 *
 * VULNERABILITY: execute() takes user-controlled target for delegatecall.
 * Attacker can pass malicious contract and execute arbitrary code in this context.
 */

contract AccessVault_02 {
    address public owner;
    mapping(address => uint256) public balances;
    uint256 public totalDeposits;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    // VULNERABILITY: User-controlled target for delegatecall
    // Attacker can execute arbitrary code in the context of this contract
    function execute(address target, bytes calldata data) external returns (bytes memory) {
        // Missing: require(allowedTargets[target], "Target not whitelisted");
        // This allows any contract to be called via delegatecall
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success, "Delegatecall failed");
        return result;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        totalDeposits -= amount;
        payable(msg.sender).transfer(amount);
    }

    receive() external payable {
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }
}
