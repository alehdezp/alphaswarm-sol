// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =============================================================================
// TEST CONTRACT: upgrade-009-constructor-in-implementation
// =============================================================================
// Tests for detecting constructors in upgradeable implementation contracts.
//
// VULNERABILITY: Using constructors in implementation contracts causes storage
// context mismatch. Constructor runs in IMPLEMENTATION storage during deployment,
// but proxy delegates to implementation - so proxy storage remains UNINITIALIZED.
//
// Pattern Detection Logic:
// - is_implementation_contract == true (via has_upgrade OR "implementation"/"logic" in name)
// - initializers_disabled == false (no _disableInitializers() call)
//
// Test Coverage:
// - TRUE POSITIVES: Implementations with constructors that initialize state
// - TRUE NEGATIVES: Safe patterns (_disableInitializers, no constructor, immutables only)
// - EDGE CASES: Empty constructors, non-upgradeable contracts with constructors
// - VARIATIONS: Different proxy types (UUPS, Transparent, Beacon), naming variations

// =============================================================================
// Mock OpenZeppelin contracts (for testing without dependencies)
// =============================================================================

abstract contract Initializable {
    uint8 private _initialized;
    bool private _initializing;

    modifier initializer() {
        require(_initialized == 0, "Already initialized");
        _;
        _initialized = 1;
    }

    modifier reinitializer(uint8 version) {
        require(_initialized < version, "Already initialized");
        _;
        _initialized = version;
    }

    function _disableInitializers() internal {
        _initialized = type(uint8).max;
    }
}

abstract contract OwnableUpgradeable is Initializable {
    address private _owner;

    function __Ownable_init() internal {
        _owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == _owner, "not owner");
        _;
    }
}

// =============================================================================
// TRUE POSITIVES - Vulnerable Patterns
// =============================================================================

