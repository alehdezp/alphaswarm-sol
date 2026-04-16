// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// =============================================================================
// TEST CONTRACT: token-004-non-standard-return
// Non-Standard ERC20 Return Value Detection
// =============================================================================
//
// This contract tests detection of functions that call ERC20 transfer/transferFrom
// without properly handling non-standard token return values (USDT, BNB, OMG).
//
// Pattern: token-004-non-standard-return
// Expected Properties:
//   - visibility: [public, external]
//   - writes_balance_state: true
//   - uses_erc20_transfer OR uses_erc20_transfer_from: true
//   - token_return_guarded: false
//   - uses_safe_erc20: false
//
// =============================================================================

// Minimal IERC20 interface for testing
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

// Minimal SafeERC20 library interface for testing
library SafeERC20 {
    function safeTransfer(IERC20 token, address to, uint256 value) internal {
        // Implementation not needed for pattern detection
    }

    function safeTransferFrom(IERC20 token, address from, address to, uint256 value) internal {
        // Implementation not needed for pattern detection
    }
}

contract NonStandardReturnTest {
    using SafeERC20 for IERC20;

    mapping(address => uint256) public balances;
    mapping(address => uint256) public deposits;
    mapping(address => uint256) public shares;
    mapping(address => uint256) public stakes;
    mapping(address => uint256) public userShares;

    // =============================================================================
    // TRUE POSITIVES - Should be flagged by token-004
    // =============================================================================

    // TP1: Direct transfer without return check
    // VULNERABLE: Uses transfer() without SafeERC20, writes balances
    function deposit(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    // TP2: Direct transferFrom without return check (different naming)
    // VULNERABLE: Uses transferFrom() without SafeERC20, writes deposits
    function addFunds(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        deposits[msg.sender] += amount;
    }

    // TP3: Outbound transfer without return check
    // VULNERABLE: Uses transfer() without SafeERC20, writes balances
    function withdraw(IERC20 token, uint256 amount) external {
        balances[msg.sender] -= amount;
        token.transfer(msg.sender, amount);
    }

    // TP4: Two-step deposit pattern
    // VULNERABLE: Uses transferFrom() without SafeERC20, writes shares
    function depositForShares(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        uint256 shareAmount = amount * 100;
        shares[msg.sender] += shareAmount;
    }

    // TP5: Multi-step with event emission
    // VULNERABLE: Uses transferFrom() without SafeERC20, writes balances
    function depositWithEvent(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
        emit Deposit(msg.sender, amount);
    }

    // TP6: Staking with transfer
    // VULNERABLE: Uses transferFrom() without SafeERC20, writes stakes
    function stake(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        stakes[msg.sender] += amount;
    }

    // TP7: Deposit to different mapping name
    // VULNERABLE: Uses transferFrom() without SafeERC20, writes userShares
    function depositAssets(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        userShares[msg.sender] += amount;
    }

    // TP8: Batch transfer pattern
    // VULNERABLE: Uses transfer() in loop without SafeERC20, writes balances
    function batchWithdraw(IERC20 token, address[] calldata recipients, uint256[] calldata amounts) external {
        for (uint256 i = 0; i < recipients.length; i++) {
            balances[recipients[i]] -= amounts[i];
            token.transfer(recipients[i], amounts[i]);
        }
    }

    // TP9: Withdrawal with different state variable
    // VULNERABLE: Uses transfer() without SafeERC20, writes deposits
    function withdrawDeposit(IERC20 token, uint256 amount) external {
        deposits[msg.sender] -= amount;
        token.transfer(msg.sender, amount);
    }

    // TP10: Collateral deposit
    // VULNERABLE: Uses transferFrom() without SafeERC20, writes balances
    function depositCollateral(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    // =============================================================================
    // TRUE NEGATIVES - Should NOT be flagged (Safe implementations)
    // =============================================================================

    // TN1: Uses SafeERC20.safeTransferFrom
    // SAFE: SafeERC20 handles non-standard returns
    function depositSafe(IERC20 token, uint256 amount) external {
        token.safeTransferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    // TN2: Uses SafeERC20.safeTransfer
    // SAFE: SafeERC20 handles non-standard returns
    function withdrawSafe(IERC20 token, uint256 amount) external {
        balances[msg.sender] -= amount;
        token.safeTransfer(msg.sender, amount);
    }

    // TN3: Manual return value check with require
    // SAFE: Explicitly checks return value (though still fails with USDT)
    function depositWithCheck(IERC20 token, uint256 amount) external {
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        balances[msg.sender] += amount;
    }

    // TN4: SafeERC20 in staking
    // SAFE: SafeERC20 handles non-standard returns
    function stakeSafe(IERC20 token, uint256 amount) external {
        token.safeTransferFrom(msg.sender, address(this), amount);
        stakes[msg.sender] += amount;
    }

    // TN5: SafeERC20 batch withdrawal
    // SAFE: SafeERC20 handles non-standard returns
    function batchWithdrawSafe(IERC20 token, address[] calldata recipients, uint256[] calldata amounts) external {
        for (uint256 i = 0; i < recipients.length; i++) {
            balances[recipients[i]] -= amounts[i];
            token.safeTransfer(recipients[i], amounts[i]);
        }
    }

    // TN6: Manual return check with if-revert
    // SAFE: Captures and validates return value
    function withdrawWithManualCheck(IERC20 token, uint256 amount) external {
        balances[msg.sender] -= amount;
        bool success = token.transfer(msg.sender, amount);
        require(success, "Transfer failed");
    }

    // TN7: SafeERC20 for collateral
    // SAFE: SafeERC20 handles non-standard returns
    function depositCollateralSafe(IERC20 token, uint256 amount) external {
        token.safeTransferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    // =============================================================================
    // EDGE CASES - Should NOT be flagged (different reasons)
    // =============================================================================

    // EDGE1: Internal function (not external/public)
    // Should NOT flag: visibility is internal
    function _depositInternal(IERC20 token, uint256 amount) internal {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    // EDGE2: Private function
    // Should NOT flag: visibility is private
    function _depositPrivate(IERC20 token, uint256 amount) private {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    // EDGE3: View function (no state write)
    // Should NOT flag: state_mutability is view
    function viewBalance(address user) external view returns (uint256) {
        return balances[user];
    }

    // EDGE4: Pure function
    // Should NOT flag: state_mutability is pure
    function calculateAmount(uint256 amount, uint256 rate) external pure returns (uint256) {
        return amount * rate / 100;
    }

    // EDGE5: Transfer without balance write
    // Should NOT flag: writes_balance_state is false
    function transferNoAccounting(IERC20 token, address to, uint256 amount) external {
        token.transfer(to, amount);
    }

    // EDGE6: Balance write without transfer
    // Should NOT flag: uses_erc20_transfer is false
    function updateBalanceNoTransfer(address user, uint256 amount) external {
        balances[user] += amount;
    }

    // EDGE7: Deposit with no ERC20 call (ETH deposit)
    // Should NOT flag: uses_erc20_transfer_from is false
    function depositETH() external payable {
        balances[msg.sender] += msg.value;
    }

    // EDGE8: Low-level call with return check (alternative safe pattern)
    // Should NOT flag: token_return_guarded should be true
    function depositLowLevel(IERC20 token, uint256 amount) external {
        (bool success, bytes memory returndata) = address(token).call(
            abi.encodeWithSelector(token.transferFrom.selector, msg.sender, address(this), amount)
        );
        require(success, "Transfer failed");
        if (returndata.length > 0) {
            require(abi.decode(returndata, (bool)), "Transfer returned false");
        }
        balances[msg.sender] += amount;
    }

    // =============================================================================
    // VARIATION TESTS - Different naming conventions
    // =============================================================================

    // VAR1: Contribute instead of deposit
    // VULNERABLE: Different naming, same vulnerability
    function contribute(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    // VAR2: Fund instead of deposit
    // VULNERABLE: Different naming, same vulnerability
    function fund(IERC20 token, uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        deposits[msg.sender] += amount;
    }

    // VAR3: Claim instead of withdraw
    // VULNERABLE: Different naming, same vulnerability
    function claim(IERC20 token, uint256 amount) external {
        balances[msg.sender] -= amount;
        token.transfer(msg.sender, amount);
    }

    // VAR4: Redeem instead of withdraw
    // VULNERABLE: Different naming, same vulnerability
    function redeem(IERC20 token, uint256 amount) external {
        shares[msg.sender] -= amount;
        token.transfer(msg.sender, amount);
    }

    // VAR5: Token parameter named 'asset'
    // VULNERABLE: Different parameter naming
    function depositAsset(IERC20 asset, uint256 amount) external {
        asset.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    // VAR6: Token parameter named 'underlying'
    // VULNERABLE: Different parameter naming
    function depositUnderlying(IERC20 underlying, uint256 amount) external {
        underlying.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    // Events
    event Deposit(address indexed user, uint256 amount);
}
