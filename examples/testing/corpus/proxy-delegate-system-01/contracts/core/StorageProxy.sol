// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title StorageProxy - Transparent proxy with storage separation
/// @dev VULNERABILITY: Storage collision risk between proxy and implementation (B2)
contract StorageProxy {
    // Slot 0: implementation address
    address public implementation;
    // Slot 1: admin address
    address public proxyAdmin;

    event Upgraded(address indexed newImplementation);

    constructor(address _impl) {
        implementation = _impl;
        proxyAdmin = msg.sender;
    }

    /// @notice Upgrade implementation
    /// @dev VULNERABILITY: Missing access control on upgrade
    function upgradeTo(address newImpl) external {
        // Missing: require(msg.sender == proxyAdmin)
        implementation = newImpl;
        emit Upgraded(newImpl);
    }

    /// @notice Change admin
    /// @dev VULNERABILITY: Missing access control
    function changeAdmin(address newAdmin) external {
        proxyAdmin = newAdmin;
    }

    /// @notice Delegatecall to implementation
    fallback() external payable {
        address impl = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    receive() external payable {}
}
