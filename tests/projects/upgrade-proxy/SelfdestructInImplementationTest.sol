// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title SelfdestructInImplementationTest
 * @notice Test contract for upgrade-010: Selfdestruct in Proxy Implementation pattern
 *
 * This pattern detects selfdestruct in implementation contracts, libraries, and upgradeable contracts.
 * The Parity Multisig Library hack ($300M frozen) was caused by selfdestruct in a library used via delegatecall.
 *
 * Test Coverage:
 * - TRUE POSITIVES: Implementation contracts WITH selfdestruct (detected)
 * - TRUE NEGATIVES: Non-upgradeable contracts with selfdestruct OR implementations without selfdestruct
 * - EDGE CASES: Access-controlled selfdestruct, conditional selfdestruct
 * - VARIATIONS: Different proxy types (UUPS, Transparent, Beacon), library patterns
 *
 * CRITICAL: Even with access control, selfdestruct in implementations is ALWAYS critical.
 */

// =============================================================================
// TRUE POSITIVES: Implementations WITH selfdestruct (SHOULD BE FLAGGED)
// =============================================================================

/**
 * @notice TP: Classic vulnerable library - Parity-style
 * VULNERABLE: Library with selfdestruct used via delegatecall
 * Real-world: Parity Multisig Library (Nov 2017, $300M frozen)
 */
library VulnerableWalletLibrary {
    // CRITICAL: Selfdestruct in library destroys ALL proxies
    function kill(address owner) public {
        require(msg.sender == owner, "not owner");
        selfdestruct(payable(owner));  // ❌ CRITICAL - Parity hack pattern
    }
}

/**
 * @notice TP: UUPS implementation with "emergency" selfdestruct
 * VULNERABLE: Even with access control, this is critical
 */
contract VulnerableUUPSImplementation {
    address public owner;
    uint256 public version;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    // CRITICAL: selfdestruct in implementation = catastrophic
    function emergencyShutdown() external onlyOwner {
        selfdestruct(payable(owner));  // ❌ CRITICAL - destroys all proxies
    }

    function _authorizeUpgrade(address) internal view onlyOwner {}
}

/**
 * @notice TP: Transparent proxy implementation with selfdestruct
 */
contract VulnerableTransparentImplementation {
    address public admin;
    mapping(address => uint256) public balances;

    // Even with admin-only access, this is CRITICAL
    function destroy() external {
        require(msg.sender == admin, "not admin");
        selfdestruct(payable(admin));  // ❌ CRITICAL
    }
}

/**
 * @notice TP: Beacon implementation with selfdestruct
 */
contract VulnerableBeaconImplementation {
    address public controller;

    // CRITICAL: selfdestruct in beacon implementation
    function terminate() external {
        require(msg.sender == controller, "not controller");
        selfdestruct(payable(controller));  // ❌ CRITICAL
    }
}

/**
 * @notice TP: Logic contract with selfdestruct
 * Tests "Logic" naming pattern instead of "Implementation"
 */
contract VulnerableLogicContract {
    address public owner;
    uint256 public fee;

    function destroyContract() external {
        require(msg.sender == owner);
        selfdestruct(payable(owner));  // ❌ CRITICAL
    }
}

/**
 * @notice TP: Implementation with NO access control on selfdestruct
 * ULTRA-CRITICAL: Anyone can destroy this
 */
