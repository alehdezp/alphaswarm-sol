// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// =============================================================================
// Test Contract for upgrade-004: Unprotected Reinitializer Function
// =============================================================================
//
// This contract tests detection of unprotected reinitializer functions in
// upgradeable contracts. Based on real exploits:
// - Audius (July 2022): $6M governance takeover via unprotected reinitializer
// - AllianceBlock (Aug 2024): Upgrade reset initialized flag
//
// Pattern Detection Logic:
// 1. Function is externally callable (public/external)
// 2. Function behaves like an initializer (is_initializer_function: true)
// 3. Function is NOT the main constructor (is_constructor: false)
// 4. Function lacks initializer/reinitializer modifier (has_initializer_modifier: false)
// 5. Function doesn't check initialization flag (checks_initialized_flag: false)
// 6. Function has NO access control (has_access_gate: false)

// Mock OpenZeppelin contracts for testing
abstract contract Initializable {
    uint8 private _initialized;
    bool private _initializing;

    modifier initializer() {
        require(_initialized == 0, "Already initialized");
        _initialized = 1;
        _;
    }

    modifier reinitializer(uint8 version) {
        require(version > _initialized, "Already initialized to this version");
        _initialized = version;
        _;
    }

    modifier onlyInitializing() {
        require(_initializing, "Not initializing");
        _;
    }

    function _disableInitializers() internal {
        _initialized = type(uint8).max;
    }
}

abstract contract OwnableUpgradeable {
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function __Ownable_init(address _owner) internal {
        owner = _owner;
    }
}

// =============================================================================
// TRUE POSITIVES: Unprotected Reinitializers (10 cases)
// =============================================================================

/// @title VulnerableReinitializer - Standard unprotected reinitializer patterns
contract VulnerableReinitializer is Initializable {
    address public owner;
    uint256 public version;
    uint256 public newFeatureValue;
    address public treasury;

    // Main initializer (protected - should NOT flag)
    function initialize(address _owner) external initializer {
        owner = _owner;
        version = 1;
    }

    // TP1: Unprotected reinitialize() - Standard naming
    function reinitialize(uint256 _newValue) external {
        newFeatureValue = _newValue;
        version = 2;
    }

    // TP2: Unprotected reinit() - Short form naming
    function reinit(address _newTreasury) external {
        treasury = _newTreasury;
        version = 2;
    }

    // TP3: Unprotected initializeV2() - Version naming pattern
    function initializeV2(uint256 _value, address _treasury) external {
        newFeatureValue = _value;
        treasury = _treasury;
        version = 2;
    }

    // TP4: Unprotected initV2() - Abbreviated version naming
    function initV2(address _owner, uint256 _value) external {
        owner = _owner;  // CRITICAL: Can change owner!
        newFeatureValue = _value;
        version = 2;
    }

    // TP5: Unprotected setupNewFeature() - Alternative naming
    function setupNewFeature(uint256 _value) external {
        newFeatureValue = _value;
        version = 2;
    }

    // TP6: Unprotected setupV2() - Setup pattern
    function setupV2(address _treasury) external {
        treasury = _treasury;
        version = 2;
    }

    // TP7: Unprotected reInitialize() - Different case pattern
    function reInitialize(uint256 _value) external {
        newFeatureValue = _value;
        version = 2;
    }

    // TP8: Unprotected initializePhase2() - Phase naming
    function initializePhase2(address _owner) external {
        owner = _owner;  // CRITICAL: Can change owner!
        version = 2;
    }

    // TP9: Unprotected reinitializeV3() - Higher version
    function reinitializeV3(address _treasury, uint256 _value) external {
        treasury = _treasury;
        newFeatureValue = _value;
        version = 3;
    }

    // TP10: Unprotected upgradeToAndInit() - Upgrade pattern
    function upgradeToAndInit(address _newImpl, uint256 _value) external {
        // In real scenario, would upgrade implementation
        newFeatureValue = _value;
        version = 2;
    }
}

