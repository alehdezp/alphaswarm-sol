// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Cross-function reentrancy vulnerability
contract CrossFunctionReentrancy {
    mapping(address => uint256) public balances;
    bool private inWithdraw;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // Vulnerable: external call before state update,
    // and attacker can re-enter via transfer()
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        inWithdraw = true;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount;
        inWithdraw = false;
    }

    // Vulnerable to reentrancy from withdraw()
    function transfer(address to, uint256 amount) external {
        require(!inWithdraw, "reentrant");
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}
