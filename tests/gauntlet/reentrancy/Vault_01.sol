// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// RE-VULN-001: Classic CEI Violation
// VULNERABLE: External call before state update
contract Vault_01 {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // VULNERABLE: classic reentrancy - call before state update
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        // BUG: external call before state update
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount; // State update AFTER call
    }

    receive() external payable {}
}
