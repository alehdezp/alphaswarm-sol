// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title StorageProxy (SAFE VARIANT) - Uses EIP-1967 storage slots
contract StorageProxy_safe {
    // EIP-1967 slots (no collision)
    bytes32 private constant IMPL_SLOT = bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1);
    bytes32 private constant ADMIN_SLOT = bytes32(uint256(keccak256("eip1967.proxy.admin")) - 1);

    event Upgraded(address indexed newImplementation);

    constructor(address _impl) {
        _setImpl(_impl);
        _setAdmin(msg.sender);
    }

    function upgradeTo(address newImpl) external {
        require(msg.sender == _getAdmin(), "Not admin"); // FIXED
        require(newImpl != address(0), "Zero address");
        _setImpl(newImpl);
        emit Upgraded(newImpl);
    }

    function changeAdmin(address newAdmin) external {
        require(msg.sender == _getAdmin(), "Not admin"); // FIXED
        _setAdmin(newAdmin);
    }

    fallback() external payable {
        address impl = _getImpl();
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    function _getImpl() internal view returns (address impl) {
        bytes32 slot = IMPL_SLOT;
        assembly { impl := sload(slot) }
    }

    function _setImpl(address impl) internal {
        bytes32 slot = IMPL_SLOT;
        assembly { sstore(slot, impl) }
    }

    function _getAdmin() internal view returns (address admin) {
        bytes32 slot = ADMIN_SLOT;
        assembly { admin := sload(slot) }
    }

    function _setAdmin(address admin) internal {
        bytes32 slot = ADMIN_SLOT;
        assembly { sstore(slot, admin) }
    }

    receive() external payable {}
}