/// @title AudiusStyleVulnerable - Simulates Audius governance vulnerability
contract AudiusStyleVulnerable is Initializable {
    address public governance;
    uint256 public votingPower;
    address public treasury;

    function initialize(address _governance) external initializer {
        governance = _governance;
    }

    // TP11: Governance takeover vulnerability (Audius-style)
    // This function allowed attacker to gain 10 trillion voting power
    function initializeGovernanceV2(address _newGovernance, uint256 _power) external {
        governance = _newGovernance;
        votingPower = _power;  // Attacker sets arbitrary voting power
    }
}

/// @title AllianceBlockStyleVulnerable - Simulates AllianceBlock pattern
contract AllianceBlockStyleVulnerable is Initializable {
    address public owner;
    bool public initialized;

    function initialize(address _owner) external {
        require(!initialized, "Already initialized");
        owner = _owner;
        initialized = true;
    }

    // TP12: After upgrade, if 'initialized' gets reset to false
    // (storage collision), this becomes callable again
    function reinitializeAfterUpgrade(address _newOwner) external {
        // Missing check: require(!initialized)
        owner = _newOwner;
    }
}

// =============================================================================
// TRUE NEGATIVES: Properly Protected Reinitializers (8 cases)
// =============================================================================

/// @title SafeReinitializer - Properly protected patterns
contract SafeReinitializer is Initializable, OwnableUpgradeable {
    uint256 public version;
    uint256 public newFeatureValue;
    address public treasury;
    bool public initializedV2;
    bool public initializedV3;

    function initialize(address _owner) external initializer {
        __Ownable_init(_owner);
        version = 1;
    }

    // TN1: Protected with reinitializer(2) modifier
    function reinitialize(uint256 _value) external reinitializer(2) {
        newFeatureValue = _value;
        version = 2;
    }

    // TN2: Protected with onlyInitializing modifier
    function initializeV2(uint256 _value) external onlyInitializing {
        newFeatureValue = _value;
        version = 2;
    }

    // TN3: Protected with custom initialization check
    function reinitV3WithCheck(address _treasury) external {
        require(!initializedV3, "Already initialized V3");
        initializedV3 = true;
        treasury = _treasury;
        version = 3;
    }

    // TN4: Protected with access control (onlyOwner)
    function initV3OnlyOwner(uint256 _value) external onlyOwner {
        newFeatureValue = _value;
        version = 3;
    }

    // TN5: Protected with if-revert pattern
    function reinitWithRevert(uint256 _value) external {
        if (initializedV2) revert("Already initialized");
        initializedV2 = true;
        newFeatureValue = _value;
    }

    // TN6: Internal function (not externally callable)
    function _reinitializeInternal(uint256 _value) internal {
        newFeatureValue = _value;
        version = 2;
    }

    // TN7: View function (can't modify state)
    function getInitializedVersion() external view returns (uint256) {
        return version;
    }

    // TN8: Protected with both access control AND initialization check
    function reinitSecure(uint256 _value) external onlyOwner {
        require(!initializedV2, "Already initialized");
        initializedV2 = true;
        newFeatureValue = _value;
    }
}

/// @title NonUpgradeableContract - Not upgradeable, should NOT flag
contract NonUpgradeableContract {
    address public owner;
    uint256 public value;

    // TN9: Constructor (not upgradeable pattern)
    constructor(address _owner) {
        owner = _owner;
    }

    // TN10: Regular function in non-upgradeable contract
    // Even though it looks like initializer, contract is not upgradeable
    function initialize(uint256 _value) external {
        value = _value;
    }
}

// =============================================================================
// EDGE CASES: Boundary Conditions (7 cases)
// =============================================================================

/// @title TwoStepInitialization - Two-step proposal + execute pattern
contract TwoStepInitialization is Initializable, OwnableUpgradeable {
    uint256 public proposedValue;
    uint256 public actualValue;
    uint256 public proposalTimestamp;

    function initialize(address _owner) external initializer {
        __Ownable_init(_owner);
    }

    // EDGE1: Proposal step (onlyOwner protected - TN)
    function proposeReinitialize(uint256 _value) external onlyOwner {
        proposedValue = _value;
        proposalTimestamp = block.timestamp;
    }

    // EDGE2: Execute step - VULNERABLE if no timelock check
    // Should FLAG as TP because anyone can execute
    function executeReinitialize() external {
        actualValue = proposedValue;
    }
}

