// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title UncheckedReturnTest
 * @notice Test contract for token-005-unchecked-return pattern
 * @dev Tests detection of ERC20 transfer/transferFrom/approve calls without return value checks
 *
 * Pattern: token-005-unchecked-return
 * Severity: high
 *
 * TEST COVERAGE:
 * - 12 TRUE POSITIVES: Unchecked transfer/transferFrom/approve calls
 * - 10 TRUE NEGATIVES: SafeERC20 or explicit return value checks
 * - 8 EDGE CASES: Internal/view functions, no state writes, special patterns
 * - 8 VARIATIONS: Different naming conventions, patterns, tokens
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

library SafeERC20 {
    function safeTransfer(IERC20 token, address to, uint256 value) internal {
        (bool success, bytes memory data) = address(token).call(
            abi.encodeWithSelector(token.transfer.selector, to, value)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "SafeERC20: transfer failed");
    }

    function safeTransferFrom(IERC20 token, address from, address to, uint256 value) internal {
        (bool success, bytes memory data) = address(token).call(
            abi.encodeWithSelector(token.transferFrom.selector, from, to, value)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "SafeERC20: transferFrom failed");
    }

    function safeApprove(IERC20 token, address spender, uint256 value) internal {
        (bool success, bytes memory data) = address(token).call(
            abi.encodeWithSelector(token.approve.selector, spender, value)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "SafeERC20: approve failed");
    }
}

