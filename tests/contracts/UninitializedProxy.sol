// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title UninitializedProxy
 * @dev Demonstrates uninitialized proxy implementation vulnerability
 *
 * If an implementation contract is not initialized, an attacker
 * can initialize it and gain control over the logic contract. This can allow
 * them to selfdestruct the implementation or change critical variables.
 *
 * REAL-WORLD: This vulnerability affected multiple DeFi protocols in 2025,
 * with attackers front-running initialization transactions to gain control
 * of implementation contracts worth over $10M.
 *
 * CWE-665: Improper Initialization
 */

// VULNERABLE: Implementation without initialization protection
contract VulnerableUUPSImplementation {
    address public owner;
    bool public initialized;

    // No constructor or initializer protection
    function initialize(address _owner) public {
        require(!initialized, "Already initialized");
        owner = _owner;
        initialized = true;
    }

    function upgradeToAndCall(address newImplementation, bytes memory data) public {
        require(msg.sender == owner, "Not owner");
        // Upgrade logic here
    }

    // Dangerous: Can be called by attacker if they initialize first
    function destroy() public {
        require(msg.sender == owner, "Not owner");
        selfdestruct(payable(owner));
    }
}

// SAFE: Implementation with constructor-based initialization lock
contract SafeUUPSImplementation {
    address public owner;
    bool private initialized;

    // @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        // Lock the implementation contract on deployment
        initialized = true;
    }

    function initialize(address _owner) public {
        require(!initialized, "Already initialized");
        owner = _owner;
        initialized = true;
    }

    function upgradeToAndCall(address newImplementation, bytes memory data) public {
        require(msg.sender == owner, "Not owner");
        // Upgrade logic here
    }
}

// SAFE: Using OpenZeppelin-style initializer pattern
contract SafeInitializableImplementation {
    address public owner;
    uint8 private _initialized;
    bool private _initializing;

    modifier initializer() {
        require(
            _initialized == 0 || _initializing,
            "Already initialized"
        );

        bool isTopLevelCall = !_initializing;
        if (isTopLevelCall) {
            _initializing = true;
            _initialized = 1;
        }

        _;

        if (isTopLevelCall) {
            _initializing = false;
        }
    }

    // @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function _disableInitializers() internal {
        _initialized = type(uint8).max;
        _initializing = false;
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

// VULNERABLE: Proxy that doesn't initialize implementation on deployment
contract VulnerableProxyDeployment {
    bytes32 private constant IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    constructor(address _implementation) {
        assembly {
            sstore(IMPLEMENTATION_SLOT, _implementation)
        }
        // Implementation not initialized here!
        // Attacker can front-run the initialization transaction
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

// SAFE: Proxy that initializes implementation during deployment
contract SafeProxyDeployment {
    bytes32 private constant IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    constructor(address _implementation, bytes memory _data) {
        assembly {
            sstore(IMPLEMENTATION_SLOT, _implementation)
        }

        // Initialize implementation immediately
        if (_data.length > 0) {
            (bool success,) = _implementation.delegatecall(_data);
            require(success, "Initialization failed");
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
