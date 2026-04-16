// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =============================================================================
// TEST CONTRACT FOR upgrade-008: Delegatecall to Untrusted Target
// =============================================================================
//
// This contract contains test cases for detecting delegatecall vulnerabilities
// where the target address comes from user input or untrusted sources.
//
// Pattern Properties Used:
// - uses_delegatecall: true
// - visibility: [public, external]
// - delegatecall_target_user_controlled: true
// - has_access_gate: false (for vulnerable)
// - validates_delegatecall_target: false (for vulnerable)
// - delegatecall_in_proxy_upgrade_context: false (for vulnerable)
//
// =============================================================================

// =============================================================================
// TRUE POSITIVES - Vulnerable Delegatecall Patterns
// =============================================================================

/**
 * @title VulnerableClassicDelegatecall
 * @notice TP: Classic vulnerable delegatecall with user-controlled target
 * @dev Allows arbitrary code execution - Parity Wallet style
 */
contract VulnerableClassicDelegatecall {
    address public owner;
    mapping(address => uint256) public balances;

    // TP: User provides target address directly
    function execute(address target, bytes memory data) external returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success, "Delegatecall failed");
        return result;
    }

    // TP: User-controlled target with different naming
    function proxy(address impl, bytes calldata callData) external payable returns (bytes memory) {
        (bool success, bytes memory returnData) = impl.delegatecall(callData);
        require(success);
        return returnData;
    }

    // TP: Attacker can overwrite storage via delegatecall
    function executeCall(address _target, bytes memory _data) external {
        (bool success,) = _target.delegatecall(_data);
        require(success);
    }
}

/**
 * @title VulnerableStorageBasedTarget
 * @notice TP: Delegatecall target comes from mutable storage
 * @dev User can change storage variable, then call execute
 */
contract VulnerableStorageBasedTarget {
    address public implementation;
    address public owner;

    // Anyone can set implementation
    function setImplementation(address _impl) external {
        implementation = _impl;
    }

    // TP: Delegates to user-controlled storage variable
    function execute(bytes memory data) external returns (bytes memory) {
        (bool success, bytes memory result) = implementation.delegatecall(data);
        require(success);
        return result;
    }
}

/**
 * @title VulnerableExternalCallResult
 * @notice TP: Delegatecall target from external call result
 * @dev Target address computed by untrusted external contract
 */
contract VulnerableExternalCallResult {
    address public registry;

    constructor(address _registry) {
        registry = _registry;
    }

    // TP: Target address from external call (untrusted)
    function executeFromRegistry(bytes memory data) external returns (bytes memory) {
        address target = IRegistry(registry).getImplementation();
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }
}

interface IRegistry {
    function getImplementation() external view returns (address);
}

/**
 * @title VulnerableComputedAddress
 * @notice TP: Delegatecall target computed from user input
 * @dev User controls seed that determines target address
 */
contract VulnerableComputedAddress {
    mapping(bytes32 => address) public implementations;

    function setImplementation(bytes32 key, address impl) external {
        implementations[key] = impl;
    }

    // TP: User provides key, controls which implementation is called
    function executeWithKey(bytes32 key, bytes memory data) external returns (bytes memory) {
        address target = implementations[key];
        require(target != address(0), "Implementation not found");
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }
}

/**
 * @title VulnerableAssemblyDelegatecall
 * @notice TP: Low-level assembly delegatecall with user target
 * @dev Assembly-based delegatecall is still vulnerable
 */
contract VulnerableAssemblyDelegatecall {
    // TP: Assembly delegatecall with user-controlled target
    function executeAssembly(address target, bytes memory data) external returns (bytes memory) {
        bytes memory result;
        assembly {
            let succeeded := delegatecall(gas(), target, add(data, 0x20), mload(data), 0, 0)
            let size := returndatasize()
            result := mload(0x40)
            mstore(result, size)
            returndatacopy(add(result, 0x20), 0, size)
            mstore(0x40, add(result, add(0x20, size)))
            if iszero(succeeded) {
                revert(0, 0)
            }
        }
        return result;
    }
}

// =============================================================================
// TRUE NEGATIVES - Safe Delegatecall Patterns
// =============================================================================

/**
 * @title SafeWithAccessControl
 * @notice TN: Delegatecall protected by onlyOwner modifier
 * @dev Only owner can specify target - reduces attack surface
 */
