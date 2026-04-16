// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title OperationsTest
 * @notice Test contract for semantic operation detection (Phase 1)
 * @dev Contains various patterns to test all 20 semantic operations
 */
contract OperationsTest {
    // State variables for balance tracking
    mapping(address => uint256) public balances;
    mapping(address => uint256) private _balances;

    // State variables for access control
    address public owner;
    address private _admin;
    mapping(address => bool) public operators;
    mapping(bytes32 => mapping(address => bool)) private _roles;

    // State variables for privileged state
    uint256 public fee;
    address public treasury;
    address public implementation;

    // Oracle interface
    address public oracle;

    // Events
    event Withdrawal(address indexed user, uint256 amount);
    event OwnershipTransferred(address indexed oldOwner, address indexed newOwner);
    event RoleGranted(bytes32 indexed role, address indexed account);

    // Modifiers for access control
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier onlyOperator() {
        require(operators[msg.sender], "Not operator");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // =========================================================================
    // VALUE MOVEMENT OPERATIONS
    // =========================================================================

    /**
     * @notice Vulnerable withdrawal - external call before state update
     * Expected operations: READS_USER_BALANCE, TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE
     * Expected signature: R:bal->X:out->W:bal (vulnerable)
     */
    function withdrawVulnerable(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        payable(msg.sender).transfer(amount);
        balances[msg.sender] -= amount;
        emit Withdrawal(msg.sender, amount);
    }

    /**
     * @notice Safe withdrawal - CEI pattern
     * Expected operations: READS_USER_BALANCE, WRITES_USER_BALANCE, TRANSFERS_VALUE_OUT
     * Expected signature: R:bal->W:bal->X:out (safe CEI)
     */
    function withdrawCEI(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
        emit Withdrawal(msg.sender, amount);
    }

    /**
     * @notice Payable function that receives ETH
     * Expected operations: RECEIVES_VALUE_IN, WRITES_USER_BALANCE
     */
    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    /**
     * @notice Low-level ETH transfer
     * Expected operations: TRANSFERS_VALUE_OUT, CALLS_EXTERNAL
     */
    function sendETH(address payable recipient, uint256 amount) external onlyOwner {
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Transfer failed");
    }

    // =========================================================================
    // ACCESS CONTROL OPERATIONS
    // =========================================================================

    /**
     * @notice Transfer ownership
     * Expected operations: CHECKS_PERMISSION, MODIFIES_OWNER, MODIFIES_CRITICAL_STATE
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Zero address");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }

    /**
     * @notice Grant operator role
     * Expected operations: CHECKS_PERMISSION, MODIFIES_ROLES
     */
    function grantOperator(address account) external onlyOwner {
        operators[account] = true;
    }

    /**
     * @notice Revoke operator role
     * Expected operations: CHECKS_PERMISSION, MODIFIES_ROLES
     */
    function revokeOperator(address account) external onlyOwner {
        operators[account] = false;
    }

    /**
     * @notice Internal role management
     * Expected operations: CHECKS_PERMISSION, MODIFIES_ROLES
     */
    function grantRole(bytes32 role, address account) external onlyOwner {
        _roles[role][account] = true;
        emit RoleGranted(role, account);
    }

    // =========================================================================
    // EXTERNAL INTERACTION OPERATIONS
    // =========================================================================

    /**
     * @notice External call to trusted contract
     * Expected operations: CALLS_EXTERNAL
     */
    function callTrusted() external view returns (uint256) {
        return IERC20(treasury).balanceOf(address(this));
    }

    /**
     * @notice External call to untrusted address (from parameter)
     * Expected operations: CALLS_EXTERNAL, CALLS_UNTRUSTED
     */
    function callUntrusted(address target) external returns (bytes memory) {
        (bool success, bytes memory data) = target.call("");
        require(success, "Call failed");
        return data;
    }

    /**
     * @notice Read from oracle
     * Expected operations: READS_ORACLE, READS_EXTERNAL_VALUE, CALLS_EXTERNAL
     */
    function getPrice() external view returns (uint256) {
        return IOracle(oracle).latestAnswer();
    }

    // =========================================================================
    // STATE MANAGEMENT OPERATIONS
    // =========================================================================

    /**
     * @notice Modify critical state (fee)
     * Expected operations: CHECKS_PERMISSION, MODIFIES_CRITICAL_STATE
     */
    function setFee(uint256 newFee) external onlyOwner {
        require(newFee <= 1000, "Fee too high");
        fee = newFee;
    }

    /**
     * @notice Modify critical state (treasury)
     * Expected operations: CHECKS_PERMISSION, MODIFIES_CRITICAL_STATE
     */
    function setTreasury(address newTreasury) external onlyOwner {
        treasury = newTreasury;
    }

    /**
     * @notice Initialize function (simulated)
     * Expected operations: INITIALIZES_STATE, MODIFIES_OWNER
     */
    function initialize(address _owner) external {
        require(owner == address(0), "Already initialized");
        owner = _owner;
    }

    // =========================================================================
    // CONTROL FLOW OPERATIONS
    // =========================================================================

    /**
     * @notice Loop over array (DoS risk)
     * Expected operations: LOOPS_OVER_ARRAY, WRITES_USER_BALANCE
     */
    function batchTransfer(address[] calldata recipients, uint256 amount) external onlyOwner {
        for (uint256 i = 0; i < recipients.length; i++) {
            balances[recipients[i]] += amount;
        }
    }

    /**
     * @notice Uses block.timestamp
     * Expected operations: USES_TIMESTAMP, VALIDATES_INPUT
     */
    function timelockCheck(uint256 deadline) external view returns (bool) {
        require(block.timestamp <= deadline, "Expired");
        return true;
    }

    /**
     * @notice Uses block.number
     * Expected operations: USES_BLOCK_DATA
     */
    function getBlockNumber() external view returns (uint256) {
        return block.number;
    }

    /**
     * @notice Uses blockhash
     * Expected operations: USES_BLOCK_DATA
     */
    function getBlockHash(uint256 blockNumber) external view returns (bytes32) {
        return blockhash(blockNumber);
    }

    // =========================================================================
    // ARITHMETIC OPERATIONS
    // =========================================================================

    /**
     * @notice Division operation
     * Expected operations: PERFORMS_DIVISION
     */
    function calculateShare(uint256 amount, uint256 totalSupply) external pure returns (uint256) {
        require(totalSupply > 0, "Division by zero");
        return amount / totalSupply;
    }

    /**
     * @notice Multiplication operation
     * Expected operations: PERFORMS_MULTIPLICATION
     */
    function calculateFee(uint256 amount) external view returns (uint256) {
        return amount * fee / 10000;
    }

    /**
     * @notice Division and multiplication (precision risk)
     * Expected operations: PERFORMS_DIVISION, PERFORMS_MULTIPLICATION
     */
    function calculateAmountWithPrecision(uint256 a, uint256 b, uint256 c) external pure returns (uint256) {
        return a * b / c;
    }

    // =========================================================================
    // VALIDATION OPERATIONS
    // =========================================================================

    /**
     * @notice Validates input parameters
     * Expected operations: VALIDATES_INPUT
     */
    function validateAndStore(uint256 value, address recipient) external {
        require(value > 0, "Value must be positive");
        require(recipient != address(0), "Invalid recipient");
        balances[recipient] = value;
    }

    /**
     * @notice Emits events
     * Expected operations: EMITS_EVENT
     */
    function emitEvent() external {
        emit OwnershipTransferred(address(0), owner);
    }

    // =========================================================================
    // COMPLEX PATTERNS
    // =========================================================================

    /**
     * @notice Complex pattern: Reentrancy vulnerable flash loan
     * Expected operations: READS_USER_BALANCE, TRANSFERS_VALUE_OUT, CALLS_UNTRUSTED, WRITES_USER_BALANCE
     */
    function flashLoanVulnerable(address borrower, uint256 amount) external {
        uint256 balanceBefore = balances[address(this)];
        require(balanceBefore >= amount, "Insufficient liquidity");

        payable(borrower).transfer(amount);
        IFlashBorrower(borrower).onFlashLoan(amount);

        require(balances[address(this)] >= balanceBefore, "Loan not repaid");
    }

    /**
     * @notice Safe pattern: Access controlled, validated, event emission
     * Expected operations: CHECKS_PERMISSION, VALIDATES_INPUT, MODIFIES_CRITICAL_STATE, EMITS_EVENT
     */
    function safeAdminAction(uint256 newFee, address newTreasury) external onlyOwner {
        require(newFee <= 500, "Fee too high");
        require(newTreasury != address(0), "Invalid treasury");

        fee = newFee;
        treasury = newTreasury;

        emit OwnershipTransferred(address(0), newTreasury);
    }
}

// =========================================================================
// MOCK INTERFACES
// =========================================================================

interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

interface IOracle {
    function latestAnswer() external view returns (uint256);
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80);
}

interface IFlashBorrower {
    function onFlashLoan(uint256 amount) external;
}
