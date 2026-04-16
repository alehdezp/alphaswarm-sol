// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// RE-SAFE-005: No External Calls
// SAFE: Pure internal accounting, no reentrancy attack surface
contract Vault_10 {
    mapping(address => uint256) public balances;
    mapping(address => uint256) public credits;

    // Internal credit system - no ETH transfers
    function depositCredits(uint256 amount) external {
        // Would normally transfer tokens, but for this test we use internal credits
        credits[msg.sender] += amount;
    }

    // SAFE: no external calls, pure internal accounting
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        credits[msg.sender] += amount; // Convert to credits instead of ETH
    }

    // SAFE: no external calls
    function transfer(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }

    // Allow admin to fund balances (for testing)
    function adminDeposit(address user, uint256 amount) external {
        balances[user] += amount;
    }
}