/// @title ProxyUpgradePattern - Called from proxy's upgradeToAndCall
contract ProxyUpgradePattern is Initializable {
    uint256 public value;

    // EDGE3: Reinitializer meant to be called via delegatecall
    // Still VULNERABLE if proxy doesn't protect the call
    function initializeV2(uint256 _value) external {
        value = _value;
    }
}

/// @title VersionCheckOnly - Has version check but no boolean flag
contract VersionCheckOnly is Initializable {
    uint256 public contractVersion;
    uint256 public value;

    function initialize() external initializer {
        contractVersion = 1;
    }

    // EDGE4: Only checks version, but check is in wrong place
    // VULNERABLE because require is AFTER state write
    function reinitializeWrongOrder(uint256 _value) external {
        value = _value;
        contractVersion = 2;
        require(contractVersion > 1, "Invalid version");  // Too late!
    }

    // EDGE5: Proper version check before state changes (TN)
    function reinitializeCorrectOrder(uint256 _value) external {
        require(contractVersion < 2, "Already v2");
        contractVersion = 2;
        value = _value;
    }
}

/// @title EmergencyReinitializer - Emergency functions
contract EmergencyReinitializer is Initializable, OwnableUpgradeable {
    bool public paused;
    uint256 public value;

    function initialize(address _owner) external initializer {
        __Ownable_init(_owner);
    }

    // EDGE6: Emergency reinitializer for bug fixes
    // VULNERABLE despite emergency purpose - needs protection
    function emergencyReinitialize(uint256 _safeValue) external {
        value = _safeValue;
        paused = false;
    }

    // EDGE7: Emergency reinitializer with proper protection (TN)
    function emergencyReinitializeSafe(uint256 _safeValue) external onlyOwner {
        value = _safeValue;
        paused = false;
    }
}

/// @title DiamondFacetReinitializer - Diamond pattern facet
contract DiamondFacetReinitializer {
    // Storage at specific slot for diamond pattern
    bytes32 constant DIAMOND_STORAGE_POSITION = keccak256("diamond.storage");

    struct DiamondStorage {
        address owner;
        uint256 value;
        bool initialized;
    }

    function diamondStorage() internal pure returns (DiamondStorage storage ds) {
        bytes32 position = DIAMOND_STORAGE_POSITION;
        assembly {
            ds.slot := position
        }
    }

    // EDGE8: Diamond facet reinitializer - VULNERABLE
    function initializeFacetV2(uint256 _value) external {
        DiamondStorage storage ds = diamondStorage();
        ds.value = _value;
    }

    // EDGE9: Diamond facet with guard (TN)
    function initializeFacetV2Safe(uint256 _value) external {
        DiamondStorage storage ds = diamondStorage();
        require(!ds.initialized, "Already initialized");
        ds.initialized = true;
        ds.value = _value;
    }
}

/// @title StorageGuardOnly - Protected only by storage variable
contract StorageGuardOnly is Initializable {
    uint256 public value;
    bool private _initializedV2;

    function initialize() external initializer {
        value = 1;
    }

    // EDGE10: Storage flag check (should be TN if checks_initialized_flag detects it)
    function reinitWithStorageFlag(uint256 _value) external {
        require(!_initializedV2, "Already initialized V2");
        _initializedV2 = true;
        value = _value;
    }
}

// =============================================================================
// VARIATION TESTS: Different Naming & Protection Patterns (6 variations)
// =============================================================================

/// @title NamingVariations - Test different naming conventions
contract NamingVariations is Initializable {
    uint256 public value;

    function initialize() external initializer {
        value = 1;
    }

    // VAR1: configure pattern (TP)
    function configure(uint256 _value) external {
        value = _value;
    }

    // VAR2: setup pattern (TP)
    function setup(uint256 _value) external {
        value = _value;
    }

    // VAR3: config pattern (TP)
    function config(uint256 _value) external {
        value = _value;
    }

    // VAR4: reset pattern (TP)
    function reset(uint256 _value) external {
        value = _value;
    }
}

