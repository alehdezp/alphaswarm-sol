// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title SelectorClash
 * @dev Demonstrates function selector clash vulnerability in transparent proxies
 *
 * Function selectors are 4-byte hashes that can collide. In transparent
 * proxies, if an implementation function has the same selector as a proxy admin function,
 * the implementation function becomes inaccessible or the proxy function is wrongly called.
 *
 * CVE-2023-30541: OpenZeppelin TransparentUpgradeableProxy selector clash
 *
 * This vulnerability was discovered in OpenZeppelin Contracts where deliberately crafted
 * function signatures could clash with proxy admin functions, making implementation
 * functions inaccessible.
 */

// Example of selector calculation
library SelectorUtils {
    // upgradeToAndCall selector: 0x4f1ef286
    // collideABCD selector could be crafted to be 0x4f1ef286
    function getSelector(string memory signature) public pure returns (bytes4) {
        return bytes4(keccak256(bytes(signature)));
    }
}

// VULNERABLE: Transparent proxy with potential selector clash
contract VulnerableTransparentProxy {
    address public implementation;
    address public admin;

    constructor(address _implementation, address _admin) {
        implementation = _implementation;
        admin = _admin;
    }

    // Admin functions
    function upgradeToAndCall(address newImplementation, bytes memory data) public {
        require(msg.sender == admin, "Not admin");
        implementation = newImplementation;
        if (data.length > 0) {
            (bool success,) = newImplementation.delegatecall(data);
            require(success);
        }
    }

    fallback() external payable {
        require(msg.sender != admin, "Admin cannot call implementation");

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

// VULNERABLE: Implementation with function that could clash
contract VulnerableImplementationWithClash {
    uint256 public value;

    // This function signature could be crafted to match proxy admin functions
    // upgradeToAndCall(address,bytes) = 0x4f1ef286
    // A malicious function like collideFunc_mc(bytes,address) might produce same selector
    function upgradeToAndCall(address token, bytes memory data) public {
        // Totally different logic than upgrade, but same selector!
        // This function becomes inaccessible through the proxy
        value = 123;
    }

    function setValue(uint256 _value) public {
        value = _value;
    }
}

// SAFE: UUPS pattern where upgrade logic is in implementation
contract SafeUUPSProxy {
    bytes32 private constant IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    constructor(address _implementation) {
        assembly {
            sstore(IMPLEMENTATION_SLOT, _implementation)
        }
    }

    // No admin functions in proxy - all logic delegated
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

// SAFE: UUPS implementation with upgrade logic
contract SafeUUPSImplementation {
    bytes32 private constant IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    address public owner;
    uint256 public value;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function initialize(address _owner) public {
        owner = _owner;
    }

    // Upgrade logic in implementation - no clash possible with proxy
    function upgradeToAndCall(address newImplementation, bytes memory data) public onlyOwner {
        assembly {
            sstore(IMPLEMENTATION_SLOT, newImplementation)
        }
        if (data.length > 0) {
            (bool success,) = address(this).call(data);
            require(success);
        }
    }

    function setValue(uint256 _value) public {
        value = _value;
    }
}

// Contract demonstrating deliberate selector collision
contract SelectorCollisionExample {
    // These two functions have different signatures but could have same selector
    // through birthday attack or brute force

    // Original: bytes4(keccak256("transferOwnership(address)")) = 0xf2fde38b
    function transferOwnership(address newOwner) public {
        // Transfer ownership logic
    }

    // Malicious: A carefully crafted function signature that produces 0xf2fde38b
    // Example: pwn_func_x9z(uint256,bytes32) might collide
    // This is why function selectors need to be checked in proxies
}
