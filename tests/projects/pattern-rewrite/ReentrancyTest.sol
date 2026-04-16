// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =============================================================================
// Comprehensive Test Contract for vm-001-classic Pattern
// Testing: Classic Reentrancy (CEI Violation)
// =============================================================================

/**
 * @title ReentrancyTest
 * @notice Brutal test suite for vm-001-classic pattern
 * @dev Tests true positives, true negatives, edge cases, and naming variations
 */
contract ReentrancyTest {

    mapping(address => uint256) public balances;
    mapping(address => uint256) public funds;
    mapping(address => uint256) public shares;
    mapping(address => uint256) public deposits;

    uint256 private locked = 1;

    // =============================================================================
    // TRUE POSITIVES - These SHOULD be flagged
    // =============================================================================

    /// @dev TP1: Classic withdraw - balance read, ETH transfer, balance write
    /// EXPECTED: FLAGGED (TRANSFERS_VALUE_OUT before WRITES_USER_BALANCE)
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        payable(msg.sender).transfer(amount);  // TRANSFERS_VALUE_OUT
        balances[msg.sender] -= amount;         // WRITES_USER_BALANCE (AFTER!)
    }

    /// @dev TP2: Renamed function extract() with funds variable
    /// EXPECTED: FLAGGED (tests naming variation)
    function extract(uint256 amount) external {
        require(funds[msg.sender] >= amount, "Insufficient funds");
        payable(msg.sender).transfer(amount);  // TRANSFERS_VALUE_OUT
        funds[msg.sender] -= amount;            // WRITES_USER_BALANCE (AFTER!)
    }

    /// @dev TP3: Obfuscated function name with shares variable
    /// EXPECTED: FLAGGED (tests obfuscation resistance)
    function fn_0x123abc(uint256 amount) external {
        require(shares[msg.sender] >= amount, "Insufficient shares");
        payable(msg.sender).transfer(amount);  // TRANSFERS_VALUE_OUT
        shares[msg.sender] -= amount;           // WRITES_USER_BALANCE (AFTER!)
    }

    /// @dev TP4: Using call() instead of transfer()
    /// EXPECTED: FLAGGED (tests different transfer mechanisms)
    function withdrawViaCall(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;  // WRITES_USER_BALANCE (AFTER!)
    }

    /// @dev TP5: Using send() instead of transfer()
    /// EXPECTED: FLAGGED (tests another transfer mechanism)
    function withdrawViaSend(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        bool success = payable(msg.sender).send(amount);
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;  // WRITES_USER_BALANCE (AFTER!)
    }

    // =============================================================================
    // TRUE NEGATIVES - These should NOT be flagged
    // =============================================================================

    /// @dev TN1: Correct CEI pattern - balance write BEFORE transfer
    /// EXPECTED: NOT FLAGGED (safe pattern)
    function withdrawSafe(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;         // WRITES_USER_BALANCE FIRST
        payable(msg.sender).transfer(amount);  // TRANSFERS_VALUE_OUT AFTER
    }

    /// @dev TN2: Function with nonReentrant-like guard
    /// EXPECTED: NOT FLAGGED (has reentrancy guard)
    function withdrawWithGuard(uint256 amount) external {
        require(locked == 1, "Reentrant call");
        locked = 2;

        require(balances[msg.sender] >= amount, "Insufficient balance");
        payable(msg.sender).transfer(amount);
        balances[msg.sender] -= amount;

        locked = 1;
    }

    /// @dev TN3: Renamed guard (noReentrancy pattern)
    /// EXPECTED: NOT FLAGGED if guard detection works
    modifier noReentrancy() {
        require(locked == 1, "No reentrancy");
        locked = 2;
        _;
        locked = 1;
    }

    function withdrawWithRenamedGuard(uint256 amount) external noReentrancy {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        payable(msg.sender).transfer(amount);
        balances[msg.sender] -= amount;
    }

    /// @dev TN4: View function that only reads balances
    /// EXPECTED: NOT FLAGGED (view function, no state changes)
    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }

    /// @dev TN5: Function that transfers but doesn't write balance
    /// EXPECTED: NOT FLAGGED (no WRITES_USER_BALANCE operation)
    function donate() external payable {
        // Just accepts ETH, no balance state update
    }

    /// @dev TN6: Function that writes balance but doesn't transfer
    /// EXPECTED: NOT FLAGGED (no TRANSFERS_VALUE_OUT operation)
    function updateBalance(address user, uint256 amount) external {
        balances[user] = amount;  // Only writes, no transfer
    }

    // =============================================================================
    // EDGE CASES
    // =============================================================================

    /// @dev EDGE1: Internal function with CEI violation
    /// EXPECTED: NOT FLAGGED (not external/public)
    function _internalWithdraw(address user, uint256 amount) internal {
        require(balances[user] >= amount, "Insufficient balance");
        payable(user).transfer(amount);  // Transfer before write
        balances[user] -= amount;
    }

    /// @dev EDGE2: Private function with CEI violation
    /// EXPECTED: NOT FLAGGED (not external/public)
    function _privateWithdraw(address user, uint256 amount) private {
        require(balances[user] >= amount, "Insufficient balance");
        payable(user).transfer(amount);
        balances[user] -= amount;
    }

    /// @dev EDGE3: Pure function
    /// EXPECTED: NOT FLAGGED (pure, no state access)
    function calculate(uint256 a, uint256 b) external pure returns (uint256) {
        return a + b;
    }

    /// @dev EDGE4: Constructor
    /// EXPECTED: NOT FLAGGED (constructor exclusion)
    constructor() {
        balances[msg.sender] = 1000 ether;
    }

    /// @dev EDGE5: Fallback function with CEI violation
    /// EXPECTED: Potentially FLAGGED (external, but special case)
    fallback() external payable {
        balances[msg.sender] += msg.value;
    }

    /// @dev EDGE6: Receive function
    /// EXPECTED: NOT FLAGGED (only receives, no violation possible)
    receive() external payable {
        balances[msg.sender] += msg.value;
    }
}

