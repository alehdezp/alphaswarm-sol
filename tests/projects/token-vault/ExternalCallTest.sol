// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ExternalCallTest
 * @notice Test contract for ext-001: Unprotected External Call pattern
 *
 * Tests detection of public/external functions that make external calls
 * without proper access control or reentrancy protection.
 *
 * Pattern: ext-001-unprotected-external-call
 * Lens: ExternalInfluence, ValueMovement
 * Severity: HIGH
 */

interface ICallback {
    function onWithdraw(address user, uint256 amount) external;
    function beforeTransfer(address from, address to, uint256 amount) external;
    function afterDeposit(address user, uint256 amount) external;
}

interface IExternalContract {
    function process(bytes memory data) external returns (bool);
    function validate(address user) external view returns (bool);
}

// =============================================================================
// TRUE POSITIVES - Should be flagged by ext-001
// =============================================================================

contract UnprotectedExternalCalls {
    mapping(address => uint256) public balances;
    address public owner;

    // TP1: Public function with external call and state write
    function withdraw(uint256 amount, address callback) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // External call before state update - VULNERABLE
        ICallback(callback).onWithdraw(msg.sender, amount);

        // State write after external call
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    // TP2: External call in middle of state changes
    function withdrawWithCallback(uint256 amount, address callback) external {
        balances[msg.sender] -= amount;

        // External call between state changes - VULNERABLE
        ICallback(callback).onWithdraw(msg.sender, amount);

        payable(msg.sender).transfer(amount);
    }

    // TP3: Multiple external calls with state changes
    function processWithCallbacks(address callback1, address callback2, bytes memory data) external {
        balances[msg.sender] += 100;

        // Multiple external calls - VULNERABLE
        ICallback(callback1).afterDeposit(msg.sender, 100);
        IExternalContract(callback2).process(data);

        balances[msg.sender] -= 50;
    }

    // TP4: Low-level call without access control
    function executeCall(address target, bytes memory data) external {
        balances[msg.sender] += 1;

        // Low-level call - VULNERABLE
        (bool success,) = target.call(data);
        require(success, "Call failed");
    }

    // TP5: Delegatecall with state changes
    function delegateExecute(address target, bytes memory data) external {
        balances[msg.sender] = 100;

        // Delegatecall - VERY VULNERABLE
        (bool success,) = target.delegatecall(data);
        require(success, "Delegatecall failed");
    }

    // TP6: Interface call with state modification
    function processExternal(address processor, bytes memory data) public {
        // State write
        balances[msg.sender] += 10;

        // External interface call - VULNERABLE
        IExternalContract(processor).process(data);
    }

    // TP7: Different naming - removeFunds with callback
    function removeFunds(uint256 amount, address callbackContract) public {
        balances[msg.sender] -= amount;

        // Callback to user-controlled address - VULNERABLE
        ICallback(callbackContract).onWithdraw(msg.sender, amount);

        payable(msg.sender).transfer(amount);
    }

    // TP8: Update operation with external validation
    function updateBalance(address user, uint256 newBalance, address validator) external {
        // External call - VULNERABLE
        IExternalContract(validator).process(abi.encode(user, newBalance));

        // State write after external call
        balances[user] = newBalance;
    }

    // TP9: Batch operation with external calls
    function batchWithdraw(address[] memory users, uint256[] memory amounts, address callback) external {
        for (uint256 i = 0; i < users.length; i++) {
            balances[users[i]] -= amounts[i];

            // External call in loop - VULNERABLE
            ICallback(callback).onWithdraw(users[i], amounts[i]);
        }
    }

    // TP10: Transfer with before/after hooks
    function transferWithHooks(address to, uint256 amount, address hooks) public {
        // Before hook - external call
        ICallback(hooks).beforeTransfer(msg.sender, to, amount);

        // State changes
        balances[msg.sender] -= amount;
        balances[to] += amount;

        // After hook - external call - VULNERABLE
        ICallback(hooks).afterDeposit(to, amount);
    }
}

// =============================================================================
// TRUE NEGATIVES - Should NOT be flagged (safe patterns)
// =============================================================================