contract SafeWithAccessControl {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // TN: Access control protects delegatecall
    function execute(address target, bytes memory data) external onlyOwner returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }
}

/**
 * @title SafeWithWhitelist
 * @notice TN: Delegatecall target validated against whitelist
 * @dev Target must be approved before use
 */
contract SafeWithWhitelist {
    mapping(address => bool) public approvedTargets;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function addApprovedTarget(address target) external {
        require(msg.sender == owner);
        approvedTargets[target] = true;
    }

    // TN: Target is validated against whitelist
    function execute(address target, bytes memory data) external returns (bytes memory) {
        require(approvedTargets[target], "Target not approved");
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }
}

/**
 * @title SafeHardcodedTarget
 * @notice TN: Delegatecall to constant/immutable address
 * @dev Target cannot be changed by users
 */
contract SafeHardcodedTarget {
    // Immutable library address set at deployment
    address private immutable LIBRARY;

    constructor(address _library) {
        require(_library != address(0));
        LIBRARY = _library;
    }

    // TN: Target is immutable, not user-controlled
    function execute(bytes memory data) external returns (bytes memory) {
        (bool success, bytes memory result) = LIBRARY.delegatecall(data);
        require(success);
        return result;
    }
}

/**
 * @title SafeUUPSProxy
 * @notice TN: Proper UUPS upgrade pattern with authorization
 * @dev Standard proxy pattern with access control
 */
contract SafeUUPSProxy {
    address public implementation;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }

    // TN: Upgrade function with access control
    function upgradeTo(address newImplementation) external onlyOwner {
        require(newImplementation != address(0));
        implementation = newImplementation;
    }

    // TN: Delegatecall in proxy upgrade context with authorization
    function upgradeToAndCall(address newImplementation, bytes memory data) external payable onlyOwner {
        implementation = newImplementation;
        (bool success,) = newImplementation.delegatecall(data);
        require(success);
    }

    // Fallback delegates to implementation
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

/**
 * @title SafeWithManualValidation
 * @notice TN: Manual require check validates target address
 * @dev Uses require instead of modifier
 */
contract SafeWithManualValidation {
    address public trustedLibrary;
    address public owner;

    constructor(address _library) {
        trustedLibrary = _library;
        owner = msg.sender;
    }

    // TN: Manual validation of target address
    function execute(address target, bytes memory data) external returns (bytes memory) {
        require(target == trustedLibrary, "Untrusted target");
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }
}

// =============================================================================
// EDGE CASES
// =============================================================================

/**
 * @title EdgeInternalDelegatecall
 * @notice Edge: Internal function with delegatecall
 * @dev Not directly exploitable (internal visibility)
 */
contract EdgeInternalDelegatecall {
    address public owner;

    // Edge: Internal - cannot be called externally
    function _executeDelegatecall(address target, bytes memory data) internal returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }

    // Public wrapper WITH access control
    function execute(address target, bytes memory data) external returns (bytes memory) {
        require(msg.sender == owner);
        return _executeDelegatecall(target, data);
    }
}

/**
 * @title EdgePrivateDelegatecall
 * @notice Edge: Private function with delegatecall
 * @dev Not externally accessible
 */
contract EdgePrivateDelegatecall {
    // Edge: Private - cannot be called externally
    function _execute(address target, bytes memory data) private returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }
}

/**
 * @title EdgeStaticDelegatecall
 * @notice Edge: View function cannot use delegatecall
 * @dev Delegatecall is state-changing operation
 */
contract EdgeStaticDelegatecall {
    // Edge: View functions cannot use delegatecall (compilation error in real code)
    // This is for testing property detection
}

/**
 * @title EdgeMultipleChecks
 * @notice Edge: Multiple validation layers
 * @dev Defense-in-depth pattern
 */
contract EdgeMultipleChecks {
    address public owner;
    mapping(address => bool) public approved;
    address public defaultLibrary;

    constructor() {
        owner = msg.sender;
    }

    // Edge: Multiple protections (access control + whitelist + fallback)
    function execute(address target, bytes memory data) external returns (bytes memory) {
        require(msg.sender == owner, "Not owner");

        address actualTarget = target;
        if (!approved[target]) {
            actualTarget = defaultLibrary;
        }

        require(actualTarget != address(0), "Invalid target");
        (bool success, bytes memory result) = actualTarget.delegatecall(data);
        require(success);
        return result;
    }
}

