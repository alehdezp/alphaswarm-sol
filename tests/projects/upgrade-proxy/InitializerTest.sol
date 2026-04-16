// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =============================================================================
// TEST CONTRACT: InitializerTest.sol
// =============================================================================
// Pattern: upgrade-005-unprotected-initializer
// Purpose: Test FIRST-TIME initializer detection (not reinitializers)
// Difference from ReinitializerTest.sol: Tests initialize() vs reinitializeV2()
// =============================================================================

// Mock OpenZeppelin imports (for testing without full dependencies)
abstract contract Initializable {
    uint8 private _initialized;
    bool private _initializing;

    modifier initializerModifier() {
        require(_initialized == 0 || _initializing, "Already initialized");
        _;
        if (!_initializing) {
            _initialized = 1;
        }
    }

    modifier onlyInitializing() {
        require(_initializing, "Not initializing");
        _;
    }

    function _disableInitializers() internal {
        _initialized = type(uint8).max;
    }
}

abstract contract OwnableUpgradeable is Initializable {
    address public owner;

    function __Ownable_init(address _owner) internal onlyInitializing {
        owner = _owner;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }
}

abstract contract UUPSUpgradeable {
    function _authorizeUpgrade(address newImplementation) internal virtual;
}

// =============================================================================
// TRUE POSITIVES (10 cases) - SHOULD BE FLAGGED
// =============================================================================

/**
 * TP1: Classic unprotected initialize() function
 * VULNERABLE: No initializer modifier, no flag check
 */
contract VulnerableClassic is Initializable {
    address public owner;
    uint256 public value;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function initialize(address _owner, uint256 _value) public {
        owner = _owner;
        value = _value;
    }
}

/**
 * TP2: Unprotected init() function (alternative naming)
 * VULNERABLE: No protection mechanism
 */
contract VulnerableInit is Initializable {
    address public admin;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function init(address _admin) external {
        admin = _admin;
    }
}

/**
 * TP3: Unprotected setup() function
 * VULNERABLE: No initializer modifier
 */
contract VulnerableSetup is Initializable {
    address public controller;
    uint256 public config;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function setup(address _controller, uint256 _config) public {
        controller = _controller;
        config = _config;
    }
}

/**
 * TP4: Unprotected __init__() function (Python-style naming)
 * VULNERABLE: No protection
 */
contract VulnerablePythonStyle is Initializable {
    address public governance;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function __init__(address _governance) external {
        governance = _governance;
    }
}

/**
 * TP5: Complex initialize with parameters
 * VULNERABLE: Multiple parameters but no protection
 */
contract VulnerableComplex is Initializable {
    address public owner;
    address public treasury;
    uint256 public fee;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function initializeContract(address _owner, address _treasury, uint256 _fee) public {
        owner = _owner;
        treasury = _treasury;
        fee = _fee;
    }
}

/**
 * TP6: Alternative naming - setUp (camelCase)
 * VULNERABLE: No initializer modifier
 */
contract VulnerableSetUp is Initializable {
    address public operator;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function setUp(address _operator) external {
        operator = _operator;
    }
}

/**
 * TP7: Alternative naming - initializeOwnable
 * VULNERABLE: Function named "initializeOwnable" but no modifier
 */
contract VulnerableInitializeOwnable is Initializable {
    address public admin;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function initializeOwnable(address _admin) public {
        admin = _admin;
    }
}

/**
 * TP8: Alternative naming - initContract
 * VULNERABLE: No protection
 */
contract VulnerableInitContract is Initializable {
    address public owner;
    bytes public data;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function initContract(address _owner, bytes memory _data) external {
        owner = _owner;
        data = _data;
    }
}

/**
 * TP9: UUPS pattern without protection
 * VULNERABLE: UUPS proxy with unprotected initializer
 */
contract VulnerableUUPS is Initializable, UUPSUpgradeable {
    address public owner;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function initialize(address _owner) public {
        owner = _owner;
    }

    function _authorizeUpgrade(address) internal override {}
}

/**
 * TP10: Beacon proxy pattern without protection
 * VULNERABLE: Beacon proxy with unprotected initializer
 */