contract VulnerableUnprotectedSelfdestruct {
    mapping(address => uint256) public balances;

    // ULTRA-CRITICAL: Unprotected selfdestruct in implementation
    function destroy() external {
        selfdestruct(payable(msg.sender));  // ❌ ULTRA-CRITICAL - anyone can call
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice TP: Library with complex logic including selfdestruct
 */
library VulnerableComplexLibrary {
    struct State {
        address owner;
        bool initialized;
    }

    function initialize(State storage state, address _owner) external {
        require(!state.initialized, "already initialized");
        state.owner = _owner;
        state.initialized = true;
    }

    // CRITICAL: Selfdestruct in library
    function destroy(State storage state) external {
        require(msg.sender == state.owner, "not owner");
        selfdestruct(payable(state.owner));  // ❌ CRITICAL
    }
}

/**
 * @notice TP: Implementation with conditional selfdestruct
 * CRITICAL: Even conditional selfdestruct is dangerous
 */
contract VulnerableConditionalSelfdestruct {
    address public owner;
    bool public deprecated;

    function deprecate() external {
        require(msg.sender == owner);
        deprecated = true;
    }

    // CRITICAL: Conditional selfdestruct still critical
    function cleanup() external {
        require(msg.sender == owner);
        if (deprecated) {
            selfdestruct(payable(owner));  // ❌ CRITICAL
        }
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice TP: Minimal proxy implementation with selfdestruct
 */
contract VulnerableMinimalProxyImplementation {
    address public implementation;

    function setImplementation(address _impl) external {
        implementation = _impl;
    }

    // CRITICAL: Selfdestruct in delegatecall context
    function destroy() external {
        selfdestruct(payable(msg.sender));  // ❌ CRITICAL
    }
}

/**
 * @notice TP: Diamond facet with selfdestruct
 */
contract VulnerableDiamondFacet {
    bytes32 constant DIAMOND_STORAGE_POSITION = keccak256("diamond.storage");

    struct DiamondStorage {
        address owner;
    }

    function diamondStorage() internal pure returns (DiamondStorage storage ds) {
        bytes32 position = DIAMOND_STORAGE_POSITION;
        assembly {
            ds.slot := position
        }
    }

    // CRITICAL: Selfdestruct in diamond facet
    function destroyFacet() external {
        DiamondStorage storage ds = diamondStorage();
        require(msg.sender == ds.owner);
        selfdestruct(payable(ds.owner));  // ❌ CRITICAL
    }
}

// =============================================================================
// TRUE NEGATIVES: Safe patterns (should NOT be flagged)
// =============================================================================

/**
 * @notice TN: Regular non-upgradeable contract with selfdestruct
 * SAFE: Not used in proxy pattern, selfdestruct is acceptable
 */
contract RegularContractWithSelfdestruct {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // SAFE: Not an implementation contract
    function destroy() external {
        require(msg.sender == owner);
        selfdestruct(payable(owner));
    }
}

/**
 * @notice TN: Implementation without selfdestruct (SAFE)
 */
contract SafeImplementation {
    address public owner;
    mapping(address => uint256) public balances;

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }

    // SAFE: Uses pause pattern instead of selfdestruct
    bool public paused;

    function emergencyPause() external onlyOwner {
        paused = true;  // ✓ SAFE - pause instead of destroy
    }

    function upgradeToAndCall(address, bytes memory) external onlyOwner {}
}

/**
 * @notice TN: UUPS implementation with proper deprecation pattern
 */
contract SafeUUPSImplementation {
    address public owner;
    enum State { Active, Deprecated }
    State public state;

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }

    // SAFE: State-based deprecation
    function deprecate() external onlyOwner {
        state = State.Deprecated;  // ✓ SAFE - flag instead of destroy
    }

    function _authorizeUpgrade(address) internal view onlyOwner {}
}

/**
 * @notice TN: Library without selfdestruct (SAFE)
 */
library SafeUtilityLibrary {
    function add(uint256 a, uint256 b) external pure returns (uint256) {
        return a + b;
    }

    function sub(uint256 a, uint256 b) external pure returns (uint256) {
        return a - b;
    }
}

/**
 * @notice TN: Implementation with circuit breaker pattern (SAFE)
 */
contract SafeCircuitBreakerImplementation {
    address public owner;
    bool public paused;
    uint256 public pauseStartTime;
    uint256 public constant MAX_PAUSE_DURATION = 30 days;

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }

    // SAFE: Circuit breaker instead of selfdestruct
    function emergencyPause() external onlyOwner {
        paused = true;
        pauseStartTime = block.timestamp;
    }

    function unpause() external onlyOwner {
        require(block.timestamp < pauseStartTime + MAX_PAUSE_DURATION);
        paused = false;
    }

    function upgradeToAndCall(address, bytes memory) external onlyOwner {}
}

/**
 * @notice TN: Test contract (should be excluded by pattern)
 */
contract TestContractWithSelfdestruct {
    function testDestroy() external {
        selfdestruct(payable(msg.sender));
    }
}

/**
 * @notice TN: Mock contract (should be excluded by pattern)
 */
contract MockImplementationWithSelfdestruct {
    function mockDestroy() external {
        selfdestruct(payable(msg.sender));
    }
}

// =============================================================================
// EDGE CASES: Boundary conditions
// =============================================================================

/**
 * @notice Edge: Selfdestruct in fallback function (CRITICAL)
 * CRITICAL: Malicious upgrade could use this pattern
 */
contract EdgeSelfdestructInFallback {
    address public owner;

    fallback() external {
        if (msg.sender == owner) {
            selfdestruct(payable(owner));  // ❌ CRITICAL
        }
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Edge: Selfdestruct in receive function (CRITICAL)
 */
contract EdgeSelfdestructInReceive {
    address public owner;

    receive() external payable {
        if (msg.sender == owner) {
            selfdestruct(payable(owner));  // ❌ CRITICAL
        }
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Edge: Inherited selfdestruct (CRITICAL)
 * Base contract has selfdestruct, child is implementation
 */
contract BaseWithSelfdestruct {
    address public owner;

    function destroy() public virtual {
        require(msg.sender == owner);
        selfdestruct(payable(owner));  // ❌ CRITICAL
    }
}

contract EdgeInheritedSelfdestruct is BaseWithSelfdestruct {
    uint256 public version;

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Edge: Multiple selfdestruct calls
 */
contract EdgeMultipleSelfdestruct {
    address public owner;
    address public admin;

    function destroyByOwner() external {
        require(msg.sender == owner);
        selfdestruct(payable(owner));  // ❌ CRITICAL
    }

    function destroyByAdmin() external {
        require(msg.sender == admin);
        selfdestruct(payable(admin));  // ❌ CRITICAL
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Edge: Selfdestruct in internal function called by public
 */
contract EdgeInternalSelfdestruct {
    address public owner;

    function destroy() external {
        require(msg.sender == owner);
        _destroy();
    }

    function _destroy() internal {
        selfdestruct(payable(owner));  // ❌ CRITICAL - still in implementation
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Edge: Selfdestruct after complex state changes
 */
contract EdgeComplexSelfdestruct {
    address public owner;
    mapping(address => uint256) public balances;

    function emergencyExit() external {
        require(msg.sender == owner);

        // Transfer all funds first
        uint256 balance = address(this).balance;
        payable(owner).transfer(balance);

        // Then selfdestruct
        selfdestruct(payable(owner));  // ❌ CRITICAL - even after transfers
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

// =============================================================================
// VARIATIONS: Different naming and proxy patterns
// =============================================================================

/**
 * @notice Variation: 'controller' instead of 'owner' naming
 */
contract VariationControllerNaming {
    address public controller;

    function terminate() external {
        require(msg.sender == controller);
        selfdestruct(payable(controller));  // ❌ CRITICAL
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Variation: 'governance' pattern
 */
contract VariationGovernancePattern {
    address public governance;

    function shutDown() external {
        require(msg.sender == governance);
        selfdestruct(payable(governance));  // ❌ CRITICAL
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Variation: 'authority' pattern
 */
contract VariationAuthorityPattern {
    address public authority;

    function destroyContract() external {
        require(msg.sender == authority);
        selfdestruct(payable(authority));  // ❌ CRITICAL
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Variation: Multi-sig protected selfdestruct (STILL CRITICAL)
 */
contract VariationMultiSigProtected {
    mapping(address => bool) public signers;
    uint256 public required = 2;
    mapping(bytes32 => uint256) public approvals;

    function destroy() external {
        bytes32 txHash = keccak256(abi.encodePacked("destroy"));
        require(signers[msg.sender], "not signer");
        approvals[txHash]++;

        if (approvals[txHash] >= required) {
            selfdestruct(payable(msg.sender));  // ❌ CRITICAL - even with multisig
        }
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Variation: Timelock protected selfdestruct (STILL CRITICAL)
 */
contract VariationTimelockProtected {
    address public owner;
    uint256 public destructionTime;
    uint256 public constant TIMELOCK = 7 days;

    function scheduleDestruction() external {
        require(msg.sender == owner);
        destructionTime = block.timestamp + TIMELOCK;
    }

    function executeDestruction() external {
        require(msg.sender == owner);
        require(block.timestamp >= destructionTime);
        require(destructionTime != 0);
        selfdestruct(payable(owner));  // ❌ CRITICAL - even with timelock
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Variation: DAO-controlled selfdestruct (STILL CRITICAL)
 */
contract VariationDAOControlled {
    address public dao;

    function destroy(bytes memory daoSignature) external {
        require(msg.sender == dao);
        // ... signature verification logic ...
        selfdestruct(payable(dao));  // ❌ CRITICAL - even with DAO control
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

/**
 * @notice Variation: Implementation suffix naming
 */
contract VaultImplementation {
    address public owner;
    mapping(address => uint256) public deposits;

    function emergencyDestroy() external {
        require(msg.sender == owner);
        selfdestruct(payable(owner));  // ❌ CRITICAL
    }
}

/**
 * @notice Variation: Logic suffix naming
 */
contract TokenLogic {
    address public owner;
    mapping(address => uint256) public balances;

    function terminate() external {
        require(msg.sender == owner);
        selfdestruct(payable(owner));  // ❌ CRITICAL
    }
}

/**
 * @notice Variation: Impl abbreviation
 */
contract StakingImpl {
    address public owner;

    function destroy() external {
        require(msg.sender == owner);
        selfdestruct(payable(owner));  // ❌ CRITICAL
    }

    function upgradeToAndCall(address, bytes memory) external {}
}

// =============================================================================
// FALSE POSITIVE PREVENTION
// =============================================================================

/**
 * @notice FP Prevention: Standalone contract (not upgradeable)
 * Should NOT be flagged - has constructor, no proxy pattern
 */
contract StandaloneContract {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function destroy() external {
        require(msg.sender == owner);
        selfdestruct(payable(owner));
    }
}

/**
 * @notice FP Prevention: Interface (cannot have selfdestruct)
 */
interface IProxy {
    function upgradeTo(address newImplementation) external;
}
