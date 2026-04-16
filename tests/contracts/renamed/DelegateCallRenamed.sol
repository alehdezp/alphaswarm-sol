// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DelegateCallRenamed
 * @notice Delegatecall vulnerabilities with non-standard naming.
 *         Tests detection without relying on "delegatecall", "proxy", "implementation" names.
 *
 * Renamed: implementation -> logic, upgrade -> switchLogic
 */
contract DelegateCallRenamed {
    address public logic;  // Renamed from "implementation"
    address public supervisor;  // Renamed from "admin"

    constructor(address _logic) {
        logic = _logic;
        supervisor = msg.sender;
    }

    // VULNERABLE: delegatecall to user-controlled target without validation
    function invokeArbitrary(address target, bytes calldata payload) external returns (bytes memory) {
        (bool ok, bytes memory result) = target.delegatecall(payload);
        require(ok, "failed");
        return result;
    }

    // VULNERABLE: No access control on logic switch
    function switchLogic(address newLogic) external {
        logic = newLogic;
    }

    // VULNERABLE: delegatecall with unvalidated data
    function invokeLogic(bytes calldata payload) external returns (bytes memory) {
        (bool ok, bytes memory result) = logic.delegatecall(payload);
        require(ok, "failed");
        return result;
    }

    fallback() external payable {
        address _logic = logic;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), _logic, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    receive() external payable {}
}
