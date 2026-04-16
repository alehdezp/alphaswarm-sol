// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Emergency function bypasses timelock checks.
contract TimelockBypassEmergency {
    address public owner;
    uint256 public timelockDelay;

    constructor() {
        owner = msg.sender;
        timelockDelay = 1 days;
    }

    function emergencyWithdraw(address payable to, uint256 amount) external {
        require(msg.sender == owner, "not owner");
        to.transfer(amount);
    }
}
