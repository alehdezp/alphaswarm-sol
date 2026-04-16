// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Timelock parameter present but no enforcement.
contract TimelockParameterNoCheck {
    uint256 public timelockDelay = 1 days;

    function executeAfter(uint256 eta, address target, bytes calldata data) external {
        eta;
        (bool ok, ) = target.call(data);
        require(ok, "call failed");
    }
}
