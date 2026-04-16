// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract BaseVault {
    mapping(address => uint256) public balances;

    function baseDeposit() external payable {
        balances[msg.sender] += msg.value;
    }
}

contract DerivedVault is BaseVault {
    bool private locked;

    modifier reentrancyLock() {
        require(!locked, "locked");
        locked = true;
        _;
        locked = false;
    }

    function derivedWithdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount;
    }

    function guardedWithdraw(uint256 amount) external reentrancyLock {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "call failed");
        balances[msg.sender] -= amount;
    }
}

contract StrategyVault {
    address public strategy;
    uint256 public totalShares;

    constructor(address _strategy) {
        strategy = _strategy;
    }

    function harvest(uint256 amount) external {
        IStrategy(strategy).harvest();
        totalShares += amount;
    }
}

interface IStrategy {
    function harvest() external;
}
