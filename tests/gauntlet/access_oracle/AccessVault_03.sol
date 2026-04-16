// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AccessVault_03 - VULNERABLE
 * @dev Ownership manipulation - No two-step transfer, front-running risk.
 * @notice Case ID: AC-VULN-003
 *
 * VULNERABILITY: transferOwnership() is single-step without confirmation.
 * Front-running or social engineering can transfer ownership to attacker.
 */

contract AccessVault_03 {
    address public owner;
    mapping(address => uint256) public balances;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // VULNERABILITY: Single-step ownership transfer
    // No pending owner confirmation - immediate transfer
    // Susceptible to front-running and address errors
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Invalid address");
        // Missing: pendingOwner = newOwner; + acceptOwnership()
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;  // Immediate transfer without confirmation
    }

    function renounceOwnership() public onlyOwner {
        // VULNERABILITY: No timelock or multi-sig requirement
        emit OwnershipTransferred(owner, address(0));
        owner = address(0);
    }

    function emergencyWithdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }
}
