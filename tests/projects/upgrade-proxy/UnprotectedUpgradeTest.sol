// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Unprotected Upgrade Function Test Contract
 * @notice Comprehensive test coverage for upgrade-007 pattern
 * @dev Tests detection of upgrade functions WITHOUT access control
 *
 * Test Categories:
 * - TRUE POSITIVES: Unprotected upgrade functions (should flag)
 * - TRUE NEGATIVES: Protected upgrade functions (should NOT flag)
 * - EDGE CASES: Boundary conditions
 * - VARIATIONS: Different naming and proxy types
 */

// =============================================================================
// TRUE POSITIVES: Unprotected Upgrade Functions
// =============================================================================

/**
 * @notice TP: Classic UUPS with unprotected _authorizeUpgrade
 */
contract VulnerableUUPSClassic {
    address public implementation;
    bool private initialized;

    function initialize(address _implementation) external {
        require(!initialized, "Already initialized");
        implementation = _implementation;
        initialized = true;
    }

    // VULNERABLE: No access control (TP)
    function _authorizeUpgrade(address newImplementation) external {
        implementation = newImplementation;
    }

    function upgradeToAndCall(address newImplementation, bytes calldata data) external {
        implementation = newImplementation;
        (bool success,) = newImplementation.delegatecall(data);
        require(success, "Upgrade failed");
    }
}

/**
 * @notice TP: Transparent proxy with unprotected upgradeTo
 */
contract VulnerableTransparentProxy {
    address public implementation;

    // VULNERABLE: Anyone can upgrade (TP)
    function upgradeTo(address newImplementation) external {
        implementation = newImplementation;
    }

    // VULNERABLE: Anyone can upgrade with call (TP)
    function upgradeToAndCall(address newImplementation, bytes calldata data) external {
        implementation = newImplementation;
        (bool success,) = newImplementation.delegatecall(data);
        require(success);
    }
}

/**
 * @notice TP: Beacon proxy with unprotected beacon upgrade
 */
contract VulnerableBeaconProxy {
    address public beacon;

    // VULNERABLE: Anyone can change beacon (TP)
    function upgradeBeacon(address newBeacon) external {
        beacon = newBeacon;
    }

    // VULNERABLE: Anyone can set implementation via beacon (TP)
    function setBeacon(address _beacon) external {
        beacon = _beacon;
    }
}

/**
 * @notice TP: Alternative naming patterns
 */
contract VulnerableAlternativeNaming {
    address public implementation;

    // VULNERABLE: setImplementation without protection (TP)
    function setImplementation(address newImpl) external {
        implementation = newImpl;
    }

    // VULNERABLE: updateImplementation without protection (TP)
    function updateImplementation(address newImpl) external {
        implementation = newImpl;
    }

    // VULNERABLE: changeImplementation without protection (TP)
    function changeImplementation(address newImpl) external {
        implementation = newImpl;
    }
}

/**
 * @notice TP: Diamond proxy pattern
 */
contract VulnerableDiamondProxy {
    mapping(bytes4 => address) public facets;

    // VULNERABLE: Anyone can add facets (TP)
    function addFacet(bytes4[] calldata selectors, address facet) external {
        for (uint i = 0; i < selectors.length; i++) {
            facets[selectors[i]] = facet;
        }
    }

    // VULNERABLE: Anyone can replace facets (TP)
    function replaceFacet(bytes4[] calldata selectors, address newFacet) external {
        for (uint i = 0; i < selectors.length; i++) {
            facets[selectors[i]] = newFacet;
        }
    }

    // VULNERABLE: Anyone can remove facets (TP)
    function removeFacet(bytes4[] calldata selectors) external {
        for (uint i = 0; i < selectors.length; i++) {
            delete facets[selectors[i]];
        }
    }
}

/**
 * @notice TP: Minimal proxy pattern
 */
contract VulnerableMinimalProxy {
    address public implementation;

    // VULNERABLE: Anyone can upgrade minimal proxy (TP)
    function setImplementation(address _impl) external {
        implementation = _impl;
    }
}

/**
 * @notice TP: Custom upgrade mechanism
 */
contract VulnerableCustomUpgrade {
    address public logic;

    // VULNERABLE: Custom upgrade function without protection (TP)
    function upgradeLogic(address newLogic) external {
        logic = newLogic;
    }

    // VULNERABLE: Direct logic replacement (TP)
    function replaceLogic(address newLogic) external {
        logic = newLogic;
    }
}

