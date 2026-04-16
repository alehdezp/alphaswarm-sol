// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ConstructorInLogic
 * @dev Demonstrates the vulnerability of using constructors in implementation contracts
 *
 * Constructors are executed only when the implementation contract
 * is deployed, not when called via delegatecall from proxy. Any state set in the
 * constructor will exist in the implementation's storage, not the proxy's storage.
 *
 * This means:
 * 1. Constructor logic is never executed in proxy context
 * 2. Immutable variables work (stored in code) but state variables don't
 * 3. Can lead to uninitialized state in proxy
 */

// VULNERABLE: Using constructor to set critical state
contract VulnerableImplementationWithConstructor {
    address public owner;
    uint256 public initialValue;
    bool public initialized;

    // PROBLEM: This runs only during implementation deployment
    // When proxy delegatecalls to this contract, owner is not set in proxy storage!
    constructor(address _owner, uint256 _value) {
        owner = _owner;
        initialValue = _value;
        initialized = true;
    }

    function setValue(uint256 _value) public {
        require(msg.sender == owner, "Not owner");  // This will fail! owner is 0x0 in proxy
        initialValue = _value;
    }

    function destroy() public {
        require(msg.sender == owner, "Not owner");
        selfdestruct(payable(owner));
    }
}

// SAFE: Using initializer instead of constructor
contract SafeImplementationWithInitializer {
    address public owner;
    uint256 public initialValue;
    bool private initialized;

    // Initializer runs in proxy context via delegatecall
    function initialize(address _owner, uint256 _value) public {
        require(!initialized, "Already initialized");
        owner = _owner;
        initialValue = _value;
        initialized = true;
    }

    function setValue(uint256 _value) public {
        require(msg.sender == owner, "Not owner");
        initialValue = _value;
    }
}

// VULNERABLE: Using immutable with constructor (partially safe)
contract ImplementationWithImmutable {
    address public immutable FACTORY;  // Safe: stored in code, not storage
    address public owner;  // Unsafe: not set in proxy context

    constructor() {
        FACTORY = msg.sender;
        owner = msg.sender;  // This won't be set in proxy!
    }

    function initialize(address _owner) public {
        // Must still initialize non-immutable state
        owner = _owner;
    }
}

// VULNERABLE: Inheritance with constructor
contract BaseContract {
    address public baseOwner;

    constructor(address _owner) {
        baseOwner = _owner;  // Not set in proxy context!
    }
}

contract VulnerableInheritedImplementation is BaseContract {
    uint256 public value;

    constructor(address _owner) BaseContract(_owner) {
        // Both constructors run only during implementation deployment
    }

    function setValue(uint256 _value) public {
        require(msg.sender == baseOwner, "Not owner");  // baseOwner is 0x0!
        value = _value;
    }
}

// SAFE: Proper initialization chain for inherited contracts
contract SafeBaseContract {
    address public baseOwner;
    bool private _baseInitialized;

    function __Base_init(address _owner) internal {
        require(!_baseInitialized, "Base already initialized");
        baseOwner = _owner;
        _baseInitialized = true;
    }
}

contract SafeInheritedImplementation is SafeBaseContract {
    uint256 public value;
    bool private initialized;

    function initialize(address _owner) public {
        require(!initialized, "Already initialized");
        __Base_init(_owner);
        initialized = true;
    }

    function setValue(uint256 _value) public {
        require(msg.sender == baseOwner, "Not owner");
        value = _value;
    }
}

// DANGEROUS: Selfdestruct in implementation
contract VulnerableImplementationWithSelfdestruct {
    address public owner;

    function initialize(address _owner) public {
        owner = _owner;
    }

    // If called on implementation directly, destroys the logic contract!
    // All proxies pointing to it will break
    function destroy() public {
        require(msg.sender == owner, "Not owner");
        selfdestruct(payable(owner));
    }
}

// SAFE: Selfdestruct protection with initialization lock
contract SafeImplementationProtectedFromSelfdestruct {
    address public owner;
    bool private initialized;

    // @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        // Lock implementation contract
        initialized = true;
    }

    function initialize(address _owner) public {
        require(!initialized, "Already initialized");
        owner = _owner;
        initialized = true;
    }

    // Even if this exists, implementation is locked
    function destroy() public {
        require(msg.sender == owner, "Not owner");
        require(initialized, "Not initialized");
        selfdestruct(payable(owner));
    }
}
