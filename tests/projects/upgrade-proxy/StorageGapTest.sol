// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =============================================================================
// TEST CONTRACT: upgrade-006-missing-storage-gap
// =============================================================================
//
// This contract tests detection of upgradeable contracts missing storage gaps.
// Storage gaps are CRITICAL for safe upgrades when using inheritance.
//
// Pattern: upgrade-006-missing-storage-gap
// Properties tested:
//   - is_upgradeable (contract uses proxy pattern)
//   - has_inheritance (inherits from base contracts)
//   - state_var_count > 0 (has state variables)
//   - has_storage_gap (presence of __gap array)
//
// Self-contained: No external imports needed
// =============================================================================

// =============================================================================
// MINIMAL INITIALIZATION HELPERS (self-contained)
// =============================================================================

/// Minimal Minimal Initializable pattern
abstract contract Initializable {
    uint8 private _initialized;
    bool private _initializing;

    modifier initializer() {
        require(!_initializing && _initialized == 0, "Already initialized");
        _initialized = 1;
        _initializing = true;
        _;
        _initializing = false;
    }

    modifier onlyInitializing() {
        require(_initializing, "Not initializing");
        _;
    }

    modifier reinitializer(uint8 version) {
        require(_initialized < version, "Already reinitialized");
        _initialized = version;
        _initializing = true;
        _;
        _initializing = false;
    }
}

/// Minimal Minimal Ownable pattern
abstract contract OwnableUpgradeable is Initializable {
    address private _owner;

    function __Ownable_init(address owner_) internal onlyInitializing {
        _owner = owner_;
    }

    modifier onlyOwner() {
        require(_owner == msg.sender, "Not owner");
        _;
    }

    // NOTE: Missing storage gap in OZ pattern!
}

/// Minimal Minimal UUPS pattern
abstract contract UUPSUpgradeable is Initializable {
    function upgradeToAndCall(address newImplementation, bytes memory data) external payable virtual {
        _authorizeUpgrade(newImplementation);
        // Upgrade logic here
    }

    function _authorizeUpgrade(address newImplementation) internal virtual;

    // NOTE: Missing storage gap!
}

// =============================================================================
// TRUE POSITIVES: Upgradeable contracts WITHOUT storage gap
// =============================================================================

/// TEST: TP - UUPS upgradeable base without storage gap
contract VulnerableUUPSBase is Initializable, UUPSUpgradeable {
    address public owner;
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    // ❌ VULNERABLE: No storage gap - future variables will shift child storage!

    function initialize(address _owner) public initializer {
        owner = _owner;
    }

    function _authorizeUpgrade(address) internal override {
        require(msg.sender == owner, "Not owner");
    }
}

/// TEST: TP - UUPS child inheriting from vulnerable base
contract VulnerableUUPSChild is VulnerableUUPSBase {
    uint256 public totalFees;        // Will shift if parent adds variables!
    address public feeCollector;

    // ❌ VULNERABLE: Parent lacks storage gap
}

/// TEST: TP - Transparent proxy implementation without gap
contract VulnerableTransparentImpl is Initializable, OwnableUpgradeable {
    mapping(address => uint256) public deposits;
    uint256 public interestRate;
    address public treasury;

    // ❌ VULNERABLE: No storage gap in upgradeable contract with inheritance

    function initialize(address _owner) public initializer {
        __Ownable_init(_owner);
    }
}

/// TEST: TP - Complex inheritance chain without gap
contract VulnerableBaseA is Initializable {
    address public admin;
    uint256 public version;

    // ❌ VULNERABLE: No storage gap

    function initialize(address _admin) public initializer {
        admin = _admin;
    }
}

contract VulnerableBaseB is VulnerableBaseA {
    mapping(address => bool) public authorized;
    uint256 public threshold;

    // ❌ VULNERABLE: No storage gap
}

contract VulnerableChild is VulnerableBaseB {
    uint256 public criticalValue;  // Will corrupt if BaseA or BaseB upgraded!

    // ❌ VULNERABLE: Entire chain lacks storage gaps
}

