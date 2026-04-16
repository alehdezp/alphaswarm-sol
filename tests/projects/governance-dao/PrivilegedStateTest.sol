// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title PrivilegedStateTest
 * @notice Comprehensive test contract for auth-003-unprotected-privileged-write
 *
 * Tests detection of unprotected writes to privileged state variables:
 * - Owner/admin addresses
 * - Role mappings
 * - Fee structures
 * - Treasury addresses
 * - Implementation addresses (upgradeable contracts)
 * - Pause states
 * - Oracle addresses
 * - Governance parameters
 *
 * Contains TRUE POSITIVES, TRUE NEGATIVES, EDGE CASES, and VARIATIONS
 */
contract PrivilegedStateTest {
    // === PRIVILEGED STATE VARIABLES ===

    // Ownership/Admin
    address public owner;
    address public admin;
    address public controller;
    address public governance;
    address public authority;

    // Role mappings
    mapping(address => bool) public isAdmin;
    mapping(bytes32 => mapping(address => bool)) public roles;
    mapping(address => uint256) public userRoles;

    // Fee structures
    uint256 public fee;
    uint256 public platformFee;
    address public feeRecipient;
    address public treasury;

    // Upgrade/Implementation
    address public implementation;
    address public logicContract;

    // Oracle
    address public oracle;
    address public priceOracle;

    // Pause state
    bool public paused;
    bool public emergencyStop;

    // Governance parameters
    uint256 public votingThreshold;
    uint256 public rewardRate;
    uint256 public minDelay;

    // Non-privileged state for testing
    mapping(address => uint256) public balances;
    uint256 public totalSupply;
    string public name;

    // Access control tracking
    bool private initialized;

    // === TRUE POSITIVES (10 cases) ===

    /// @dev TP1: Unprotected setOwner - classic vulnerability
    function setOwner(address newOwner) external {
        owner = newOwner;
    }

    /// @dev TP2: Unprotected setAdmin - admin takeover
    function setAdmin(address newAdmin) external {
        admin = newAdmin;
    }

    /// @dev TP3: Unprotected grantRole - role escalation
    function grantRole(bytes32 role, address account) external {
        roles[role][account] = true;
    }

    /// @dev TP4: Unprotected setFee - fee manipulation
    function setFee(uint256 newFee) external {
        fee = newFee;
    }

    /// @dev TP5: Unprotected setTreasury - fund redirection
    function setTreasury(address newTreasury) external {
        treasury = newTreasury;
    }

    /// @dev TP6: Unprotected upgradeImplementation - logic replacement
    function upgradeImplementation(address newImplementation) external {
        implementation = newImplementation;
    }

    /// @dev TP7: Unprotected updateGovernor - governance takeover
    function updateGovernor(address newGovernor) external {
        governance = newGovernor;
    }

    /// @dev TP8: Unprotected setRewardRate - parameter manipulation
    function setRewardRate(uint256 newRate) external {
        rewardRate = newRate;
    }

    /// @dev TP9: Unprotected setOracle - oracle manipulation attack
    function setOracle(address newOracle) external {
        oracle = newOracle;
    }

    /// @dev TP10: Unprotected pause function - DoS attack
    function pause() external {
        paused = true;
    }

    // === VARIATIONS: Different Naming (4 cases) ===

    /// @dev VAR1: updateOwner (variation of setOwner)
    function updateOwner(address newOwner) external {
        owner = newOwner;
    }

    /// @dev VAR2: changeAdmin (variation of setAdmin)
    function changeAdmin(address newAdmin) external {
        admin = newAdmin;
    }

    /// @dev VAR3: configureController (variation using 'controller' naming)
    function configureController(address newController) external {
        controller = newController;
    }

    /// @dev VAR4: modifyAuthority (variation using 'authority' naming)
    function modifyAuthority(address newAuthority) external {
        authority = newAuthority;
    }

    // === VARIATIONS: Multiple Writes (2 cases) ===

    /// @dev VAR5: Multiple privileged writes in one function
    function updateAdminAndFee(address newAdmin, uint256 newFee) external {
        admin = newAdmin;
        fee = newFee;
    }

    /// @dev VAR6: Complex multi-state write
    function updateGovernance(address newGov, uint256 newDelay, uint256 newThreshold) external {
        governance = newGov;
        minDelay = newDelay;
        votingThreshold = newThreshold;
    }

    // === TRUE NEGATIVES: With Access Control (8 cases) ===

    /// @dev TN1: setOwner WITH onlyOwner modifier (safe)
    function setOwnerProtected(address newOwner) external onlyOwner {
        owner = newOwner;
    }

    /// @dev TN2: setAdmin WITH custom require check (safe)
    function setAdminWithRequire(address newAdmin) external {
        require(msg.sender == owner, "Not owner");
        admin = newAdmin;
    }

    /// @dev TN3: grantRole WITH hasRole check (safe)
    function grantRoleProtected(bytes32 role, address account) external {
        require(roles[keccak256("ADMIN_ROLE")][msg.sender], "Not admin");
        roles[role][account] = true;
    }

    /// @dev TN4: setFee WITH if-revert pattern (safe)
    function setFeeWithIf(uint256 newFee) external {
        if (msg.sender != owner) revert("Unauthorized");
        fee = newFee;
    }

    /// @dev TN5: Internal function (safe - not externally callable)
    function _setOwner(address newOwner) internal {
        owner = newOwner;
    }

    /// @dev TN6: View function reading privileged state (safe - no writes)
    function getOwner() external view returns (address) {
        return owner;
    }

    /// @dev TN7: Function writing non-privileged state (safe - user balances)
    function updateBalance(address user, uint256 amount) external {
        balances[user] = amount;
    }

    /// @dev TN8: Private helper function (safe - not externally callable)
    function _updateFee(uint256 newFee) private {
        fee = newFee;
    }

    // === EDGE CASES (6 cases) ===

    /// @dev EDGE1: Constructor setting initial owner (safe - intentional setup)
    constructor() {
        owner = msg.sender;
        admin = msg.sender;
        initialized = true;
    }

    /// @dev EDGE2: Initializer function (safe - intentional setup pattern)
    function initialize(address initialOwner) external initializer {
        owner = initialOwner;
        admin = initialOwner;
    }

    /// @dev EDGE3: Two-step ownership transfer - propose (vulnerable step 1)
    address public pendingOwner;

    function transferOwnership(address newOwner) external {
        // VULNERABLE: No access check on propose step
        pendingOwner = newOwner;
    }

    /// @dev EDGE4: Two-step ownership transfer - accept (safe - self-authorization)
    function acceptOwnership() external {
        require(msg.sender == pendingOwner, "Not pending owner");
        owner = pendingOwner;
        pendingOwner = address(0);
    }

    /// @dev EDGE5: Privileged write in callback/hook (vulnerable in certain contexts)
    function onTransferReceived(address from, address to, uint256 amount) external {
        // Callback that writes privileged state - vulnerable
        admin = from;
    }

    /// @dev EDGE6: Emergency function with privileged write (vulnerable - needs access control)
    function emergencyUpdateTreasury(address newTreasury) external {
        // Emergency functions also need access control
        treasury = newTreasury;
        emergencyStop = true;
    }

    // === VARIATIONS: Different Access Control Styles (4 cases) ===

    /// @dev VAR7: Custom modifier pattern (safe)
    modifier onlyController() {
        require(msg.sender == controller, "Not controller");
        _;
    }

    function setFeeByController(uint256 newFee) external onlyController {
        fee = newFee;
    }

    /// @dev VAR8: Multi-condition check (safe)
    function setFeeWithMultiCheck(uint256 newFee) external {
        require(msg.sender == owner || msg.sender == admin, "Unauthorized");
        fee = newFee;
    }

    /// @dev VAR9: Role-based check (safe)
    function setFeeByAdmin(uint256 newFee) external {
        require(isAdmin[msg.sender], "Not admin");
        fee = newFee;
    }

    /// @dev VAR10: Time-delayed update (vulnerable - no access control on initiate)
    uint256 public pendingFee;
    uint256 public feeUpdateTime;

    function scheduleFeeUpdate(uint256 newFee) external {
        // VULNERABLE: No access control
        pendingFee = newFee;
        feeUpdateTime = block.timestamp + 1 days;
    }

    function executeFeeUpdate() external {
        require(block.timestamp >= feeUpdateTime, "Too early");
        fee = pendingFee;
    }

    // === EDGE CASES: Cross-Contract Patterns (2 cases) ===

    /// @dev EDGE7: Proxy admin function (vulnerable without access control)
    function upgradeTo(address newImplementation) external {
        implementation = newImplementation;
    }

    /// @dev EDGE8: Delegatecall upgrade (vulnerable - critical)
    function upgradeToAndCall(address newImplementation, bytes calldata data) external {
        implementation = newImplementation;
        (bool success, ) = newImplementation.delegatecall(data);
        require(success, "Delegatecall failed");
    }

    // === HELPER MODIFIERS ===

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier initializer() {
        require(!initialized, "Already initialized");
        _;
        initialized = true;
    }
}