// =============================================================================
// Additional Test Contracts for Variations
// =============================================================================

/**
 * @title ReentrancyVariations
 * @notice Tests different coding styles and patterns
 */
contract ReentrancyVariations {

    mapping(address => uint256) public userDeposits;  // Renamed from balances
    mapping(address => uint256) public accountShares;  // Different naming

    /// @dev VARIATION1: Different variable naming convention
    /// EXPECTED: FLAGGED
    function removeFunds(uint256 amt) external {
        require(userDeposits[msg.sender] >= amt, "Insufficient");
        payable(msg.sender).transfer(amt);
        userDeposits[msg.sender] -= amt;
    }

    /// @dev VARIATION2: Using block-style indentation
    /// EXPECTED: FLAGGED
    function extractShares(uint256 shareAmount) external
    {
        require(accountShares[msg.sender] >= shareAmount, "Insufficient shares");

        payable(msg.sender).transfer(shareAmount);

        accountShares[msg.sender] -= shareAmount;
    }

    /// @dev VARIATION3: Compact single-line style
    /// EXPECTED: FLAGGED
    function quickWithdraw(uint256 a) external { require(userDeposits[msg.sender]>=a); payable(msg.sender).transfer(a); userDeposits[msg.sender]-=a; }
}

/**
 * @title ReentrancyWithInheritance
 * @notice Tests inherited guard detection
 */
abstract contract BaseGuard {
    uint256 private _status;

    modifier nonReentrant() {
        require(_status != 2, "Reentrant");
        _status = 2;
        _;
        _status = 1;
    }
}

contract ReentrancyWithInheritance is BaseGuard {

    mapping(address => uint256) public balances;

    /// @dev EDGE7: Inherited guard
    /// EXPECTED: NOT FLAGGED (has inherited nonReentrant)
    function withdrawWithInheritedGuard(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        payable(msg.sender).transfer(amount);  // Transfer before write
        balances[msg.sender] -= amount;         // But protected by guard
    }

    /// @dev TP6: Vulnerable even with base contract (no guard applied)
    /// EXPECTED: FLAGGED
    function withdrawNoGuard(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        payable(msg.sender).transfer(amount);
        balances[msg.sender] -= amount;
    }
}

/**
 * @title ERC777ReentrancyTest
 * @notice Tests token transfer reentrancy
 */
interface IERC777 {
    function send(address recipient, uint256 amount, bytes calldata data) external;
}

contract ERC777ReentrancyTest {

    mapping(address => uint256) public tokenBalances;
    IERC777 public token;

    constructor(address _token) {
        token = IERC777(_token);
    }

    /// @dev TP7: ERC777 token callback reentrancy
    /// EXPECTED: FLAGGED (ERC777 has tokensReceived hook)
    function withdrawTokens(uint256 amount) external {
        require(tokenBalances[msg.sender] >= amount, "Insufficient balance");
        token.send(msg.sender, amount, "");  // TRANSFERS_VALUE_OUT (with callback!)
        tokenBalances[msg.sender] -= amount;  // WRITES_USER_BALANCE (AFTER!)
    }

    /// @dev TN7: Safe token withdrawal
    /// EXPECTED: NOT FLAGGED (CEI pattern)
    function withdrawTokensSafe(uint256 amount) external {
        require(tokenBalances[msg.sender] >= amount, "Insufficient balance");
        tokenBalances[msg.sender] -= amount;  // State update first
        token.send(msg.sender, amount, "");    // Transfer after
    }
}

/**
 * @title CrossFunctionReentrancy
 * @notice Tests cross-function reentrancy variant
 */
contract CrossFunctionReentrancy {

    mapping(address => uint256) public balances;
    mapping(address => uint256) public rewards;

    /// @dev TP8: Cross-function reentrancy - function A
    /// EXPECTED: FLAGGED (transfers before updating shared state)
    function withdrawBalance(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        payable(msg.sender).transfer(amount);  // External call
        balances[msg.sender] -= amount;         // State update after
    }

    /// @dev Function B reads the same state (demonstrates cross-function risk)
    function claimRewards() external {
        uint256 balance = balances[msg.sender];  // Reads potentially stale state
        uint256 reward = balance / 10;
        rewards[msg.sender] += reward;
    }
}

/**
 * @title InitializerTest
 * @notice Tests initializer function exclusion
 */
contract InitializerTest {

    mapping(address => uint256) public balances;
    bool private initialized;

    /// @dev EDGE8: Initializer function
    /// EXPECTED: NOT FLAGGED (is_initializer_function = true)
    function initialize(address[] calldata recipients, uint256[] calldata amounts) external {
        require(!initialized, "Already initialized");
        initialized = true;

        for (uint i = 0; i < recipients.length; i++) {
            payable(recipients[i]).transfer(amounts[i]);  // Transfer before write
            balances[recipients[i]] = amounts[i];          // But in initializer
        }
    }

    /// @dev EDGE9: Function named 'init' but not a true initializer
    /// EXPECTED: FLAGGED (not a real initializer)
    function init(uint256 amount) external {
        payable(msg.sender).transfer(amount);
        balances[msg.sender] -= amount;
    }
}