// =============================================================================
// TRUE NEGATIVES: Protected Upgrade Functions
// =============================================================================

/**
 * @notice TN: UUPS with onlyOwner protection
 */
contract SafeUUPSWithOnlyOwner {
    address public owner;
    address public implementation;
    bool private initialized;

    function initialize(address _owner, address _implementation) external {
        require(!initialized, "Already initialized");
        owner = _owner;
        implementation = _implementation;
        initialized = true;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    // SAFE: Protected with onlyOwner (TN)
    function _authorizeUpgrade(address newImplementation) external onlyOwner {
        implementation = newImplementation;
    }

    // SAFE: Protected upgrade call (TN)
    function upgradeToAndCall(address newImplementation, bytes calldata data) external onlyOwner {
        implementation = newImplementation;
        (bool success,) = newImplementation.delegatecall(data);
        require(success);
    }
}

/**
 * @notice TN: Transparent proxy with admin protection
 */
contract SafeTransparentWithAdmin {
    address public admin;
    address public implementation;

    constructor(address _admin, address _implementation) {
        admin = _admin;
        implementation = _implementation;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }

    // SAFE: Protected with onlyAdmin (TN)
    function upgradeTo(address newImplementation) external onlyAdmin {
        implementation = newImplementation;
    }

    // SAFE: Protected upgrade with call (TN)
    function upgradeToAndCall(address newImplementation, bytes calldata data) external onlyAdmin {
        implementation = newImplementation;
        (bool success,) = newImplementation.delegatecall(data);
        require(success);
    }
}

/**
 * @notice TN: Role-based access control
 */
contract SafeWithRoleControl {
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    mapping(address => mapping(bytes32 => bool)) public roles;
    address public implementation;

    function grantRole(bytes32 role, address account) external {
        roles[account][role] = true;
    }

    modifier onlyRole(bytes32 role) {
        require(roles[msg.sender][role], "Missing role");
        _;
    }

    // SAFE: Protected with role-based access (TN)
    function _authorizeUpgrade(address newImplementation) external onlyRole(UPGRADER_ROLE) {
        implementation = newImplementation;
    }
}

/**
 * @notice TN: Manual require check
 */
contract SafeWithManualCheck {
    address public governance;
    address public implementation;

    constructor(address _governance) {
        governance = _governance;
    }

    // SAFE: Manual permission check (TN)
    function upgradeTo(address newImplementation) external {
        require(msg.sender == governance, "Only governance");
        implementation = newImplementation;
    }

    // SAFE: Alternative manual check (TN)
    function setImplementation(address newImpl) external {
        if (msg.sender != governance) revert("Unauthorized");
        implementation = newImpl;
    }
}

/**
 * @notice TN: Multi-sig protection
 */
contract SafeWithMultiSig {
    address public multiSig;
    address public implementation;

    constructor(address _multiSig) {
        multiSig = _multiSig;
    }

    modifier onlyMultiSig() {
        require(msg.sender == multiSig, "Only multi-sig");
        _;
    }

    // SAFE: Protected by multi-sig (TN)
    function _authorizeUpgrade(address newImplementation) external onlyMultiSig {
        implementation = newImplementation;
    }
}

/**
 * @notice TN: Timelock protection
 */
contract SafeWithTimelock {
    address public timelock;
    address public implementation;

    constructor(address _timelock) {
        timelock = _timelock;
    }

    modifier onlyTimelock() {
        require(msg.sender == timelock, "Only timelock");
        _;
    }

    // SAFE: Protected by timelock (TN)
    function upgradeTo(address newImplementation) external onlyTimelock {
        implementation = newImplementation;
    }
}

/**
 * @notice TN: Internal helper function
 */
contract SafeInternalHelper {
    address public owner;
    address public implementation;

    constructor(address _owner) {
        owner = _owner;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    // SAFE: Internal function (not externally callable) (TN)
    function _setImplementation(address newImpl) internal {
        implementation = newImpl;
    }

    // SAFE: Public wrapper with access control calls internal (TN)
    function upgradeToAndCall(address newImpl, bytes calldata data) external onlyOwner {
        _setImplementation(newImpl);
        (bool success,) = newImpl.delegatecall(data);
        require(success);
    }
}

// =============================================================================
// EDGE CASES: Boundary Conditions
// =============================================================================

/**
 * @notice Edge: View/pure function (cannot upgrade)
 */
contract EdgeViewFunction {
    address public implementation;

    // SAFE: View function cannot modify state (TN)
    function getImplementation() external view returns (address) {
        return implementation;
    }

    // SAFE: Pure function cannot modify state (TN)
    function calculateImplementationAddress(address base, uint256 offset) external pure returns (address) {
        return address(uint160(uint256(uint160(base)) + offset));
    }
}

/**
 * @notice Edge: Upgrade function that checks different authority
 */
contract EdgeControllerNaming {
    address public controller;
    address public implementation;

    function setController(address _controller) external {
        require(msg.sender == controller, "Only controller");
        controller = _controller;
    }

    modifier onlyController() {
        require(msg.sender == controller, "Only controller");
        _;
    }

    // SAFE: Protected by controller (TN)
    function upgradeTo(address newImpl) external onlyController {
        implementation = newImpl;
    }
}

/**
 * @notice Edge: Private upgrade function
 */
contract EdgePrivateUpgrade {
    address public owner;
    address private implementation;

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    // SAFE: Private visibility (not externally callable) (TN)
    function _upgradeImpl(address newImpl) private {
        implementation = newImpl;
    }

    // SAFE: Public wrapper with access control (TN)
    function performUpgrade(address newImpl) external onlyOwner {
        _upgradeImpl(newImpl);
    }
}

/**
 * @notice Edge: Fallback/receive cannot be upgrade functions
 */
contract EdgeFallbackReceive {
    address public implementation;

    // SAFE: Fallback cannot be used for upgrades (TN)
    fallback() external payable {
        // Delegatecall to implementation
    }

    // SAFE: Receive cannot be used for upgrades (TN)
    receive() external payable {
        // Handle ETH
    }
}

/**
 * @notice Edge: Upgrade disabled (implementation is immutable)
 */
contract EdgeImmutableImpl {
    address public immutable implementation;

    constructor(address _implementation) {
        implementation = _implementation;
    }

    // SAFE: Cannot upgrade immutable implementation (TN)
    // Note: This would fail to compile if function exists
}

/**
 * @notice Edge: Upgrade with complex multi-step authorization
 */
contract EdgeComplexAuthorization {
    address public owner;
    address public pendingOwner;
    address public implementation;
    mapping(address => bool) public approvers;
    mapping(address => uint256) public approvalCounts;

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier requiresApproval() {
        require(approvalCounts[msg.sender] >= 3, "Insufficient approvals");
        _;
    }

    // SAFE: Complex authorization (TN)
    function upgradeTo(address newImpl) external onlyOwner requiresApproval {
        implementation = newImpl;
        approvalCounts[msg.sender] = 0;
    }
}

// =============================================================================
// VARIATIONS: Different Naming and Proxy Types
// =============================================================================

/**
 * @notice Variation: Governor instead of owner
 */
contract VariationGovernorNaming {
    address public governor;
    address public implementation;

    // VULNERABLE: No access control (TP)
    function upgradeTo(address newImpl) external {
        implementation = newImpl;
    }
}

/**
 * @notice Variation: Safe governor naming
 */
contract VariationSafeGovernor {
    address public governor;
    address public implementation;

    modifier onlyGovernor() {
        require(msg.sender == governor, "Only governor");
        _;
    }

    // SAFE: Protected by governor (TN)
    function upgradeTo(address newImpl) external onlyGovernor {
        implementation = newImpl;
    }
}

/**
 * @notice Variation: Authority pattern
 */
contract VariationAuthorityPattern {
    address public authority;
    address public implementation;

    // VULNERABLE: No access control (TP)
    function setImplementation(address newImpl) external {
        implementation = newImpl;
    }
}

/**
 * @notice Variation: Safe authority pattern
 */
contract VariationSafeAuthority {
    address public authority;
    address public implementation;

    modifier onlyAuthority() {
        require(msg.sender == authority, "Only authority");
        _;
    }

    // SAFE: Protected by authority (TN)
    function setImplementation(address newImpl) external onlyAuthority {
        implementation = newImpl;
    }
}

/**
 * @notice Variation: Registry pattern
 */
contract VariationRegistryPattern {
    mapping(string => address) public implementations;

    // VULNERABLE: Anyone can register implementation (TP)
    function registerImplementation(string memory name, address impl) external {
        implementations[name] = impl;
    }

    // VULNERABLE: Anyone can update implementation (TP)
    function updateImplementation(string memory name, address newImpl) external {
        implementations[name] = newImpl;
    }
}

/**
 * @notice Variation: Safe registry with controller
 */
contract VariationSafeRegistry {
    address public controller;
    mapping(string => address) public implementations;

    modifier onlyController() {
        require(msg.sender == controller, "Only controller");
        _;
    }

    // SAFE: Protected registration (TN)
    function registerImplementation(string memory name, address impl) external onlyController {
        implementations[name] = impl;
    }

    // SAFE: Protected update (TN)
    function updateImplementation(string memory name, address newImpl) external onlyController {
        implementations[name] = newImpl;
    }
}

/**
 * @notice Variation: Manager pattern
 */
contract VariationManagerPattern {
    address public manager;
    address public implementation;

    // VULNERABLE: No protection (TP)
    function upgradeImplementation(address newImpl) external {
        implementation = newImpl;
    }
}

/**
 * @notice Variation: Safe manager pattern
 */
contract VariationSafeManager {
    address public manager;
    address public implementation;

    modifier onlyManager() {
        require(msg.sender == manager, "Only manager");
        _;
    }

    // SAFE: Protected by manager (TN)
    function upgradeImplementation(address newImpl) external onlyManager {
        implementation = newImpl;
    }
}

/**
 * @notice Variation: EIP-1967 standard slots
 */
contract VariationEIP1967 {
    // Standard EIP-1967 implementation slot
    bytes32 private constant IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    function _getImplementation() private view returns (address impl) {
        bytes32 slot = IMPLEMENTATION_SLOT;
        assembly {
            impl := sload(slot)
        }
    }

    function _setImplementation(address newImpl) private {
        bytes32 slot = IMPLEMENTATION_SLOT;
        assembly {
            sstore(slot, newImpl)
        }
    }

    // VULNERABLE: Anyone can upgrade via EIP-1967 slot (TP)
    function upgradeTo(address newImplementation) external {
        _setImplementation(newImplementation);
    }
}

/**
 * @notice Variation: Safe EIP-1967 with access control
 */
contract VariationSafeEIP1967 {
    address public admin;
    bytes32 private constant IMPLEMENTATION_SLOT = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }

    function _setImplementation(address newImpl) private {
        bytes32 slot = IMPLEMENTATION_SLOT;
        assembly {
            sstore(slot, newImpl)
        }
    }

    // SAFE: Protected upgrade (TN)
    function upgradeTo(address newImplementation) external onlyAdmin {
        _setImplementation(newImplementation);
    }
}

/**
 * @notice Variation: Beacon pattern
 */
contract VariationBeaconController {
    address public beacon;

    // VULNERABLE: Anyone can change beacon (TP)
    function changeBeacon(address newBeacon) external {
        beacon = newBeacon;
    }

    // VULNERABLE: Anyone can update beacon (TP)
    function updateBeacon(address newBeacon) external {
        beacon = newBeacon;
    }
}

/**
 * @notice Variation: Safe beacon pattern
 */
contract VariationSafeBeacon {
    address public owner;
    address public beacon;

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    // SAFE: Protected beacon change (TN)
    function changeBeacon(address newBeacon) external onlyOwner {
        beacon = newBeacon;
    }
}

/**
 * @notice Variation: Proxy admin pattern
 */
contract VariationProxyAdmin {
    address public proxyAdmin;
    address public implementation;

    // VULNERABLE: No protection (TP)
    function upgradeProxy(address proxy, address newImpl) external {
        // Would upgrade proxy contract
        implementation = newImpl;
    }
}

/**
 * @notice Variation: Safe proxy admin
 */
contract VariationSafeProxyAdmin {
    address public proxyAdmin;
    address public implementation;

    modifier onlyProxyAdmin() {
        require(msg.sender == proxyAdmin, "Only proxy admin");
        _;
    }

    // SAFE: Protected proxy upgrade (TN)
    function upgradeProxy(address proxy, address newImpl) external onlyProxyAdmin {
        implementation = newImpl;
    }
}

/**
 * @notice Non-upgradeable contract (should NOT flag)
 */
contract NonUpgradeableContract {
    address public someAddress;

    // SAFE: Not an upgradeable contract (TN)
    function setSomeAddress(address addr) external {
        someAddress = addr;
    }
}
