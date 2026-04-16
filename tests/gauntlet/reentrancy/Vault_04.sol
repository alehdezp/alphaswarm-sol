// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// RE-SAFE-002: Uses Pull Pattern
// SAFE: Two-step withdrawal eliminates reentrancy vector
contract Vault_04 {
    mapping(address => uint256) public balances;
    mapping(address => uint256) public pendingWithdrawals;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // Step 1: Initiate withdrawal (no external call)
    function initiateWithdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        pendingWithdrawals[msg.sender] += amount;
    }

    // Step 2: Claim pending funds (idempotent, safe)
    function claim() external {
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "nothing to claim");
        pendingWithdrawals[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
    }

    receive() external payable {}
}
