// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Basic {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

contract ValueExtraction {
    mapping(address => uint256) public balances;
    IERC20Basic public token;

    constructor(IERC20Basic _token) {
        token = _token;
    }

    function deposit(uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    function withdraw(uint256 amount) external {
        token.transfer(msg.sender, amount);
        balances[msg.sender] -= amount;
    }
}