contract ProtectedExternalCalls {
    mapping(address => uint256) public balances;
    address public owner;
    bool private locked;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier nonReentrant() {
        require(!locked, "Reentrant call");
        locked = true;
        _;
        locked = false;
    }

    // TN1: Has access control (onlyOwner)
    function adminCallback(address target, bytes memory data) external onlyOwner {
        balances[msg.sender] += 1;

        // External call with access control - SAFE
        (bool success,) = target.call(data);
        require(success, "Call failed");
    }

    // TN2: Has reentrancy guard
    function withdrawProtected(uint256 amount, address callback) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Reentrancy guard present - SAFE
        balances[msg.sender] -= amount;
        ICallback(callback).onWithdraw(msg.sender, amount);
        payable(msg.sender).transfer(amount);
    }

    // TN3: View function (no state changes)
    function checkBalance(address user, address validator) external view returns (bool) {
        // External call in view function - SAFE (no state changes)
        return IExternalContract(validator).validate(user);
    }

    // TN4: Pure function (no state access)
    function calculate(uint256 a, uint256 b) external pure returns (uint256) {
        // No external calls, pure computation - SAFE
        return a + b;
    }

    // TN5: Internal function (not externally callable)
    function _internalCallback(address callback, uint256 amount) internal {
        balances[msg.sender] += amount;

        // Internal visibility - SAFE from external attack
        ICallback(callback).afterDeposit(msg.sender, amount);
    }

    // TN6: Private function
    function _privateExecute(address target, bytes memory data) private {
        balances[msg.sender] = 100;

        // Private visibility - SAFE
        (bool success,) = target.call(data);
        require(success);
    }

    // TN7: CEI pattern (Checks-Effects-Interactions)
    function withdrawCEI(uint256 amount, address callback) external {
        // Checks
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Effects (state changes FIRST)
        balances[msg.sender] -= amount;

        // Interactions (external calls LAST) - SAFE pattern
        payable(msg.sender).transfer(amount);
        ICallback(callback).onWithdraw(msg.sender, amount);
    }

    // TN8: Both access control AND reentrancy guard
    function adminWithdraw(uint256 amount, address callback) external onlyOwner nonReentrant {
        balances[msg.sender] -= amount;

        // Protected by both modifiers - SAFE
        ICallback(callback).onWithdraw(msg.sender, amount);
        payable(msg.sender).transfer(amount);
    }

    // TN9: No state writes (read-only operation with callback)
    function notifyExternal(address callback) external {
        // External call but no state changes - SAFE (pattern requires writes_state)
        ICallback(callback).onWithdraw(msg.sender, 0);
    }

    constructor() {
        owner = msg.sender;
    }

    // TN10: Initialization with callback (initializer pattern)
    bool private initializedWithCallback;

    function initializeWithCallback(address initialCallback) external {
        require(!initializedWithCallback, "Already initialized");
        initializedWithCallback = true;

        balances[msg.sender] = 1000;

        // Initializer external call - but no modifier detection
        ICallback(initialCallback).afterDeposit(msg.sender, 1000);
    }
}

// =============================================================================
// EDGE CASES - Boundary conditions
// =============================================================================

contract ExternalCallEdgeCases {
    mapping(address => uint256) public balances;
    address public owner;
    bool private initialized;

    modifier initializer() {
        require(!initialized, "Already initialized");
        _;
        initialized = true;
    }

    // EDGE1: Initializer function (should be excluded by pattern)
    function initialize(address callback) external initializer {
        owner = msg.sender;
        balances[msg.sender] = 1000;

        // Initializer external call - SAFE (one-time setup)
        ICallback(callback).afterDeposit(msg.sender, 1000);
    }

    // EDGE2: External call with require(msg.sender == owner) inline
    function withdrawWithRequire(uint256 amount, address callback) external {
        require(msg.sender == owner, "Not owner");

        balances[msg.sender] -= amount;

        // Has access check but not via modifier - may flag as FP
        ICallback(callback).onWithdraw(msg.sender, amount);
    }

    // EDGE3: External call with if-revert pattern
    function withdrawWithIf(uint256 amount, address callback) external {
        if (msg.sender != owner) revert("Not owner");

        balances[msg.sender] -= amount;

        // Has access check with if-revert - may flag as FP
        ICallback(callback).onWithdraw(msg.sender, amount);
    }

    // EDGE4: Try-catch external call
    function withdrawWithTryCatch(uint256 amount, address callback) external {
        balances[msg.sender] -= amount;

        // Try-catch handles external call failure
        try ICallback(callback).onWithdraw(msg.sender, amount) {
            // Success
        } catch {
            // Failure handled gracefully
        }

        payable(msg.sender).transfer(amount);
    }

    // EDGE5: Staticcall (read-only)
    function validateWithStaticcall(address target, bytes memory data) external {
        balances[msg.sender] += 1;

        // Staticcall is read-only but still external
        (bool success,) = target.staticcall(data);
        require(success, "Validation failed");
    }

    // EDGE6: External call to trusted/hardcoded address
    function callTrustedContract(bytes memory data) external {
        address trustedContract = 0x1234567890123456789012345678901234567890;

        balances[msg.sender] += 1;

        // Hardcoded trusted address - still vulnerable to reentrancy
        (bool success,) = trustedContract.call(data);
        require(success);
    }

    // EDGE7: Multiple modifiers including custom
    modifier whenNotPaused() {
        require(true, "Paused");
        _;
    }

    function withdrawMultiModifier(uint256 amount, address callback) external whenNotPaused {
        balances[msg.sender] -= amount;

        // Has custom modifier but no access control - should flag
        ICallback(callback).onWithdraw(msg.sender, amount);
    }
}

