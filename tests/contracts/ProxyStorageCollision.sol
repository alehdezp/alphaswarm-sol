// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ProxyStorageCollision
 * @dev Demonstrates storage collision vulnerability in proxy contracts
 *
 * Storage collision occurs when proxy and implementation contracts
 * use overlapping storage slots, causing state variables to overwrite each other.
 *
 * CWE-1321: Storage layout incompatibility
 *
 * This contract shows:
 * 1. Vulnerable pattern: Implementation uses slot 0 for critical data
 * 2. Proxy also uses slot 0 for implementation address
 * 3. Result: Writing to implementation can corrupt proxy state
 */

// VULNERABLE: Implementation contract with storage that collides with proxy
contract VulnerableImplementation {
    address public owner;  // slot 0 - COLLIDES with proxy's implementation slot
    uint256 public value;  // slot 1

    function initialize(address _owner) public {
        owner = _owner;
    }

    function setValue(uint256 _value) public {
        value = _value;
    }
}

// VULNERABLE: Simple proxy without ERC-1967 standard storage slots
contract VulnerableProxy {
    address public implementation;  // slot 0 - COLLIDES with implementation's owner

    constructor(address _implementation) {
        implementation = _implementation;
    }

    fallback() external payable {
        address _impl = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), _impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}

// SAFE: Implementation using ERC-1967 compliant storage
contract SafeImplementation {
    address public owner;
    uint256 public value;

    // Storage gap to avoid collision with proxy slots
    uint256[50] private __gap;

    function initialize(address _owner) public {
        owner = _owner;
    }

    function setValue(uint256 _value) public {
        value = _value;
    }
}

// SAFE: ERC-1967 compliant proxy using deterministic storage slots
contract SafeProxy {
    // ERC-1967: bytes32(uint256(keccak256('eip1967.proxy.implementation')) - 1)
    bytes32 private constant IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    constructor(address _implementation) {
        assembly {
            sstore(IMPLEMENTATION_SLOT, _implementation)
        }
    }

    fallback() external payable {
        assembly {
            let _impl := sload(IMPLEMENTATION_SLOT)
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), _impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}
