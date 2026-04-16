// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title LowLevelCallTest
 * @notice Comprehensive test scenarios for ext-003: Unprotected Low-Level Call pattern
 * @dev Tests detection of public/external functions using low-level call() without access control
 *
 * Pattern Detection Target: ext-003
 * - Uses: uses_call = true
 * - Severity signals: has_call_with_value OR call_target_user_controlled
 * - Excludes: has_access_gate OR has_access_control OR call_target_validated
 */

// =============================================================================
// TRUE POSITIVES: Unprotected low-level calls (VULNERABLE)
// =============================================================================

contract VulnerableCallPatterns {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // TP1: Standard unprotected call with value (HIGH RISK - fund drainage)
    function forwardCall(address target, bytes memory data) external payable {
        (bool success,) = target.call{value: msg.value}(data);
        require(success, "Call failed");
    }

    // TP2: Unprotected call with user-controlled target (HIGH RISK - arbitrary interaction)
    function executeCall(address destination, bytes calldata payload) external {
        (bool success,) = destination.call(payload);
        require(success, "Execution failed");
    }

    // TP3: Unprotected staticcall (still vulnerable to gas griefing/DoS)
    function queryExternal(address target, bytes memory data) external view returns (bytes memory) {
        (bool success, bytes memory result) = target.staticcall(data);
        require(success, "Static call failed");
        return result;
    }

    // TP4: Variation - different naming (relay)
    function relayTransaction(address to, bytes calldata callData) external payable {
        (bool ok,) = to.call{value: msg.value}(callData);
        require(ok);
    }

    // TP5: Variation - different naming (proxy)
    function proxyCall(address implementation, bytes memory input) external returns (bytes memory) {
        (bool success, bytes memory output) = implementation.call(input);
        require(success);
        return output;
    }

    // TP6: Variation - different naming (execute)
    function execute(address target, bytes memory encodedCall) external payable {
        (bool result,) = target.call{value: msg.value}(encodedCall);
        require(result, "Execute failed");
    }

    // TP7: Call with user-controlled value (fund drainage risk)
    function sendWithCall(address recipient, uint256 amount) external {
        (bool sent,) = recipient.call{value: amount}("");
        require(sent, "Send failed");
    }

    // TP8: Multiple calls in sequence (all unprotected)
    function batchCall(address[] calldata targets, bytes[] calldata data) external {
        for (uint256 i = 0; i < targets.length; i++) {
            (bool success,) = targets[i].call(data[i]);
            require(success);
        }
    }

    // TP9: Unprotected call without checking return value (even worse)
    function unsafeCall(address target, bytes memory data) external {
        target.call(data);  // No success check - additional risk
    }

    // TP10: Call with hardcoded gas but still unprotected
    function gasLimitedCall(address target, bytes memory data) external {
        target.call{gas: 100000}(data);
    }
}

// =============================================================================
// TRUE NEGATIVES: Protected/Safe low-level calls (SAFE)
// =============================================================================

contract SafeCallPatterns {
    address public owner;
    mapping(address => bool) public trustedTargets;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    // TN1: Protected with onlyOwner modifier (SAFE)
    function forwardCallProtected(address target, bytes memory data)
        external
        payable
        onlyOwner
    {
        (bool success,) = target.call{value: msg.value}(data);
        require(success, "Call failed");
    }

    // TN2: Protected with inline require check (SAFE)
    function executeCallWithCheck(address destination, bytes calldata payload) external {
        require(msg.sender == owner, "Unauthorized");
        (bool success,) = destination.call(payload);
        require(success, "Execution failed");
    }

    // TN3: Target is validated against whitelist (SAFE)
    function callTrusted(address target, bytes memory data) external {
        require(trustedTargets[target], "Target not trusted");
        (bool success,) = target.call(data);
        require(success);
    }

    // TN4: Internal function (not externally callable) (SAFE)
    function _internalCall(address target, bytes memory data) internal {
        (bool success,) = target.call(data);
        require(success);
    }

    // TN5: Private function (SAFE)
    function _privateCall(address target, bytes memory data) private {
        target.call(data);
    }

    // TN6: Target is hardcoded/not user-controlled (SAFE for this test)
    address constant TRUSTED_CONTRACT = address(0x1234567890123456789012345678901234567890);
    function callHardcodedTarget(bytes memory data) external {
        (bool success,) = TRUSTED_CONTRACT.call(data);
        require(success);
    }

    // TN7: Initializer function (SAFE - simulates constructor behavior)
    function initialize(address target, bytes memory initData) external {
        require(owner == address(0), "Already initialized");
        (bool success,) = target.call(initData);
        require(success);
        owner = msg.sender;
    }

    // TN8: No low-level call used (uses transfer instead) (SAFE for this pattern)
    function sendETH(address payable recipient, uint256 amount) external onlyOwner {
        recipient.transfer(amount);
    }
}

