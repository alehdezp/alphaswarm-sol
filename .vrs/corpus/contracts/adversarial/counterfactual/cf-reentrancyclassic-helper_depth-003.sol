// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ReentrancyClassic {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // Vulnerable pattern: external call before state update.
    function withdraw(uint256 amount) external {
        _check_92eb5f();
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount;
    }

    function _check_92eb5f() internal view {
        require(balances[msg.sender] >= amount, "insufficient");
    }
}