contract VulnerableBeacon is Initializable {
    address public owner;
    address public beacon;

    // VULNERABLE: upgrade-005 SHOULD flag this
    function initialize(address _owner, address _beacon) external {
        owner = _owner;
        beacon = _beacon;
    }
}

// =============================================================================
// TRUE NEGATIVES (8 cases) - SHOULD NOT BE FLAGGED
// =============================================================================

/**
 * TN1: initialize() with initializer modifier (SAFE)
 * SAFE: Has OpenZeppelin initializer modifier
 */
contract SafeWithModifier is Initializable {
    address public owner;

    // SAFE: Has initializer modifier
    function initialize(address _owner) public initializerModifier {
        owner = _owner;
    }
}

/**
 * TN2: init() with onlyInitializing modifier (SAFE)
 * SAFE: Uses onlyInitializing for chained initialization
 */
contract SafeWithOnlyInitializing is Initializable {
    address public admin;

    // SAFE: Has onlyInitializing modifier
    function init(address _admin) internal onlyInitializing {
        admin = _admin;
    }
}

/**
 * TN3: setup() with manual initialized flag check (SAFE)
 * SAFE: Manual flag check prevents re-initialization
 */
contract SafeWithFlagCheck is Initializable {
    address public controller;
    bool private initialized;

    // SAFE: Has manual initialized flag check
    function setup(address _controller) public {
        require(!initialized, "Already initialized");
        initialized = true;
        controller = _controller;
    }
}

/**
 * TN4: Non-upgradeable contract with initialize()
 * SAFE: Not upgradeable, so no front-running risk
 * NOTE: This MIGHT be flagged as FP if contract_is_upgradeable
 * incorrectly identifies it as upgradeable due to Initializable inheritance
 */
contract NonUpgradeableContract {
    address public owner;

    // SAFE: Not upgradeable (no proxy)
    function initialize(address _owner) public {
        owner = _owner;
    }
}

/**
 * TN5: Constructor (not initializer)
 * SAFE: Constructors run at deployment, not front-runnable
 */
contract SafeWithConstructor {
    address public owner;

    // SAFE: Constructor
    constructor(address _owner) {
        owner = _owner;
    }
}

/**
 * TN6: View function named getInitializer (not state-changing)
 * SAFE: View function, can't modify state
 */
contract SafeViewFunction is Initializable {
    address public initializerAddress;

    // SAFE: View function
    function getInitializer() public view returns (address) {
        return initializerAddress;
    }
}

/**
 * TN7: Internal _initialize() helper
 * SAFE: Internal visibility, can't be called externally
 */
contract SafeInternalHelper is Initializable {
    address public owner;

    // SAFE: Internal function
    function _initialize(address _owner) internal {
        owner = _owner;
    }

    function publicInit(address _owner) external initializerModifier {
        _initialize(_owner);
    }
}

/**
 * TN8: initialize() with custom isNotInitialized modifier
 * SAFE: Custom modifier provides protection
 */
contract SafeCustomModifier is Initializable {
    address public admin;
    bool private _initialized;

    modifier isNotInitialized() {
        require(!_initialized, "Already initialized");
        _;
        _initialized = true;
    }

    // SAFE: Custom modifier provides protection
    function initialize(address _admin) external isNotInitialized {
        admin = _admin;
    }
}

// =============================================================================
// EDGE CASES (7 cases)
// =============================================================================

/**
 * EDGE1: Two-step initialization
 * Phase 1 might be vulnerable if unprotected
 */
contract EdgeTwoStepInit is Initializable {
    address public owner;
    bool public phase1Done;
    bool public phase2Done;

    // EDGE: Phase 1 - VULNERABLE if called standalone
    function initializePhase1(address _owner) public {
        require(!phase1Done, "Phase 1 done");
        owner = _owner;
        phase1Done = true;
    }

    // EDGE: Phase 2 - Protected by owner check
    function initializePhase2(uint256 config) public {
        require(msg.sender == owner, "Only owner");
        require(!phase2Done, "Phase 2 done");
        phase2Done = true;
    }
}

/**
 * EDGE2: Initializer called from constructor
 * SAFE: Constructor calls initialize, no external access
 */