// =============================================================================
// EDGE CASES: Boundary conditions and special scenarios
// =============================================================================

contract EdgeCases {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // EDGE1: Call with value but requires zero value (false positive acceptable)
    function callRequiresZeroValue(address target, bytes memory data) external payable {
        require(msg.value == 0, "No value allowed");
        (bool success,) = target.call(data);
        require(success);
    }

    // EDGE2: Call to msg.sender (caller controls target but calls themselves)
    function callbackToSender(bytes memory data) external {
        (bool success,) = msg.sender.call(data);
        require(success);
    }

    // EDGE3: Call with custom access control (role-based)
    mapping(address => bool) public authorized;

    function executeAuthorized(address target, bytes memory data) external {
        require(authorized[msg.sender], "Not authorized");
        (bool success,) = target.call(data);
        require(success);
    }

    // EDGE4: Call return value checked but not used (still checks success)
    function callWithUnusedReturn(address target, bytes memory data) external {
        (bool success, bytes memory returnData) = target.call(data);
        require(success);
        // returnData unused but success checked
    }

    // EDGE5: Multiple access control checks (OR logic)
    function callMultiAuth(address target, bytes memory data) external {
        require(msg.sender == owner || authorized[msg.sender], "Unauthorized");
        (bool success,) = target.call(data);
        require(success);
    }

    // EDGE6: Time-based access control
    uint256 public unlockTime;

    function timelockCall(address target, bytes memory data) external {
        require(block.timestamp >= unlockTime, "Timelocked");
        (bool success,) = target.call(data);
        require(success);
    }
}

// =============================================================================
// VARIATIONS: Different implementations/naming conventions
// =============================================================================

contract VariationNamingConventions {
    address public controller;
    address public admin;
    address public governance;

    // VAR1: Controller naming instead of owner (TP - still vulnerable)
    function forwardCall(address target, bytes memory data) external payable {
        (bool success,) = target.call{value: msg.value}(data);
        require(success);
    }

    // VAR2: Protected with controller check (TN - safe)
    function forwardCallControllerProtected(address target, bytes memory data) external payable {
        require(msg.sender == controller, "Not controller");
        (bool success,) = target.call{value: msg.value}(data);
        require(success);
    }

    // VAR3: Admin naming with protection (TN - safe)
    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    function executeAsAdmin(address target, bytes memory data) external onlyAdmin {
        target.call(data);
    }

    // VAR4: Governance naming with protection (TN - safe)
    function governanceCall(address target, bytes memory data) external {
        require(msg.sender == governance, "Not governance");
        (bool ok,) = target.call(data);
        require(ok);
    }
}

contract VariationCallTypes {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }

    // VAR5: Unprotected call without data (TP - value transfer vulnerability)
    function sendValue(address payable recipient) external payable {
        (bool sent,) = recipient.call{value: msg.value}("");
        require(sent);
    }

    // VAR6: Unprotected staticcall (TP - gas griefing/DoS)
    function staticQuery(address target, bytes4 selector) external view returns (uint256) {
        (bool success, bytes memory data) = target.staticcall(abi.encodeWithSelector(selector));
        require(success);
        return abi.decode(data, (uint256));
    }

    // VAR7: Protected staticcall (TN - safe)
    function staticQueryProtected(address target, bytes4 selector)
        external
        view
        onlyOwner
        returns (uint256)
    {
        (bool success, bytes memory data) = target.staticcall(abi.encodeWithSelector(selector));
        require(success);
        return abi.decode(data, (uint256));
    }

    // VAR8: Assembly-level call (TP - should still be detected)
    function assemblyCall(address target, bytes memory data) external payable {
        assembly {
            let success := call(gas(), target, callvalue(), add(data, 0x20), mload(data), 0, 0)
            if iszero(success) { revert(0, 0) }
        }
    }

    // VAR9: Assembly-level call with access control (TN - safe)
    function assemblyCallProtected(address target, bytes memory data) external payable onlyOwner {
        assembly {
            let success := call(gas(), target, callvalue(), add(data, 0x20), mload(data), 0, 0)
            if iszero(success) { revert(0, 0) }
        }
    }
}