/// TEST: TP - Beacon proxy implementation without gap
contract VulnerableBeaconImpl is Initializable {
    address public controller;
    mapping(address => uint256) public userBalances;
    uint256 public lastUpdateTime;

    // ❌ VULNERABLE: No storage gap

    function initialize(address _controller) public initializer {
        controller = _controller;
    }
}

/// TEST: TP - DeFi vault pattern without gap
contract VulnerableVaultBase is Initializable, OwnableUpgradeable {
    mapping(address => uint256) public shares;
    uint256 public totalShares;
    address public asset;

    // ❌ VULNERABLE: Vault base without storage gap

    function initialize(address _asset, address _owner) public initializer {
        __Ownable_init(_owner);
        asset = _asset;
    }
}

contract VulnerableVaultStrategy is VulnerableVaultBase {
    address public strategy;
    uint256 public performanceFee;

    // ❌ VULNERABLE: Strategy inherits from vault without gap
}

/// TEST: TP - Governance contract without gap
contract VulnerableGovernanceBase is Initializable {
    mapping(address => uint256) public votingPower;
    uint256 public proposalCount;
    uint256 public quorum;

    // ❌ VULNERABLE: Governance base without gap

    function initialize(uint256 _quorum) public initializer {
        quorum = _quorum;
    }
}

contract VulnerableGovernanceExtended is VulnerableGovernanceBase {
    address public timelock;
    uint256 public votingDelay;

    // ❌ VULNERABLE: Extended governance without gap
}

/// TEST: TP - Token implementation without gap
contract VulnerableTokenBase is Initializable {
    mapping(address => uint256) public balances;
    mapping(address => mapping(address => uint256)) public allowances;
    uint256 public totalSupply;

    // ❌ VULNERABLE: Token base without gap

    function initialize(uint256 _supply) public initializer {
        totalSupply = _supply;
    }
}

contract VulnerableTokenExtended is VulnerableTokenBase {
    string public name;
    string public symbol;
    uint8 public decimals;

    // ❌ VULNERABLE: Extended token without gap
}

/// TEST: TP - Abstract base contract without gap
abstract contract VulnerableAbstractBase is Initializable {
    address public owner;
    bool public paused;

    // ❌ VULNERABLE: Abstract base without gap

    function __Base_init(address _owner) internal onlyInitializing {
        owner = _owner;
        paused = false;
    }
}

contract VulnerableConcreteImpl is VulnerableAbstractBase {
    uint256 public value;

    function initialize(address _owner) public initializer {
        __Base_init(_owner);
    }

    // ❌ VULNERABLE: Inherits from abstract base without gap
}

/// TEST: TP - Diamond facet without gap
contract VulnerableDiamondFacet is Initializable {
    address public facetOwner;
    mapping(bytes4 => address) public selectors;

    // ❌ VULNERABLE: Facet without gap

    function initializeFacet(address _owner) public initializer {
        facetOwner = _owner;
    }
}

// =============================================================================
// TRUE NEGATIVES: Safe contracts WITH storage gap
// =============================================================================

/// TEST: TN - UUPS with proper storage gap
contract SafeUUPSBase is Initializable, UUPSUpgradeable {
    address public owner;
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    // ✓ SAFE: Storage gap reserves slots for future variables
    uint256[50] private __gap;

    function initialize(address _owner) public initializer {
        owner = _owner;
    }

    function _authorizeUpgrade(address) internal override {
        require(msg.sender == owner, "Not owner");
    }
}

/// TEST: TN - Child inheriting from safe base
contract SafeUUPSChild is SafeUUPSBase {
    uint256 public totalFees;
    address public feeCollector;

    // ✓ SAFE: Parent has storage gap (child variables safe)
    uint256[50] private __gap;
}