/// @title ProtectionVariations - Different protection mechanisms
contract ProtectionVariations is Initializable, OwnableUpgradeable {
    uint256 public value;
    bool public initializedV2;
    uint256 public version;
    mapping(address => bool) public admins;

    function initialize(address _owner) external initializer {
        __Ownable_init(_owner);
        admins[_owner] = true;
        version = 1;
    }

    // VAR5: Custom modifier protection (TN)
    modifier onlyAdmin() {
        require(admins[msg.sender], "Not admin");
        _;
    }

    function reinitWithCustomModifier(uint256 _value) external onlyAdmin {
        value = _value;
    }

    // VAR6: msg.sender check (TN)
    function reinitWithMsgSenderCheck(uint256 _value) external {
        require(msg.sender == owner, "Not owner");
        value = _value;
    }

    // VAR7: Multiple require statements (TN)
    function reinitWithMultipleChecks(uint256 _value) external {
        require(msg.sender == owner, "Not owner");
        require(!initializedV2, "Already initialized");
        require(version < 2, "Already v2");
        initializedV2 = true;
        version = 2;
        value = _value;
    }
}

/// @title ProxyPatternVariations - Different proxy patterns
contract TransparentProxyImplementation is Initializable, OwnableUpgradeable {
    uint256 public value;

    function initialize(address _owner) external initializer {
        __Ownable_init(_owner);
    }

    // VAR8: Transparent proxy reinitializer (TP)
    function initializeV2Transparent(uint256 _value) external {
        value = _value;
    }
}

contract UUPSImplementation is Initializable, OwnableUpgradeable {
    uint256 public value;

    function initialize(address _owner) external initializer {
        __Ownable_init(_owner);
    }

    // VAR9: UUPS reinitializer (TP)
    function initializeV2UUPS(uint256 _value) external {
        value = _value;
    }

    // UUPS upgrade function (should NOT flag - not an initializer)
    function upgradeTo(address newImplementation) external onlyOwner {
        // Upgrade logic
    }
}

contract BeaconImplementation is Initializable {
    uint256 public value;

    function initialize() external initializer {
        value = 1;
    }

    // VAR10: Beacon proxy reinitializer (TP)
    function initializeV2Beacon(uint256 _value) external {
        value = _value;
    }
}

// =============================================================================
// SUMMARY
// =============================================================================
//
// TRUE POSITIVES (Expected to FLAG): 24 functions
// - VulnerableReinitializer: 10 (reinitialize, reinit, initializeV2, initV2,
//   setupNewFeature, setupV2, reInitialize, initializePhase2, reinitializeV3,
//   upgradeToAndInit)
// - AudiusStyleVulnerable: 1 (initializeGovernanceV2)
// - AllianceBlockStyleVulnerable: 1 (reinitializeAfterUpgrade)
// - TwoStepInitialization: 1 (executeReinitialize)
// - ProxyUpgradePattern: 1 (initializeV2)
// - VersionCheckOnly: 1 (reinitializeWrongOrder)
// - EmergencyReinitializer: 1 (emergencyReinitialize)
// - DiamondFacetReinitializer: 1 (initializeFacetV2)
// - NamingVariations: 4 (configure, setup, config, reset)
// - TransparentProxyImplementation: 1 (initializeV2Transparent)
// - UUPSImplementation: 1 (initializeV2UUPS)
// - BeaconImplementation: 1 (initializeV2Beacon)
//
// TRUE NEGATIVES (Should NOT flag): 20 functions
// - SafeReinitializer: 8 (various protected patterns)
// - NonUpgradeableContract: 2 (constructor, initialize)
// - TwoStepInitialization: 1 (proposeReinitialize)
// - VersionCheckOnly: 1 (reinitializeCorrectOrder)
// - EmergencyReinitializer: 1 (emergencyReinitializeSafe)
// - DiamondFacetReinitializer: 1 (initializeFacetV2Safe)
// - StorageGuardOnly: 1 (reinitWithStorageFlag)
// - ProtectionVariations: 3 (various protected patterns)
// - All main initialize() functions: 10+ (protected with initializer modifier)
//
// EDGE CASES: 10 scenarios tested
// VARIATIONS: 10 different patterns tested
//
// Expected Metrics:
// - True Positives: ~24
// - True Negatives: ~20
// - False Positives: 0 (ideally)
// - False Negatives: 0 (ideally)
// - Precision: TP / (TP + FP) = 24 / 24 = 100%
// - Recall: TP / (TP + FN) = 24 / 24 = 100%
// - Target Status: EXCELLENT (precision >= 90%, recall >= 85%)