contract UncheckedReturnTest {
    using SafeERC20 for IERC20;

    mapping(address => uint256) public balances;
    mapping(address => uint256) public shares;
    mapping(address => uint256) public deposits;
    mapping(address => uint256) public stakes;
    uint256 public totalSupply;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // =========================================================================
    // TRUE POSITIVES - Unchecked transfer/transferFrom/approve (VULNERABLE)
    // =========================================================================

    /// @dev TP1: Unchecked transferFrom in deposit
    function deposit(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        balances[msg.sender] += amount;
    }

    /// @dev TP2: Unchecked transfer in withdraw
    function withdraw(IERC20 token, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        token.transfer(msg.sender, amount); // ❌ No return check
    }

    /// @dev TP3: Unchecked approve - preparation for third party
    function approveRouter(IERC20 token, address router, uint256 amount) external {
        token.approve(router, amount); // ❌ No return check
        totalSupply += amount; // State change after approve
    }

    /// @dev TP4: Unchecked transferFrom with shares accounting
    function stake(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        shares[msg.sender] += amount;
    }

    /// @dev TP5: Unchecked transfer with shares accounting
    function unstake(IERC20 token, uint256 amount) external {
        require(shares[msg.sender] >= amount, "Insufficient shares");
        shares[msg.sender] -= amount;
        token.transfer(msg.sender, amount); // ❌ No return check
    }

    /// @dev TP6: Unchecked transferFrom with deposits accounting
    function contribute(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        deposits[msg.sender] += amount;
    }

    /// @dev TP7: Unchecked transfer with deposits accounting
    function claim(IERC20 token, uint256 amount) external {
        require(deposits[msg.sender] >= amount, "Insufficient deposit");
        deposits[msg.sender] -= amount;
        token.transfer(msg.sender, amount); // ❌ No return check
    }

    /// @dev TP8: Unchecked transferFrom with stakes accounting
    function fundAccount(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        stakes[msg.sender] += amount;
    }

    /// @dev TP9: Unchecked approve with multiple approvals
    function approveMultiple(IERC20 token, address[] calldata spenders, uint256 amount) external {
        for (uint256 i = 0; i < spenders.length; i++) {
            token.approve(spenders[i], amount); // ❌ No return check
        }
        totalSupply += amount * spenders.length;
    }

    /// @dev TP10: Unchecked transferFrom with event
    function depositWithEvent(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        balances[msg.sender] += amount;
        // emit Deposit(msg.sender, amount);
    }

    /// @dev TP11: Unchecked transfer to arbitrary recipient
    function sendTokens(IERC20 token, address recipient, uint256 amount) external {
        token.transfer(recipient, amount); // ❌ No return check
        totalSupply -= amount;
    }

    /// @dev TP12: Unchecked approve before transferFrom pattern
    function depositWithApproval(IERC20 token, address spender, uint256 amount) external {
        token.approve(spender, amount); // ❌ No return check
        balances[msg.sender] += amount;
    }

    // =========================================================================
    // TRUE NEGATIVES - SafeERC20 or return value checks (SAFE)
    // =========================================================================

    /// @dev TN1: SafeERC20 transferFrom
    function depositSafe(IERC20 token, uint256 amount) external {
        token.safeTransferFrom(msg.sender, address(this), amount); // ✓ SafeERC20
        balances[msg.sender] += amount;
    }

    /// @dev TN2: SafeERC20 transfer
    function withdrawSafe(IERC20 token, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        token.safeTransfer(msg.sender, amount); // ✓ SafeERC20
    }

    /// @dev TN3: SafeERC20 approve
    function approveRouterSafe(IERC20 token, address router, uint256 amount) external {
        token.safeApprove(router, amount); // ✓ SafeERC20
        totalSupply += amount;
    }

    /// @dev TN4: Explicit require on transferFrom return
    function depositWithCheck(IERC20 token, uint256 amount) external {
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed"); // ✓ Return checked
        balances[msg.sender] += amount;
    }

    /// @dev TN5: Explicit require on transfer return
    function withdrawWithCheck(IERC20 token, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        require(token.transfer(msg.sender, amount), "Transfer failed"); // ✓ Return checked
    }

    /// @dev TN6: Bool variable + require on transferFrom
    function depositBoolCheck(IERC20 token, uint256 amount) external {
        bool success = token.transferFrom(msg.sender, address(this), amount); // ✓ Return captured
        require(success, "Transfer failed"); // ✓ Return checked
        balances[msg.sender] += amount;
    }

    /// @dev TN7: Bool variable + require on transfer
    function withdrawBoolCheck(IERC20 token, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        bool success = token.transfer(msg.sender, amount); // ✓ Return captured
        require(success, "Transfer failed"); // ✓ Return checked
    }

    /// @dev TN8: Try-catch on transferFrom
    function depositTryCatch(IERC20 token, uint256 amount) external {
        try token.transferFrom(msg.sender, address(this), amount) returns (bool success) {
            require(success, "Transfer returned false"); // ✓ Return checked
            balances[msg.sender] += amount;
        } catch {
            revert("Transfer failed"); // ✓ Failure handled
        }
    }

    /// @dev TN9: Balance before/after check
    function depositBalanceCheck(IERC20 token, uint256 amount) external {
        uint256 balanceBefore = token.balanceOf(address(this));
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed"); // ✓ Return checked
        uint256 balanceAfter = token.balanceOf(address(this));
        uint256 actualReceived = balanceAfter - balanceBefore;
        balances[msg.sender] += actualReceived;
    }

    /// @dev TN10: Approve with bool check
    function approveWithCheck(IERC20 token, address spender, uint256 amount) external {
        bool success = token.approve(spender, amount); // ✓ Return captured
        require(success, "Approval failed"); // ✓ Return checked
        totalSupply += amount;
    }

    // =========================================================================
    // EDGE CASES - Should NOT be flagged for different reasons
    // =========================================================================

    /// @dev EDGE1: Internal function (not public/external)
    function _depositInternal(IERC20 token, uint256 amount) internal {
        token.transferFrom(msg.sender, address(this), amount); // Internal - not flagged
        balances[msg.sender] += amount;
    }

    /// @dev EDGE2: Private function (not public/external)
    function _withdrawPrivate(IERC20 token, uint256 amount) private {
        balances[msg.sender] -= amount;
        token.transfer(msg.sender, amount); // Private - not flagged
    }

    /// @dev EDGE3: View function (no state writes)
    function viewBalance(IERC20 token, address account) external view returns (uint256) {
        return token.balanceOf(account); // View - not flagged
    }

    /// @dev EDGE4: Pure function (no state access)
    function calculateAmount(uint256 a, uint256 b) external pure returns (uint256) {
        return a * b; // Pure - not flagged
    }

    /// @dev EDGE5: Unchecked transfer but no state write
    function transferNoStateWrite(IERC20 token, address recipient, uint256 amount) external {
        token.transfer(recipient, amount); // ❌ No return check BUT no state write
        // No state modification - should NOT be flagged (writes_state=false)
    }

    /// @dev EDGE6: State write but no token call
    function updateBalanceNoTransfer(address user, uint256 amount) external {
        balances[user] += amount; // State write but no token call - not flagged
    }

    /// @dev EDGE7: Fallback function (no ERC20 involved)
    fallback() external payable {
        balances[msg.sender] += msg.value; // Fallback not ERC20 - not flagged
    }

    /// @dev EDGE8: Receive ETH (no ERC20 involved)
    receive() external payable {
        balances[msg.sender] += msg.value; // ETH not ERC20 - not flagged
    }

    // =========================================================================
    // VARIATIONS - Different naming conventions (all VULNERABLE)
    // =========================================================================

    /// @dev VAR1: 'asset' instead of 'token'
    function depositAsset(IERC20 asset, uint256 amount) external {
        asset.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        balances[msg.sender] += amount;
    }

    /// @dev VAR2: 'underlying' instead of 'token'
    function depositUnderlying(IERC20 underlying, uint256 amount) external {
        underlying.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        balances[msg.sender] += amount;
    }

    /// @dev VAR3: 'erc20' instead of 'token'
    function depositERC20(IERC20 erc20, uint256 amount) external {
        erc20.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        balances[msg.sender] += amount;
    }

    /// @dev VAR4: 'removeFunds' instead of 'withdraw'
    function removeFunds(IERC20 token, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        token.transfer(msg.sender, amount); // ❌ No return check
    }

    /// @dev VAR5: 'authorize' instead of 'approve'
    function authorizeSpender(IERC20 token, address spender, uint256 amount) external {
        token.approve(spender, amount); // ❌ No return check
        totalSupply += amount;
    }

    /// @dev VAR6: 'addLiquidity' pattern
    function addLiquidity(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        deposits[msg.sender] += amount;
    }

    /// @dev VAR7: 'redeem' pattern
    function redeem(IERC20 token, uint256 amount) external {
        require(shares[msg.sender] >= amount, "Insufficient shares");
        shares[msg.sender] -= amount;
        token.transfer(msg.sender, amount); // ❌ No return check
    }

    /// @dev VAR8: Batch operations
    function batchDeposit(IERC20 token, address[] calldata users, uint256[] calldata amounts) external {
        for (uint256 i = 0; i < users.length; i++) {
            token.transferFrom(users[i], address(this), amounts[i]); // ❌ No return check
            balances[users[i]] += amounts[i];
        }
    }

    // =========================================================================
    // ADDITIONAL PATTERNS FOR COMPREHENSIVE COVERAGE
    // =========================================================================

    /// @dev Multi-step with unchecked transferFrom (VULNERABLE)
    function depositMultiStep(IERC20 token, uint256 amount) external {
        uint256 fee = amount / 100;
        uint256 netAmount = amount - fee;
        token.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        balances[msg.sender] += netAmount;
        balances[owner] += fee;
    }

    /// @dev Conditional transfer without check (VULNERABLE)
    function depositConditional(IERC20 token, uint256 amount, bool useStake) external {
        token.transferFrom(msg.sender, address(this), amount); // ❌ No return check
        if (useStake) {
            stakes[msg.sender] += amount;
        } else {
            balances[msg.sender] += amount;
        }
    }

    /// @dev Inline require with other condition (SAFE if return is checked)
    function depositRequireAmount(IERC20 token, uint256 amount) external {
        require(amount > 0 && token.transferFrom(msg.sender, address(this), amount), "Failed"); // ✓ Return checked
        balances[msg.sender] += amount;
    }

    /// @dev Low-level call with return check (SAFE)
    function depositLowLevel(IERC20 token, uint256 amount) external {
        (bool success, bytes memory data) = address(token).call(
            abi.encodeWithSelector(token.transferFrom.selector, msg.sender, address(this), amount)
        );
        require(success && abi.decode(data, (bool)), "Transfer failed"); // ✓ Return checked
        balances[msg.sender] += amount;
    }
}