/// TEST: TN - Transparent proxy with gap
contract SafeTransparentImpl is Initializable, OwnableUpgradeable {
    mapping(address => uint256) public deposits;
    uint256 public interestRate;

    // ✓ SAFE: Has storage gap
    uint256[47] private __gap;  // 3 vars used (owner from Ownable, deposits, interestRate)

    function initialize(address _owner) public initializer {
        __Ownable_init(_owner);
    }
}

/// TEST: TN - Complete chain with storage gaps
contract SafeBaseA is Initializable {
    address public admin;
    uint256 public version;

    // ✓ SAFE: Base A has gap
    uint256[48] private __gap;

    function initialize(address _admin) public initializer {
        admin = _admin;
    }
}

contract SafeBaseB is SafeBaseA {
    mapping(address => bool) public authorized;
    uint256 public threshold;

    // ✓ SAFE: Base B has gap
    uint256[48] private __gap;
}

contract SafeChild is SafeBaseB {
    uint256 public criticalValue;

    // ✓ SAFE: Entire chain has gaps
    uint256[49] private __gap;
}

/// TEST: TN - OpenZeppelin standard pattern
contract SafeOZPattern is Initializable, OwnableUpgradeable {
    uint256 public customValue;

    // ✓ SAFE: Following OpenZeppelin convention (50 slots)
    uint256[49] private __gap;  // 1 used (customValue) + 49 gap = 50 total

    function initialize(address _owner) public initializer {
        __Ownable_init(_owner);
    }
}