// =============================================================================
// VARIATION TESTS - Different implementations of same vulnerability
// =============================================================================

contract ExternalCallVariations {
    mapping(address => uint256) public deposits;  // Different variable name
    mapping(address => uint256) public userShares;  // Different variable name
    address public controller;  // Different role name
    address public admin;  // Different role name

    modifier onlyController() {
        require(msg.sender == controller, "Not controller");
        _;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    // VAR1: Different variable names - deposits instead of balances
    function extractFunds(uint256 amount, address notificationContract) external {
        deposits[msg.sender] -= amount;

        // VULNERABLE - different naming
        ICallback(notificationContract).onWithdraw(msg.sender, amount);
    }

    // VAR2: Different role name - controller instead of owner
    function controllerExecute(address target, bytes memory data) external onlyController {
        deposits[msg.sender] += 1;

        // SAFE - has controller access control
        (bool success,) = target.call(data);
        require(success);
    }

    // VAR3: Shares instead of balances
    function redeemShares(uint256 shares, address callback) external {
        userShares[msg.sender] -= shares;

        // VULNERABLE - operates on shares
        ICallback(callback).onWithdraw(msg.sender, shares);
    }

    // VAR4: Admin role protection
    function adminOperation(address target, bytes memory data) external onlyAdmin {
        deposits[msg.sender] = 100;

        // SAFE - admin access control
        (bool success,) = target.call(data);
        require(success);
    }

    // VAR5: Different function name - claim instead of withdraw
    function claimRewards(uint256 amount, address hook) public {
        deposits[msg.sender] -= amount;

        // VULNERABLE - different naming pattern
        ICallback(hook).afterDeposit(msg.sender, amount);
    }

    // VAR6: Different state variable structure - struct
    struct Account {
        uint256 balance;
        uint256 shares;
        bool active;
    }

    mapping(address => Account) public accounts;

    function withdrawFromAccount(uint256 amount, address callback) external {
        accounts[msg.sender].balance -= amount;

        // VULNERABLE - struct field modification
        ICallback(callback).onWithdraw(msg.sender, amount);
    }
}

// =============================================================================
// FALSE POSITIVE CANDIDATES - Might incorrectly flag
// =============================================================================

contract PotentialFalsePositives {
    mapping(address => uint256) public balances;
    mapping(address => bool) public trustedCallbacks;
    address public owner;

    // FP1: Whitelisted callback addresses
    function withdrawTrusted(uint256 amount, address callback) external {
        require(trustedCallbacks[callback], "Callback not trusted");

        balances[msg.sender] -= amount;

        // Callback is whitelisted but pattern may not detect this
        ICallback(callback).onWithdraw(msg.sender, amount);
    }

    // FP2: Pull payment pattern (intentional public access)
    function claimPendingReward() external {
        uint256 reward = balances[msg.sender];
        balances[msg.sender] = 0;

        // Intentional callback for reward distribution
        // Pattern may flag but this is intended design
        ICallback(msg.sender).afterDeposit(msg.sender, reward);
    }

    // FP3: Oracle callback (intended public access)
    function updatePrice(address oracle) external {
        // State write
        balances[address(this)] += 1;

        // Intentional oracle callback - may be flagged
        IExternalContract(oracle).process(abi.encode(block.timestamp));
    }
}