/**
 * @title InheritanceTest
 * @notice Test detection across inheritance hierarchies
 */
contract InheritanceTest is PrivilegedStateTest {
    address public supervisor;

    /// @dev VARIATION: Privileged write in derived contract
    function setSupervisor(address newSupervisor) external {
        supervisor = newSupervisor;
    }

    /// @dev VARIATION: Protected via inherited modifier
    function setSupervisorProtected(address newSupervisor) external onlyOwner {
        supervisor = newSupervisor;
    }

    /// @dev VARIATION: Calling internal setter from base
    function setOwnerViaInternal(address newOwner) external {
        // This is vulnerable - public function calling internal setter without access control
        _setOwner(newOwner);
    }
}

/**
 * @title MultiSigPatterns
 * @notice Test multi-signature patterns
 */
contract MultiSigPatterns {
    address[] public signers;
    mapping(address => bool) public isSigner;
    uint256 public requiredSignatures;

    /// @dev VULNERABLE: No access control on adding signer
    function addSigner(address newSigner) external {
        isSigner[newSigner] = true;
        signers.push(newSigner);
    }

    /// @dev VULNERABLE: No access control on removing signer
    function removeSigner(address signer) external {
        isSigner[signer] = false;
    }

    /// @dev VULNERABLE: No access control on changing threshold
    function setThreshold(uint256 newThreshold) external {
        requiredSignatures = newThreshold;
    }

    /// @dev SAFE: Multi-sig protected (requires multiple signers)
    function addSignerProtected(address newSigner, bytes[] calldata signatures) external {
        require(signatures.length >= requiredSignatures, "Not enough signatures");
        // Verify signatures...
        isSigner[newSigner] = true;
        signers.push(newSigner);
    }
}

/**
 * @title RealWorldExploitPatterns
 * @notice Patterns from documented exploits
 */
contract RealWorldExploitPatterns {
    address public keeper;
    address[] public validators;
    mapping(address => bool) public isValidator;

    /// @dev Poly Network pattern: Unprotected changeKeepers
    function changeKeepers(address newKeeper) external {
        keeper = newKeeper;  // $611M exploit
    }

    /// @dev Ronin Bridge pattern: Unprotected validator modification
    function addValidator(address validator) external {
        isValidator[validator] = true;
        validators.push(validator);  // $625M exploit
    }

    /// @dev Rug pull pattern: Unprotected fee recipient change
    function setFeeRecipient(address recipient) external {
        // Common rug pull: Change fee recipient to attacker address
        // All fees now go to attacker
    }
}
