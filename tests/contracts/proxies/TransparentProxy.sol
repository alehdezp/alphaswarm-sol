// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TestTransparentProxy
 * @notice Test contract for EIP-1967 Transparent Proxy pattern detection.
 * @dev Uses standard EIP-1967 storage slots for implementation and admin.
 */
contract TestTransparentProxy {
    // EIP-1967 implementation slot: keccak256('eip1967.proxy.implementation') - 1
    bytes32 internal constant IMPLEMENTATION_SLOT =
        0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    // EIP-1967 admin slot: keccak256('eip1967.proxy.admin') - 1
    bytes32 internal constant ADMIN_SLOT =
        0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103;

    event Upgraded(address indexed implementation);
    event AdminChanged(address previousAdmin, address newAdmin);

    /**
     * @dev Sets implementation and admin addresses.
     */
    constructor(address _logic, address _admin) {
        assembly {
            sstore(IMPLEMENTATION_SLOT, _logic)
            sstore(ADMIN_SLOT, _admin)
        }
    }

    /**
     * @dev Returns the current implementation address.
     */
    function implementation() public view returns (address impl) {
        assembly {
            impl := sload(IMPLEMENTATION_SLOT)
        }
    }

    /**
     * @dev Returns the current admin address.
     */
    function admin() public view returns (address adm) {
        assembly {
            adm := sload(ADMIN_SLOT)
        }
    }

    /**
     * @dev Upgrades to a new implementation (admin only).
     */
    function upgradeTo(address newImplementation) external {
        require(msg.sender == admin(), "Not admin");
        assembly {
            sstore(IMPLEMENTATION_SLOT, newImplementation)
        }
        emit Upgraded(newImplementation);
    }

    /**
     * @dev Changes the admin (admin only).
     */
    function changeAdmin(address newAdmin) external {
        address oldAdmin = admin();
        require(msg.sender == oldAdmin, "Not admin");
        assembly {
            sstore(ADMIN_SLOT, newAdmin)
        }
        emit AdminChanged(oldAdmin, newAdmin);
    }

    /**
     * @dev Fallback function delegates all calls to implementation.
     */
    fallback() external payable {
        address impl;
        assembly {
            impl := sload(IMPLEMENTATION_SLOT)
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    /**
     * @dev Receive function for plain ETH transfers.
     */
    receive() external payable {}
}

/**
 * @title TestImplementationV1
 * @notice Simple implementation contract for testing.
 */
contract TestImplementationV1 {
    uint256 public value;
    address public owner;

    function initialize() external {
        require(owner == address(0), "Already initialized");
        owner = msg.sender;
    }

    function setValue(uint256 _value) external {
        require(msg.sender == owner, "Not owner");
        value = _value;
    }

    function getValue() external view returns (uint256) {
        return value;
    }
}