// TP1: Classic vulnerable implementation - constructor sets owner
contract VulnerableClassicImplementation is Initializable {
    address public owner;
    bool private initialized;

    // VULNERABLE: Constructor initializes state in IMPLEMENTATION storage
    constructor() {
        owner = msg.sender;  // ❌ Sets in implementation storage, NOT proxy storage
        initialized = true;   // ❌ Proxy storage shows initialized = false
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

// TP2: UUPS implementation with constructor vulnerability
contract VulnerableUUPSImplementation is Initializable {
    address public owner;
    uint256 public version;

    // VULNERABLE: Constructor sets version in implementation storage
    constructor() {
        version = 1;  // ❌ Wrong storage context
        owner = msg.sender;  // ❌ Wrong storage context
    }

    function initialize() public initializer {
        owner = msg.sender;
    }

    function _authorizeUpgrade(address) internal view {
        require(msg.sender == owner, "not owner");
    }
}

// TP3: Transparent proxy implementation with constructor
contract VulnerableTransparentImplementation is Initializable {
    address public admin;
    mapping(address => uint256) public balances;

    // VULNERABLE: Constructor initializes admin
    constructor() {
        admin = msg.sender;  // ❌ Admin is address(0) in proxy storage
    }

    function initialize(address _admin) public initializer {
        admin = _admin;
    }
}

// TP4: Beacon implementation with constructor
contract VulnerableBeaconImplementation is Initializable {
    address public controller;
    bool public paused;

    // VULNERABLE: Constructor initializes state
    constructor() {
        controller = msg.sender;  // ❌ Wrong storage context
        paused = false;            // ❌ Wrong storage context
    }

    function initialize(address _controller) public initializer {
        controller = _controller;
    }
}

// TP5: Implementation with "Logic" naming pattern
contract VulnerableLogicContract is Initializable {
    address public owner;
    uint256 public fee;

    // VULNERABLE: Constructor in logic contract
    constructor() {
        owner = msg.sender;  // ❌ Wrong storage context
        fee = 100;           // ❌ Wrong storage context
    }

    function initialize(address _owner, uint256 _fee) public initializer {
        owner = _owner;
        fee = _fee;
    }
}

// TP6: Complex implementation with multiple state variables
contract VulnerableComplexImplementation is Initializable, OwnableUpgradeable {
    address public treasury;
    uint256 public feeRate;
    mapping(address => bool) public authorized;

    // VULNERABLE: Constructor initializes multiple state variables
    constructor() {
        treasury = msg.sender;   // ❌ Wrong storage context
        feeRate = 300;           // ❌ Wrong storage context
        authorized[msg.sender] = true;  // ❌ Wrong storage context
    }

    function initialize(address _treasury, uint256 _feeRate) public initializer {
        __Ownable_init();
        treasury = _treasury;
        feeRate = _feeRate;
    }
}

// TP7: Variation - "Implementation" in name (explicit)
contract ExplicitImplementation is Initializable {
    address public governance;

    // VULNERABLE: Constructor in explicit implementation
    constructor() {
        governance = msg.sender;  // ❌ Wrong storage context
    }

    function initialize(address _governance) public initializer {
        governance = _governance;
    }
}

// =============================================================================
// TRUE NEGATIVES - Safe Patterns
// =============================================================================

// TN1: Safe - _disableInitializers() in constructor (BEST PRACTICE)
contract SafeImplementationDisabled is Initializable {
    address public owner;
    uint256 public value;

    // Safe: Using _disableInitializers pattern
    constructor() {
        _disableInitializers();  // ✓ SAFE: Disables implementation initialization
    }

    function initialize(address _owner) public initializer {
        owner = _owner;  // ✓ Executes in proxy storage context
    }
}

// TN2: Safe - Only immutable variables in constructor
contract SafeImplementationImmutables is Initializable {
    address public immutable WETH;
    address public immutable FACTORY;
    address public owner;  // Regular state variable

    // Safe: Using _disableInitializers pattern
    constructor(address _weth, address _factory) {
        WETH = _weth;        // ✓ SAFE: Immutable - stored in bytecode
        FACTORY = _factory;  // ✓ SAFE: Immutable - stored in bytecode
        _disableInitializers();
    }

    function initialize(address _owner) public initializer {
        owner = _owner;  // ✓ Regular state - initialized in proxy storage
    }
}

// TN3: Safe - Empty constructor with _disableInitializers
contract SafeImplementationEmpty is Initializable {
    address public owner;

    // Safe: Using _disableInitializers pattern
    constructor() {
        _disableInitializers();  // ✓ SAFE: Only disables initializers
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

// TN4: Safe - No constructor at all
contract SafeImplementationNoConstructor is Initializable {
    address public owner;
    uint256 public fee;

    // ✓ SAFE: No constructor, only initializer
    function initialize(address _owner, uint256 _fee) public initializer {
        owner = _owner;
        fee = _fee;
    }
}

// TN5: Safe - UUPS with proper _disableInitializers
contract SafeUUPSImplementation is Initializable, OwnableUpgradeable {
    uint256 public value;

    // Safe: Using _disableInitializers pattern
    constructor() {
        _disableInitializers();  // ✓ SAFE
    }

    function initialize() public initializer {
        __Ownable_init();
    }

    function _authorizeUpgrade(address) internal view onlyOwner {}
}

// TN6: Safe - Transparent with _disableInitializers
contract SafeTransparentImplementation is Initializable {
    address public admin;

    // Safe: Using _disableInitializers pattern
    constructor() {
        _disableInitializers();  // ✓ SAFE
    }

    function initialize(address _admin) public initializer {
        admin = _admin;
    }
}

// TN7: Safe - Beacon with _disableInitializers
contract SafeBeaconImplementation is Initializable {
    address public controller;

    // Safe: Using _disableInitializers pattern
    constructor() {
        _disableInitializers();  // ✓ SAFE
    }

    function initialize(address _controller) public initializer {
        controller = _controller;
    }
}

// TN8: Non-upgradeable contract with constructor (SAFE - not used with proxy)
contract RegularContractWithConstructor {
    address public owner;

    // ✓ SAFE: This is NOT an upgradeable contract (no Initializable)
    constructor() {
        owner = msg.sender;
    }
}

// =============================================================================
// EDGE CASES
// =============================================================================

// EDGE1: Constructor with only event emission (SAFE)
contract EdgeConstructorOnlyEvent is Initializable {
    address public owner;
    event Deployed(address implementation);

    // Safe: Using _disableInitializers pattern
    constructor() {
        emit Deployed(address(this));  // Only event, no state writes
        _disableInitializers();
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

// EDGE2: Constructor sets immutable + calls _disableInitializers
contract EdgeMixedImmutableAndDisable is Initializable {
    address public immutable GOVERNANCE;
    address public owner;

    // Safe: Using _disableInitializers pattern
    constructor(address _governance) {
        GOVERNANCE = _governance;  // Immutable - safe
        _disableInitializers();    // Disable initializers - safe
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

// EDGE3: _initialized = type(uint8).max pattern (manual disable)
contract EdgeManualDisablePattern is Initializable {
    address public owner;
    uint8 private _initialized;

    // Safe: Using _disableInitializers pattern
    constructor() {
        _initialized = type(uint8).max;  // ✓ Manual disable pattern
    }

    function initialize(address _owner) public {
        require(_initialized != type(uint8).max, "Initializable: contract is already initialized");
        owner = _owner;
        _initialized = 1;
    }
}

// EDGE4: Multiple inheritance with constructor
contract EdgeMultipleInheritance is Initializable, OwnableUpgradeable {
    uint256 public version;

    // VULNERABLE: Constructor in upgradeable contract
    constructor() {
        version = 1;  // ❌ Wrong storage context (no _disableInitializers)
    }

    function initialize() public initializer {
        __Ownable_init();
    }
}

// =============================================================================
// VARIATIONS - Naming and Pattern Variations
// =============================================================================

// VAR1: "Logic" naming instead of "Implementation"
contract VariationLogicNaming is Initializable {
    address public admin;

    // VULNERABLE: Constructor in logic contract
    constructor() {
        admin = msg.sender;  // ❌ Wrong storage context
    }

    function initialize(address _admin) public initializer {
        admin = _admin;
    }
}

// VAR2: "Impl" abbreviation
contract VariationImplNaming is Initializable {
    address public controller;

    // VULNERABLE: Constructor in impl contract
    constructor() {
        controller = msg.sender;  // ❌ Wrong storage context
    }

    function initialize(address _controller) public initializer {
        controller = _controller;
    }
}

// VAR3: Custom upgrade function (detected as implementation)
contract VariationCustomUpgrade is Initializable {
    address public owner;

    // VULNERABLE: Constructor in upgradeable contract
    constructor() {
        owner = msg.sender;  // ❌ Wrong storage context
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }

    function upgradeToAndCall(address newImplementation, bytes memory data) external {
        // Custom upgrade logic
    }
}

// VAR4: Has _authorizeUpgrade (UUPS indicator)
contract VariationAuthorizeUpgrade is Initializable {
    address public owner;

    // VULNERABLE: Constructor in UUPS contract
    constructor() {
        owner = msg.sender;  // ❌ Wrong storage context
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }

    function _authorizeUpgrade(address) internal view {
        require(msg.sender == owner, "not owner");
    }
}

// VAR5: Diamond proxy facet
contract VariationDiamondFacet is Initializable {
    address public owner;

    // VULNERABLE: Constructor in diamond facet
    constructor() {
        owner = msg.sender;  // ❌ Wrong storage context
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

// VAR6: Safe variation - Proxy contract itself (should NOT be flagged)
contract VariationProxyContract {
    address public implementation;

    // ✓ SAFE: This is a PROXY, not an IMPLEMENTATION
    // Proxies can have constructors
    constructor(address _implementation) {
        implementation = _implementation;
    }

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
}

// VAR7: Safe variation - disableInitializers() without underscore
contract VariationDisableNoUnderscore is Initializable {
    address public owner;

    // Safe: Using _disableInitializers pattern
    constructor() {
        // ✓ SAFE: Builder checks for both _disableInitializers and disableInitializers
        _disableInitializers();
    }

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}