contract EdgeConstructorInitialize is Initializable {
    address public owner;

    constructor(address _owner) {
        initialize(_owner);
    }

    // EDGE: Called from constructor only
    function initialize(address _owner) private {
        owner = _owner;
    }
}

/**
 * EDGE3: Initializer with version parameter but no modifier
 * VULNERABLE: Version tracking without protection is insufficient
 */
contract EdgeVersionTracking is Initializable {
    address public owner;
    uint256 public version;

    // EDGE: Version parameter doesn't provide protection
    function initialize(address _owner, uint256 _version) public {
        version = _version;
        owner = _owner;
    }
}

/**
 * EDGE4: Proxy's initialize vs implementation's initialize
 * Both should be protected
 */
contract EdgeProxyImplementation is Initializable {
    address public owner;

    // EDGE: Implementation initializer
    function initialize(address _owner) public {
        owner = _owner;
    }

    // Disable initializers in implementation
    constructor() {
        _disableInitializers();
    }
}

/**
 * EDGE5: Chained initializers (__Parent_init_unchained)
 * SAFE if parent has protection, but child might be vulnerable
 */
contract EdgeParent is Initializable {
    address public parentOwner;

    function __Parent_init(address _owner) internal onlyInitializing {
        parentOwner = _owner;
    }
}

contract EdgeChild is EdgeParent {
    address public childOwner;

    // EDGE: Child initializer without protection
    function initialize(address _parentOwner, address _childOwner) public {
        __Parent_init(_parentOwner);
        childOwner = _childOwner;
    }
}

/**
 * EDGE6: Diamond proxy facet initializer
 * Each facet might have its own initializer
 */
contract EdgeDiamondFacet is Initializable {
    address public facetOwner;

    // EDGE: Facet initializer
    function initializeFacet(address _owner) external {
        facetOwner = _owner;
    }
}

/**
 * EDGE7: Initialize with complex access control that isn't detected
 * Might be flagged if has_access_gate doesn't detect the pattern
 */
contract EdgeComplexAccessControl is Initializable {
    address public owner;
    mapping(address => bool) public authorized;

    // EDGE: Complex access control
    function initialize(address _owner) public {
        // Custom access check that might not be detected
        require(authorized[msg.sender] || owner == address(0), "Not authorized");
        owner = _owner;
    }
}

// =============================================================================
// VARIATION TESTS (6 cases)
// =============================================================================

/**
 * VAR1: Different naming - initialize vs init vs setup vs __init__
 * Tests naming pattern detection
 */
contract VariationNaming1 is Initializable {
    address public owner;

    // VARIATION: Standard naming
    function initialize(address _owner) public {
        owner = _owner;
    }
}

contract VariationNaming2 is Initializable {
    address public owner;

    // VARIATION: Shortened naming
    function init(address _owner) public {
        owner = _owner;
    }
}

contract VariationNaming3 is Initializable {
    address public owner;

    // VARIATION: Alternative naming
    function setup(address _owner) public {
        owner = _owner;
    }
}

/**
 * VAR2: Different protection mechanisms
 * Tests protection detection
 */
contract VariationProtection1 is Initializable {
    address public owner;

    // VARIATION: initializer modifier
    function initialize(address _owner) public initializerModifier {
        owner = _owner;
    }
}

contract VariationProtection2 is Initializable {
    address public owner;

    // VARIATION: onlyInitializing modifier
    function initialize(address _owner) internal onlyInitializing {
        owner = _owner;
    }
}

contract VariationProtection3 is Initializable {
    address public owner;
    bool private initialized;

    // VARIATION: Custom flag check
    function initialize(address _owner) public {
        require(!initialized, "Already initialized");
        initialized = true;
        owner = _owner;
    }
}

/**
 * VAR3: Different proxy patterns
 * Tests proxy type detection
 */
contract VariationTransparentProxy is Initializable {
    address public owner;

    // VARIATION: Transparent proxy pattern
    function initialize(address _owner) public {
        owner = _owner;
    }
}

contract VariationUUPSProxy is Initializable, UUPSUpgradeable {
    address public owner;

    // VARIATION: UUPS proxy pattern
    function initialize(address _owner) public {
        owner = _owner;
    }

    function _authorizeUpgrade(address) internal override {}
}

