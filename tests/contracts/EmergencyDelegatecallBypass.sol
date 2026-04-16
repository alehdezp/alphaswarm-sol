// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Emergency delegatecall path without target validation.
contract EmergencyDelegatecallBypass {
    function emergencyExecute(address target, bytes calldata data) external returns (bytes memory) {
        (bool ok, bytes memory result) = target.delegatecall(data);
        require(ok, "delegatecall failed");
        return result;
    }
}