// =============================================================================
// VARIATIONS - Different Naming Conventions
// =============================================================================

/**
 * @title VariationInvokeNaming
 * @notice TP: Different function naming (invoke instead of execute)
 * @dev Tests pattern works across naming variations
 */
contract VariationInvokeNaming {
    // TP: "invoke" naming instead of "execute"
    function invoke(address target, bytes memory data) external returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }

    // TP: "call" naming
    function call(address to, bytes memory data) external returns (bytes memory) {
        (bool success, bytes memory result) = to.delegatecall(data);
        require(success);
        return result;
    }
}

/**
 * @title VariationParameterNaming
 * @notice TP: Different parameter naming
 * @dev Tests pattern detects regardless of parameter names
 */
contract VariationParameterNaming {
    // TP: Parameter named "impl" instead of "target"
    function execute(address impl, bytes calldata callData) external returns (bytes memory) {
        (bool success, bytes memory returnData) = impl.delegatecall(callData);
        require(success);
        return returnData;
    }

    // TP: Parameter named "logic" instead of "target"
    function executeLogic(address logic, bytes memory payload) external returns (bytes memory) {
        (bool success, bytes memory result) = logic.delegatecall(payload);
        require(success);
        return result;
    }

    // TP: Parameter named "contract" instead of "target"
    function executeContract(address contractAddr, bytes memory input) external returns (bytes memory) {
        (bool success, bytes memory output) = contractAddr.delegatecall(input);
        require(success);
        return output;
    }
}

/**
 * @title VariationAdminNaming
 * @notice TN: Different access control naming (admin instead of owner)
 * @dev Tests pattern recognizes various access control patterns
 */
contract VariationAdminNaming {
    address public admin;

    constructor() {
        admin = msg.sender;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin);
        _;
    }

    // TN: Access control with "admin" naming
    function execute(address target, bytes memory data) external onlyAdmin returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }
}

/**
 * @title VariationControllerNaming
 * @notice TN: Controller-based access control
 * @dev Tests pattern recognizes controller pattern
 */
contract VariationControllerNaming {
    address public controller;

    constructor() {
        controller = msg.sender;
    }

    modifier onlyController() {
        require(msg.sender == controller);
        _;
    }

    // TN: Access control with "controller" naming
    function execute(address target, bytes memory data) external onlyController returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }
}

/**
 * @title VariationGovernanceNaming
 * @notice TN: Governance-based access control
 * @dev Tests pattern recognizes governance pattern
 */
contract VariationGovernanceNaming {
    address public governance;

    constructor() {
        governance = msg.sender;
    }

    modifier onlyGovernance() {
        require(msg.sender == governance);
        _;
    }

    // TN: Access control with "governance" naming
    function execute(address target, bytes memory data) external onlyGovernance returns (bytes memory) {
        (bool success, bytes memory result) = target.delegatecall(data);
        require(success);
        return result;
    }
}

// =============================================================================
// MALICIOUS CONTRACTS (for understanding attack scenarios)
// =============================================================================

/**
 * @title MaliciousStorageOverwrite
 * @notice Example attacker contract that overwrites storage slot 0
 * @dev This demonstrates the Parity Wallet attack
 */
contract MaliciousStorageOverwrite {
    address public owner;  // Storage slot 0 - matches victim's owner

    // When called via delegatecall, overwrites victim's owner
    function pwn() external {
        owner = msg.sender;
    }
}

/**
 * @title MaliciousSelfDestruct
 * @notice Example attacker contract with selfdestruct
 * @dev When called via delegatecall, destroys victim contract
 */
contract MaliciousSelfDestruct {
    function destroy(address payable recipient) external {
        selfdestruct(recipient);
    }
}

/**
 * @title MaliciousBalanceManipulation
 * @notice Example attacker contract that manipulates balances
 * @dev Demonstrates storage slot collision for balance manipulation
 */
contract MaliciousBalanceManipulation {
    // Storage slot 0: owner
    address public owner;
    // Storage slot 1: balances mapping (keccak256(address, 1) for specific balance)
    mapping(address => uint256) public balances;

    // When called via delegatecall, sets attacker's balance to max
    function inflate() external {
        balances[msg.sender] = type(uint256).max;
    }
}