contract VariationBeaconProxy is Initializable {
    address public owner;
    address public beacon;

    // VARIATION: Beacon proxy pattern
    function initialize(address _owner, address _beacon) public {
        owner = _owner;
        beacon = _beacon;
    }
}

/**
 * VAR4: Different initialization complexity
 * Tests behavior detection across complexity levels
 */
contract VariationSimple is Initializable {
    address public owner;

    // VARIATION: Simple (1 state write)
    function initialize(address _owner) public {
        owner = _owner;
    }
}

contract VariationComplex is Initializable, OwnableUpgradeable {
    address public treasury;
    address public governance;
    uint256 public fee;
    uint256 public maxSupply;

    // VARIATION: Complex (multiple state writes, inheritance)
    function initialize(
        address _owner,
        address _treasury,
        address _governance,
        uint256 _fee,
        uint256 _maxSupply
    ) public {
        __Ownable_init(_owner);
        treasury = _treasury;
        governance = _governance;
        fee = _fee;
        maxSupply = _maxSupply;
    }
}

contract VariationChained is Initializable, OwnableUpgradeable {
    uint256 public value;

    // VARIATION: Chained initialization
    function initialize(address _owner, uint256 _value) public initializerModifier {
        __Ownable_init(_owner);
        value = _value;
    }
}

// =============================================================================
// COMPARISON WITH REINITIALIZER (upgrade-004)
// =============================================================================

/**
 * COMPARE1: First-time initializer (upgrade-005)
 * vs. Reinitializer (upgrade-004)
 */
contract CompareInitializeVsReinitialize is Initializable {
    address public owner;
    uint256 public value;

    // This should be caught by upgrade-005 (first-time initializer)
    function initialize(address _owner) public {
        owner = _owner;
    }

    // This should be caught by upgrade-004 (reinitializer)
    function reinitializeV2(uint256 _value) public {
        value = _value;
    }
}

/**
 * COMPARE2: Check if patterns overlap
 * Both patterns should NOT flag the same function
 */
contract CompareNoOverlap is Initializable {
    address public owner;
    uint256 public version;

    // upgrade-005: First-time, SHOULD flag
    function initialize(address _owner) public {
        owner = _owner;
        version = 1;
    }

    // upgrade-004: Reinitializer, SHOULD flag
    function reinitialize(uint256 newVersion) public {
        version = newVersion;
    }

    // Both should NOT flag this (has protection)
    function initializeV3(uint256 newVersion) public initializerModifier {
        version = newVersion;
    }
}

// =============================================================================
// TEST SUMMARY
// =============================================================================
//
// TRUE POSITIVES (10):
//   - initialize(address,uint256) in VulnerableClassic
//   - init(address) in VulnerableInit
//   - setup(address,uint256) in VulnerableSetup
//   - __init__(address) in VulnerablePythonStyle
//   - initializeContract(address,address,uint256) in VulnerableComplex
//   - setUp(address) in VulnerableSetUp
//   - initializeOwnable(address) in VulnerableInitializeOwnable
//   - initContract(address,bytes) in VulnerableInitContract
//   - initialize(address) in VulnerableUUPS
//   - initialize(address,address) in VulnerableBeacon
//
// TRUE NEGATIVES (8):
//   - initialize(address) with initializer modifier
//   - init(address) with onlyInitializing modifier
//   - setup(address) with manual flag check
//   - initialize(address) in non-upgradeable contract
//   - constructor(address)
//   - getInitializer() view function
//   - _initialize(address) internal function
//   - initialize(address) with custom modifier
//
// EDGE CASES (7):
//   - Two-step initialization
//   - Constructor calling initialize
//   - Version tracking without protection
//   - Proxy vs implementation initialize
//   - Chained initializers
//   - Diamond facet initializers
//   - Complex access control
//
// VARIATIONS (12):
//   - Naming: initialize, init, setup, __init__
//   - Protection: initializer, onlyInitializing, custom flag
//   - Proxy: Transparent, UUPS, Beacon
//   - Complexity: Simple, Complex, Chained
//
// COMPARISON TESTS (2):
//   - Initialize vs reinitialize (should be separate patterns)
//   - Overlap check (patterns should not flag same function)
//
// =============================================================================
