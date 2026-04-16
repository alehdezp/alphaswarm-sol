// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title FeeOnTransferTest
 * @notice Test contract for token-001-unhandled-fee-on-transfer pattern
 * @dev Tests deposit-like functions that may not handle fee-on-transfer tokens correctly
 *
 * Pattern Overview:
 * - TRUE POSITIVE: transferFrom() + balance write WITHOUT balance verification
 * - TRUE NEGATIVE: transferFrom() + balance write WITH before/after balance check
 * - EDGE CASES: View functions, internal functions, withdrawals
 * - VARIATIONS: Different naming (deposit/stake/addLiquidity/contribute)
 */

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract FeeOnTransferTest {
    mapping(address => uint256) public balances;
    mapping(address => uint256) public shares;
    mapping(address => uint256) public deposits;
    mapping(address => uint256) public stakes;

    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // =========================================================================
    // TRUE POSITIVES - Vulnerable to fee-on-transfer tokens
    // =========================================================================

    /// @dev TP1: Standard deposit without balance verification
    /// Pattern: uses_erc20_transfer_from=true AND writes_balance_state=true
    ///          AND checks_received_amount=false
    function deposit(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;  // VULNERABLE: Assumes amount received = amount
    }

    /// @dev TP2: Variation - stake naming
    function stake(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        stakes[msg.sender] += amount;  // VULNERABLE: Same issue
    }

    /// @dev TP3: Variation - addLiquidity naming
    function addLiquidity(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        deposits[msg.sender] += amount;  // VULNERABLE: Same issue
    }

    /// @dev TP4: Variation - contribute naming
    function contribute(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        shares[msg.sender] += amount;  // VULNERABLE: Same issue
    }

    /// @dev TP5: Share-based deposit without validation
    function depositForShares(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        // Calculate shares based on amount (not actual received)
        uint256 shareAmount = amount * 100 / 95;  // Some share calculation
        shares[msg.sender] += shareAmount;  // VULNERABLE: Uses amount, not received
    }

    /// @dev TP6: Collateral deposit (DeFi pattern)
    function depositCollateral(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;  // VULNERABLE
    }

    /// @dev TP7: Pool deposit (AMM pattern)
    function addToPool(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        deposits[msg.sender] += amount;  // VULNERABLE
    }

    /// @dev TP8: Fund deposit (investment pattern)
    function fundAccount(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;  // VULNERABLE
    }

    // =========================================================================
    // TRUE NEGATIVES - Safe patterns with balance verification
    // =========================================================================

    /// @dev TN1: Before/after balance check (SAFE)
    /// Pattern: checks_received_amount=true
    function depositSafe(IERC20 token, uint256 amount) external {
        uint256 balanceBefore = token.balanceOf(address(this));
        token.transferFrom(msg.sender, address(this), amount);
        uint256 balanceAfter = token.balanceOf(address(this));

        uint256 actualReceived = balanceAfter - balanceBefore;
        balances[msg.sender] += actualReceived;  // SAFE: Uses actual received amount
    }

    /// @dev TN2: Safe stake with balance verification
    function stakeSafe(IERC20 token, uint256 amount) external {
        uint256 balanceBefore = token.balanceOf(address(this));
        token.transferFrom(msg.sender, address(this), amount);
        uint256 balanceAfter = token.balanceOf(address(this));

        stakes[msg.sender] += balanceAfter - balanceBefore;  // SAFE
    }

    /// @dev TN3: Safe with explicit received amount check
    function depositWithCheck(IERC20 token, uint256 amount) external {
        uint256 balanceBefore = token.balanceOf(address(this));
        token.transferFrom(msg.sender, address(this), amount);
        uint256 balanceAfter = token.balanceOf(address(this));

        uint256 received = balanceAfter - balanceBefore;
        require(received > 0, "No tokens received");

        balances[msg.sender] += received;  // SAFE
    }

    /// @dev TN4: Withdrawal function (NOT affected by fee-on-transfer)
    /// Pattern: is_withdraw_like=true should NOT be flagged
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        // Note: Withdrawal uses IERC20.transfer, not transferFrom
        // Fee-on-transfer issue only affects deposits (transferFrom)
    }

    /// @dev TN5: View function (no state changes)
    /// Pattern: state_mutability=view should NOT be flagged
    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }

    /// @dev TN6: Pure function
    /// Pattern: state_mutability=pure should NOT be flagged
    function calculateShares(uint256 amount) external pure returns (uint256) {
        return amount * 100 / 95;
    }

    // =========================================================================
    // EDGE CASES
    // =========================================================================

    /// @dev EDGE1: Internal function (not externally callable)
    /// Pattern: visibility=internal should NOT be flagged
    function _depositInternal(IERC20 token, uint256 amount) internal {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    /// @dev EDGE2: Private function
    /// Pattern: visibility=private should NOT be flagged
    function _depositPrivate(IERC20 token, uint256 amount) private {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    /// @dev EDGE3: Public function that only reads state
    /// Pattern: uses_erc20_transfer_from=false (no transferFrom call)
    function viewDeposit(address user) external view returns (uint256) {
        return balances[user];
    }

    /// @dev EDGE4: Deposit without balance write (should NOT flag - no accounting impact)
    /// Pattern: writes_balance_state=false
    function depositNoAccounting(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        // No balance update - weird but not the fee-on-transfer vulnerability
    }

    /// @dev EDGE5: Multiple transfers with verification on second one only
    /// This is VULNERABLE on the first transfer but SAFE on second
    function depositTwoTokens(IERC20 token1, IERC20 token2, uint256 amount) external {
        // First transfer: VULNERABLE
        token1.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;

        // Second transfer: SAFE
        uint256 balanceBefore = token2.balanceOf(address(this));
        token2.transferFrom(msg.sender, address(this), amount);
        uint256 balanceAfter = token2.balanceOf(address(this));
        balances[msg.sender] += balanceAfter - balanceBefore;
    }

    /// @dev EDGE6: Withdrawal-like function that transfers OUT
    /// Pattern: is_withdraw_like=true should NOT be flagged
    function unstake(uint256 amount) external {
        require(stakes[msg.sender] >= amount, "Insufficient stake");
        stakes[msg.sender] -= amount;
        // Transfer out (withdrawal pattern)
    }

    /// @dev EDGE7: Transfer without user balance write (treasury/fee collection)
    /// Pattern: writes_balance_state=false
    function collectFee(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        // No user balance update - fees go to contract
    }

    // =========================================================================
    // VARIATIONS - Different implementation patterns (all VULNERABLE)
    // =========================================================================

    /// @dev VAR1: Using deposits mapping instead of balances
    function depositToMapping(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        deposits[msg.sender] += amount;  // VULNERABLE: Different mapping name
    }

    /// @dev VAR2: Using shares mapping
    function depositForSharesMapping(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        shares[msg.sender] += amount;  // VULNERABLE: Different mapping name
    }

    /// @dev VAR3: Struct-based accounting (if property detector supports it)
    struct UserAccount {
        uint256 balance;
        uint256 shares;
    }
    mapping(address => UserAccount) public accounts;

    function depositToStruct(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        accounts[msg.sender].balance += amount;  // VULNERABLE: Struct field write
    }

    /// @dev VAR4: Using custom token parameter name
    function depositAsset(IERC20 asset, uint256 amount) external {
        asset.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;  // VULNERABLE: Parameter named "asset"
    }

    /// @dev VAR5: Using "underlying" token naming
    function depositUnderlying(IERC20 underlying, uint256 amount) external {
        underlying.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;  // VULNERABLE: Parameter named "underlying"
    }

    /// @dev VAR6: Multi-step deposit with intermediate variable
    function depositMultiStep(IERC20 token, uint256 amount) external {
        bool success = token.transferFrom(msg.sender, address(this), amount);
        require(success, "Transfer failed");

        uint256 creditAmount = amount;  // Intermediate variable
        balances[msg.sender] += creditAmount;  // VULNERABLE: Still uses amount
    }

    /// @dev VAR7: Deposit with event emission (common pattern)
    event Deposited(address indexed user, uint256 amount);

    function depositWithEvent(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;  // VULNERABLE
        emit Deposited(msg.sender, amount);
    }

    /// @dev VAR8: Deposit with reentrancy guard (still vulnerable to fee-on-transfer)
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "No reentrancy");
        locked = true;
        _;
        locked = false;
    }

    function depositWithGuard(IERC20 token, uint256 amount) external nonReentrant {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;  // VULNERABLE: Guard doesn't prevent fee issue
    }

    // =========================================================================
    // ADDITIONAL SAFE PATTERNS (should NOT flag)
    // =========================================================================

    /// @dev SAFE1: Using SafeERC20 with balance check
    function depositSafeERC20(IERC20 token, uint256 amount) external {
        uint256 balanceBefore = token.balanceOf(address(this));
        // Assume SafeERC20.safeTransferFrom used here
        token.transferFrom(msg.sender, address(this), amount);
        uint256 balanceAfter = token.balanceOf(address(this));

        uint256 received = balanceAfter - balanceBefore;
        require(received > 0, "No tokens received");
        balances[msg.sender] += received;  // SAFE
    }

    /// @dev SAFE2: ERC4626-style deposit (share-based with balance check)
    function depositERC4626Style(IERC20 token, uint256 amount) external returns (uint256 shares_) {
        uint256 balanceBefore = token.balanceOf(address(this));
        token.transferFrom(msg.sender, address(this), amount);
        uint256 balanceAfter = token.balanceOf(address(this));

        uint256 received = balanceAfter - balanceBefore;

        // Calculate shares based on actual received amount
        shares_ = received * 100 / 95;  // Example calculation
        shares[msg.sender] += shares_;  // SAFE: Uses actual received

        return shares_;
    }

    /// @dev SAFE3: Deposit with minimum received check
    function depositWithMinimum(IERC20 token, uint256 amount, uint256 minReceived) external {
        uint256 balanceBefore = token.balanceOf(address(this));
        token.transferFrom(msg.sender, address(this), amount);
        uint256 balanceAfter = token.balanceOf(address(this));

        uint256 received = balanceAfter - balanceBefore;
        require(received >= minReceived, "Insufficient received");

        balances[msg.sender] += received;  // SAFE
    }
}
