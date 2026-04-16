// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Vault - Test fixture with known vulnerabilities
 * @notice This contract has intentional vulnerabilities for testing
 *
 * KNOWN VULNERABILITIES (Ground Truth):
 *
 * 1. VAULT-001: Reentrancy in withdraw()
 *    - Type: reentrancy
 *    - Severity: CRITICAL
 *    - Pattern: reentrancy-classic
 *    - Operations: TRANSFERS_VALUE_OUT before WRITES_USER_BALANCE
 *    - Signature: R:bal→X:out→W:bal
 *
 * 2. VAULT-002: Missing access control on setOwner()
 *    - Type: access-control
 *    - Severity: CRITICAL
 *    - Pattern: weak-access-control
 *    - Properties: has_access_gate = false, modifies_owner = true
 *
 * SAFE FUNCTIONS (Should NOT be flagged):
 *
 * - emergencyWithdraw(): Has onlyOwner modifier (has_access_gate = true)
 * - transferOwnership(): Has onlyOwner modifier
 */
contract Vault {
    // ============ State Variables ============
    mapping(address => uint256) public balances;
    address public owner;
    bool private _locked;

    // ============ Events ============
    event Deposit(address indexed user, uint256 amount);
    event Withdrawal(address indexed user, uint256 amount);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // ============ Modifiers ============
    modifier onlyOwner() {
        require(msg.sender == owner, "Vault: caller is not the owner");
        _;
    }

    modifier nonReentrant() {
        require(!_locked, "Vault: reentrant call");
        _locked = true;
        _;
        _locked = false;
    }

    // ============ Constructor ============
    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    // ============ Core Functions ============

    /**
     * @notice Deposit ETH into the vault
     * @dev Safe function - no vulnerabilities
     */
    function deposit() external payable {
        require(msg.value > 0, "Vault: zero deposit");
        balances[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    /**
     * @notice Withdraw ETH from the vault
     * @dev VULNERABILITY: Reentrancy - external call before state update
     *
     * EXPECTED DETECTION:
     * - BSKG Operations: TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE
     * - Pattern Match: reentrancy-classic
     * - Behavioral Signature: R:bal→X:out→W:bal (vulnerable)
     */
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Vault: insufficient balance");

        // BUG: External call BEFORE state update
        (bool success,) = msg.sender.call{value: amount}("");
        require(success, "Vault: transfer failed");

        // State update AFTER external call = REENTRANCY
        balances[msg.sender] -= amount;

        emit Withdrawal(msg.sender, amount);
    }

    /**
     * @notice Safe withdrawal with reentrancy guard
     * @dev This function is SAFE - should NOT be flagged
     */
    function safeWithdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Vault: insufficient balance");

        // Safe: reentrancy guard prevents re-entry
        balances[msg.sender] -= amount;

        (bool success,) = msg.sender.call{value: amount}("");
        require(success, "Vault: transfer failed");

        emit Withdrawal(msg.sender, amount);
    }

    // ============ Admin Functions ============

    /**
     * @notice Emergency withdraw all funds
     * @dev Safe function - has onlyOwner modifier
     *
     * EXPECTED: NOT flagged for access control issues
     * - BSKG Property: has_access_gate = true
     */
    function emergencyWithdraw() external onlyOwner {
        uint256 balance = address(this).balance;
        payable(owner).transfer(balance);
    }

    /**
     * @notice Set new owner (VULNERABLE)
     * @dev VULNERABILITY: Missing access control
     *
     * EXPECTED DETECTION:
     * - BSKG Operations: MODIFIES_OWNER
     * - BSKG Property: has_access_gate = false
     * - Pattern Match: weak-access-control
     */
    function setOwner(address newOwner) external {
        // BUG: No access control! Anyone can call this
        require(newOwner != address(0), "Vault: zero address");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }

    /**
     * @notice Transfer ownership (SAFE)
     * @dev Safe function - has onlyOwner modifier
     *
     * EXPECTED: NOT flagged for access control issues
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Vault: zero address");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }

    // ============ View Functions ============

    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }

    function getTotalDeposits() external view returns (uint256) {
        return address(this).balance;
    }
}