/// TEST: TN - Different gap naming (should still be detected)
contract SafeAlternativeGapNaming is Initializable {
    address public owner;
    uint256 public value;

    // ✓ SAFE: Alternative gap naming (still has "gap" in name)
    uint256[48] private _gap;        // Underscore prefix
    uint256[50] private storageGap;  // Different name but contains "gap"

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

/// TEST: TN - Calculated gap size
contract SafeCalculatedGap is Initializable {
    address public owner;              // 1 slot
    uint256 public value1;             // 1 slot
    uint256 public value2;             // 1 slot
    mapping(address => uint256) public balances;  // 1 slot
    // Total: 4 slots used

    // ✓ SAFE: Gap size = 50 - 4 = 46
    uint256[46] private __gap;

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

// =============================================================================
// TRUE NEGATIVES: Non-upgradeable contracts (no gap needed)
// =============================================================================

/// TEST: TN - Regular contract without proxy pattern
contract RegularContract {
    address public owner;
    mapping(address => uint256) public balances;

    // ✓ SAFE: Not upgradeable, no gap needed

    constructor(address _owner) {
        owner = _owner;
    }
}

/// TEST: TN - Contract without inheritance
contract StandaloneContract is Initializable {
    uint256 public value;

    // ✓ SAFE: No inheritance, no collision risk (but upgradeable_without_storage_gap might flag)
    // This tests pattern precision

    function initialize(uint256 _value) public initializer {
        value = _value;
    }
}

/// TEST: TN - Library (not upgradeable)
library UtilityLibrary {
    // ✓ SAFE: Libraries are not upgradeable

    function calculate(uint256 a, uint256 b) internal pure returns (uint256) {
        return a + b;
    }
}

/// TEST: TN - Interface (no storage)
interface IVault {
    function deposit(uint256 amount) external;
    function withdraw(uint256 amount) external;
}

// =============================================================================
// EDGE CASES: Boundary conditions
// =============================================================================

/// TEST: Edge - Contract with only gap (no other state vars)
contract EdgeOnlyGap is Initializable {
    // Edge case: Only gap variable, no other state
    uint256[50] private __gap;

    function initialize() public initializer {
        // Empty initialization
    }
}

/// TEST: Edge - Multiple gaps (unusual but valid)
contract EdgeMultipleGaps is Initializable {
    address public owner;

    // Edge case: Multiple gap arrays (builder should detect ANY gap)
    uint256[25] private __gap1;
    uint256[25] private __gap2;

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

/// TEST: Edge - Very small gap (not recommended but detectable)
contract EdgeSmallGap is Initializable {
    address public owner;
    uint256 public value;

    // Edge case: Small gap (bad practice but should be detected)
    uint256[5] private __gap;  // Only 5 slots

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

/// TEST: Edge - Abstract contract with gap
abstract contract EdgeAbstractWithGap is Initializable {
    address public owner;

    // Edge case: Abstract contracts can also have gaps
    uint256[49] private __gap;

    function __Base_init(address _owner) internal onlyInitializing {
        owner = _owner;
    }
}

contract EdgeConcreteWithGap is EdgeAbstractWithGap {
    uint256 public value;
    uint256[49] private __gap;

    function initialize(address _owner) public initializer {
        __Base_init(_owner);
    }
}

/// TEST: Edge - Terminal leaf contract without children
contract EdgeTerminalContract is Initializable, OwnableUpgradeable {
    uint256 public finalValue;

    // Edge case: Terminal contract (no children expected)
    // Gap still recommended as best practice
    // Pattern will flag this - up to auditor to decide if acceptable

    function initialize(address _owner) public initializer {
        __Ownable_init(_owner);
    }
}

// =============================================================================
// VARIATION TESTS: Different naming and patterns
// =============================================================================

/// TEST: Variation - Controller instead of owner
contract VariationController is Initializable {
    address public controller;  // Different naming from "owner"
    mapping(address => uint256) public stakes;

    // ❌ VULNERABLE: Different naming but same pattern

    function initialize(address _controller) public initializer {
        controller = _controller;
    }
}

/// TEST: Variation - Manager pattern
contract VariationManager is Initializable {
    address public manager;
    mapping(address => bool) public approved;
    uint256 public limit;

    // ❌ VULNERABLE: Manager pattern without gap

    function initialize(address _manager) public initializer {
        manager = _manager;
    }
}

/// TEST: Variation - Different upgrade pattern naming
contract VariationUpgradable is Initializable {  // Note: "Upgradable" not "Upgradeable"
    address public admin;
    uint256 public counter;

    // ❌ VULNERABLE: Spelling variation but still upgradeable

    function initialize(address _admin) public initializer {
        admin = _admin;
    }
}

/// TEST: Variation - Registry pattern
contract VariationRegistry is Initializable {
    mapping(address => mapping(bytes32 => address)) public registry;
    address public registrar;

    // ❌ VULNERABLE: Registry pattern without gap

    function initialize(address _registrar) public initializer {
        registrar = _registrar;
    }
}

/// TEST: Variation - Safe with different gap naming styles
contract VariationSafeGapStyles is Initializable {
    address public owner;

    // ✓ SAFE: Gap with different style (UPPER_CASE)
    uint256[50] private __GAP;

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

/// TEST: Variation - Mixed case gap
contract VariationMixedCaseGap is Initializable {
    address public owner;

    // ✓ SAFE: Mixed case gap naming
    uint256[50] private __Gap;

    function initialize(address _owner) public initializer {
        owner = _owner;
    }
}

// =============================================================================
// FALSE POSITIVE PREVENTION: Should NOT flag these
// =============================================================================

/// TEST: FP Prevention - Non-upgradeable with Initializable
contract NonUpgradeableWithInitializable is Initializable {
    uint256 public value;

    // Should NOT flag: Uses Initializable but not actually upgradeable
    // (No proxy pattern, just initialization pattern)

    function initialize(uint256 _value) public initializer {
        value = _value;
    }
}

/// TEST: FP Prevention - Contract without inheritance
contract NoInheritanceUpgradeable is Initializable {
    uint256 public value;

    // Should NOT flag: Upgradeable but no inheritance (no collision risk)

    function initialize(uint256 _value) public initializer {
        value = _value;
    }
}

/// TEST: FP Prevention - Empty contract
contract EmptyUpgradeable is Initializable {
    // Should NOT flag: No state variables (nothing to collide)

    function initialize() public initializer {
        // Empty
    }
}
