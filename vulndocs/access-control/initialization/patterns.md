# Patterns: Initialization Vulnerabilities

## Vulnerable Pattern - Unprotected Initializer

```solidity
contract VulnerableUpgradeable {
    address public owner;
    bool public initialized;

    // VULNERABLE: Anyone can call initialize
    function initialize(address _owner) external {
        owner = _owner;
        initialized = true;
    }

    function adminFunction() external {
        require(msg.sender == owner, "Not owner");
        // ...
    }
}
```

## Vulnerable Pattern - Missing Initialized Check

```solidity
contract MissingCheck {
    address public owner;

    // VULNERABLE: Can be called multiple times
    function initialize(address _owner) external {
        // No check if already initialized!
        owner = _owner;
    }
}
```

## Vulnerable Pattern - Reinitializable

```solidity
contract Reinitializable {
    address public owner;
    bool public initialized;

    // VULNERABLE: initialized flag can be reset
    function initialize(address _owner) external {
        require(!initialized, "Already initialized");
        owner = _owner;
        initialized = true;
    }

    // VULNERABLE: Allows reinitialization
    function reset() external {
        initialized = false;  // Anyone can call, then reinitialize
    }
}
```

## Safe Pattern - OpenZeppelin Initializable

```solidity
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";

contract SafeUpgradeable is Initializable {
    address public owner;

    // SAFE: initializer modifier ensures single initialization
    function initialize(address _owner) external initializer {
        owner = _owner;
    }

    // SAFE: For upgrades, use reinitializer with version
    function initializeV2(address _newParam) external reinitializer(2) {
        // V2 initialization logic
    }
}
```

## Safe Pattern - Manual Initialization Guard

```solidity
contract ManualGuard {
    address public owner;
    bool private _initialized;

    modifier initializer() {
        require(!_initialized, "Already initialized");
        _;
        _initialized = true;
    }

    function initialize(address _owner) external initializer {
        require(_owner != address(0), "Zero address");
        owner = _owner;
    }
}
```

## Variations

### Uninitialized Implementation Contract

```solidity
// Implementation contract can be initialized by attacker
contract VulnerableImpl {
    address public owner;

    function initialize() external {
        owner = msg.sender;
    }
}

// Attacker initializes implementation directly (not through proxy)
// Can then selfdestruct or manipulate storage
```

### Missing DisableInitializers

```solidity
// VULNERABLE: Implementation constructor doesn't disable initializers
contract VulnerableImpl is Initializable {
    // constructor() {
    //     _disableInitializers();  // MISSING!
    // }

    function initialize() external initializer {
        // ...
    }
}

// SAFE: Disable initializers in implementation constructor
contract SafeImpl is Initializable {
    constructor() {
        _disableInitializers();  // Prevents initialization of implementation
    }

    function initialize() external initializer {
        // ...
    }
}
```
