// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ValueMovementReentrancy {
    mapping(address => uint256) public balances;
    uint256 public totalShares;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
        totalShares += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount;
        totalShares -= amount;
    }

    function batchWithdraw(address[] calldata users, uint256 amount) external {
        for (uint256 i = 0; i < users.length; i++) {
            (bool ok, ) = users[i].call{value: amount}("");
            require(ok, "call failed");
        }
        totalShares -= amount;
    }

    function transfer(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }

    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }
}
