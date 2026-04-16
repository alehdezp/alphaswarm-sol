// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Delegatecall with user-controlled target and no validation.
contract DelegatecallTargetUnvalidated {
    function execute(address target, bytes calldata data) external {
        (bool ok, ) = target.delegatecall(data);
        require(ok, "delegatecall failed");
    }
}