// =============================================================================
// REAL-WORLD PATTERNS: Common DeFi/wallet patterns
// =============================================================================

contract GnosisSafeStyle {
    address public owner;

    // TP: Gnosis Safe-style execution without proper signature validation
    function execTransaction(
        address to,
        uint256 value,
        bytes memory data,
        uint8 operation
    ) external payable {
        if (operation == 0) {
            (bool success,) = to.call{value: value}(data);
            require(success, "Transaction failed");
        }
    }

    // TN: Properly protected Gnosis-style execution
    function execTransactionProtected(
        address to,
        uint256 value,
        bytes memory data,
        bytes memory signatures
    ) external payable {
        require(checkSignatures(signatures), "Invalid signatures");
        (bool success,) = to.call{value: value}(data);
        require(success);
    }

    function checkSignatures(bytes memory) internal view returns (bool) {
        return msg.sender == owner;
    }
}

contract MultiCallPattern {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // TP: Unprotected multicall (vulnerable)
    function multicall(bytes[] calldata data) external returns (bytes[] memory results) {
        results = new bytes[](data.length);
        for (uint256 i = 0; i < data.length; i++) {
            (bool success, bytes memory result) = address(this).call(data[i]);
            require(success);
            results[i] = result;
        }
    }

    // TN: Protected multicall (safe)
    function multicallProtected(bytes[] calldata data)
        external
        returns (bytes[] memory results)
    {
        require(msg.sender == owner, "Not owner");
        results = new bytes[](data.length);
        for (uint256 i = 0; i < data.length; i++) {
            (bool success, bytes memory result) = address(this).call(data[i]);
            require(success);
            results[i] = result;
        }
    }
}

contract ProxyPattern {
    address public implementation;
    address public admin;

    receive() external payable {}

    // TP: Unprotected fallback with call (very dangerous)
    fallback() external payable {
        (bool success,) = implementation.call(msg.data);
        require(success);
    }

    // Note: Fallback protection is tricky - builder may not detect modifier on fallback
}

// =============================================================================
// ATTACK SCENARIO TESTS: Specific exploit patterns
// =============================================================================

contract AttackScenarios {
    mapping(address => uint256) public balances;

    // TP: Fund drainage via unprotected call with value
    function withdraw(address payable recipient, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        (bool sent,) = recipient.call{value: amount}("");
        require(sent, "Transfer failed");
    }

    // TP: Arbitrary external interaction enabling reentrancy
    function processCallback(address callback, bytes memory data) external {
        (bool success,) = callback.call(data);
        require(success);
    }

    // TP: Gas griefing via expensive external call
    function executeExpensive(address target, bytes memory data) external {
        // No gas limit - attacker can provide gas-expensive contract
        (bool success,) = target.call(data);
        require(success);
    }

    // TP: DoS via always-reverting call
    function criticalOperation(address validator, bytes memory validationData) external {
        (bool valid,) = validator.call(validationData);
        require(valid, "Validation failed");  // Attacker provides always-reverting contract
        // Critical protocol logic would go here
    }
}

// =============================================================================
// FALSE POSITIVE PREVENTION: Patterns that should NOT be flagged
// =============================================================================

contract FalsePositivePrevention {
    address public owner;
    mapping(address => bool) public whitelist;

    constructor() {
        owner = msg.sender;
    }

    // TN: Has access control modifier
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function protectedCall(address target, bytes memory data) external onlyOwner {
        (bool success,) = target.call(data);
        require(success);
    }

    // TN: Has inline access control
    function inlineProtectedCall(address target, bytes memory data) external {
        require(msg.sender == owner, "Unauthorized");
        (bool success,) = target.call(data);
        require(success);
    }

    // TN: Target is validated/whitelisted
    function whitelistedCall(address target, bytes memory data) external {
        require(whitelist[target], "Target not whitelisted");
        (bool success,) = target.call(data);
        require(success);
    }

    // TN: Internal visibility
    function _internalCall(address target, bytes memory data) internal {
        target.call(data);
    }

    // TN: Private visibility
    function _privateCall(address target, bytes memory data) private {
        target.call(data);
    }
}
