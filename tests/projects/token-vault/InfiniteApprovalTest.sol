// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
}

interface IERC20Permit {
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external;
}

/**
 * @title InfiniteApprovalTest
 * @notice Test contract for token-003-infinite-approval pattern
 *
 * This contract tests detection of functions that approve infinite/maximum
 * token allowances (type(uint256).max) versus limited approvals.
 *
 * Pattern Detection: uses_erc20_approve = true (any approve() call)
 *
 * LIMITATION: Currently detects ALL approve() usage, not just infinite approvals.
 * Future enhancement needed: approves_infinite_amount property to distinguish
 * between infinite and limited approvals.
 */
contract InfiniteApprovalTest {
    IERC20 public token;
    address public stakingContract;

    // =========================================================================
    // TRUE POSITIVES - Functions that approve tokens (will flag ALL approves)
    // =========================================================================

    /**
     * TP1: Standard infinite approval pattern
     * Uses type(uint256).max for gas efficiency
     */
    function approveInfinite(IERC20 _token, address spender) external {
        _token.approve(spender, type(uint256).max);
    }

    /**
     * TP2: Hardcoded max value (literal hex)
     * Same as type(uint256).max but using hex notation
     */
    function approveMaxHex(IERC20 _token, address spender) external {
        _token.approve(spender, 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff);
    }

    /**
     * TP3: Hardcoded max value (arithmetic)
     * 2^256 - 1
     */
    function approveMaxArithmetic(IERC20 _token, address spender) external {
        uint256 maxValue = 2**256 - 1;
        _token.approve(spender, maxValue);
    }

    /**
     * TP4: Stake function with infinite approval
     * Common DeFi pattern - approve once, use forever
     */
    function stakeWithInfiniteApproval(IERC20 _token, uint256 amount) external {
        // First time: infinite approval (saves gas on future stakes)
        uint256 currentAllowance = _token.allowance(msg.sender, address(stakingContract));
        if (currentAllowance < amount) {
            _token.approve(address(stakingContract), type(uint256).max);
        }
        // stakingContract.deposit(_token, amount);
    }

    /**
     * TP5: Swap function with infinite approval
     * DEX aggregator pattern
     */
    function swapWithInfiniteApproval(
        IERC20 tokenIn,
        address router,
        uint256 amountIn
    ) external {
        tokenIn.approve(router, type(uint256).max);
        // router.swap(tokenIn, tokenOut, amountIn);
    }

    /**
     * TP6: Multi-token infinite approval
     * Approve multiple tokens to same spender
     */
    function approveMultipleTokens(
        IERC20[] calldata tokens,
        address spender
    ) external {
        for (uint256 i = 0; i < tokens.length; i++) {
            tokens[i].approve(spender, type(uint256).max);
        }
    }

    /**
     * TP7: Approve with fallback check
     * Checks allowance and only approves if needed
     */
    function approveIfNeeded(
        IERC20 _token,
        address spender,
        uint256 needed
    ) external {
        if (_token.allowance(address(this), spender) < needed) {
            _token.approve(spender, type(uint256).max);
        }
    }

    /**
     * TP8: Approve in constructor
     * One-time infinite approval during deployment
     */
    constructor(IERC20 _token, address _stakingContract) {
        token = _token;
        stakingContract = _stakingContract;
        _token.approve(_stakingContract, type(uint256).max);
    }

    // =========================================================================
    // FP (Will Flag But Limited Approval) - Pattern limitation
    // =========================================================================

    /**
     * FP1: Limited approval (exact amount)
     * LIMITATION: Pattern will flag this even though it's SAFE
     * Uses exact amount, not infinite
     */
    function approveLimited(IERC20 _token, address spender, uint256 amount) external {
        _token.approve(spender, amount);
    }

    /**
     * FP2: Stake with limited approval
     * LIMITATION: Pattern will flag this even though it's SAFE
     * Approves only what's needed
     */
    function stakeSafe(IERC20 _token, uint256 amount) external {
        _token.approve(address(stakingContract), amount);
        // stakingContract.deposit(_token, amount);
    }

    /**
     * FP3: Approve with reset to zero
     * LIMITATION: Pattern will flag this even though it's SAFE
     * Resets approval after use
     */
    function approveAndReset(
        IERC20 _token,
        address spender,
        uint256 amount
    ) external {
        _token.approve(spender, amount);
        // spender.doSomething();
        _token.approve(spender, 0);
    }

    /**
     * FP4: Incremental approval top-up
     * LIMITATION: Pattern will flag this even though it's SAFE
     * Only adds what's needed to existing allowance
     */
    function topUpApproval(
        IERC20 _token,
        address spender,
        uint256 needed
    ) external {
        uint256 currentAllowance = _token.allowance(address(this), spender);
        if (currentAllowance < needed) {
            uint256 additionalAllowance = needed - currentAllowance;
            _token.approve(spender, currentAllowance + additionalAllowance);
        }
    }

    /**
     * FP5: Swap with exact approval
     * LIMITATION: Pattern will flag this even though it's SAFE
     * Approves exact amount for swap
     */
    function swapSafe(
        IERC20 tokenIn,
        address router,
        uint256 amountIn
    ) external {
        tokenIn.approve(router, amountIn);
        // router.swap(tokenIn, tokenOut, amountIn);
    }

    /**
     * FP6: Time-limited approval (custom implementation)
     * LIMITATION: Pattern will flag this even though it's SAFE
     * Concept: would track expiry in separate storage
     */
    function approveWithExpiry(
        IERC20 _token,
        address spender,
        uint256 amount,
        uint256 /* duration */
    ) external {
        // In real implementation, would store expiry timestamp
        _token.approve(spender, amount);
    }

    /**
     * FP7: Revoke approval (set to zero)
     * LIMITATION: Pattern will flag this even though it's SAFE
     * Used to cancel previous infinite approval
     */
    function revokeApproval(IERC20 _token, address spender) external {
        _token.approve(spender, 0);
    }

    /**
     * FP8: Approve small test amount
     * LIMITATION: Pattern will flag this even though it's SAFE
     */
    function approveSmall(IERC20 _token, address spender) external {
        _token.approve(spender, 1 ether);
    }

    // =========================================================================
    // TRUE NEGATIVES - Safe patterns (should NOT flag)
    // =========================================================================

    /**
     * TN1: ERC20Permit - Just-in-time approval via signature
     * Does NOT call approve(), uses permit() instead
     */
    function stakeWithPermit(
        IERC20Permit _token,
        uint256 amount,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // Permit grants exact approval amount and expires at deadline
        _token.permit(msg.sender, address(this), amount, deadline, v, r, s);
        // Transfer tokens (uses the just-granted approval)
        IERC20(address(_token)).transferFrom(msg.sender, address(this), amount);
    }

    /**
     * TN2: Direct transfer (no approval needed)
     * Uses transfer() instead of approve()
     */
    function depositDirect(IERC20 _token, uint256 amount) external {
        _token.transferFrom(msg.sender, address(this), amount);
    }

    /**
     * TN3: View function - query allowance
     * Only reads, doesn't write approval
     */
    function getAllowance(
        IERC20 _token,
        address owner,
        address spender
    ) external view returns (uint256) {
        return _token.allowance(owner, spender);
    }

    /**
     * TN4: Pure function - calculate amount
     * No token interaction
     */
    function calculateAmount(uint256 amount, uint256 rate)
        external
        pure
        returns (uint256)
    {
        return (amount * rate) / 1000;
    }

    /**
     * TN5: Internal function
     * Not externally callable
     */
    function _approveInternal(
        IERC20 _token,
        address spender,
        uint256 amount
    ) internal {
        _token.approve(spender, amount);
    }

    /**
     * TN6: Private function
     * Not externally callable
     */
    function _approvePrivate(
        IERC20 _token,
        address spender,
        uint256 amount
    ) private {
        _token.approve(spender, amount);
    }

    // =========================================================================
    // EDGE CASES
    // =========================================================================

    /**
     * EDGE1: Approve self
     * Unusual pattern - approving contract to spend its own tokens
     */
    function approveSelf(IERC20 _token, uint256 amount) external {
        _token.approve(address(this), amount);
    }

    /**
     * EDGE2: Approve to zero address
     * Should fail but tests pattern detection
     */
    function approveToZero(IERC20 _token, uint256 amount) external {
        _token.approve(address(0), amount);
    }

    /**
     * EDGE3: Conditional approve
     * Only approves under certain conditions
     */
    function approveConditional(
        IERC20 _token,
        address spender,
        uint256 amount,
        bool shouldApprove
    ) external {
        if (shouldApprove) {
            _token.approve(spender, amount);
        }
    }

    /**
     * EDGE4: Emergency approval removal
     * Batch revoke approvals (security function)
     */
    function emergencyRevokeAll(IERC20[] calldata tokens, address spender)
        external
    {
        for (uint256 i = 0; i < tokens.length; i++) {
            tokens[i].approve(spender, 0);
        }
    }

    // =========================================================================
    // VARIATIONS - Different naming conventions
    // =========================================================================

    /**
     * VAR1: Function named 'grantAllowance' instead of 'approve'
     * Still calls approve() internally
     */
    function grantAllowance(IERC20 asset, address recipient) external {
        asset.approve(recipient, type(uint256).max);
    }

    /**
     * VAR2: Function named 'authorizeSpender'
     */
    function authorizeSpender(IERC20 currency, address spender) external {
        currency.approve(spender, type(uint256).max);
    }

    /**
     * VAR3: Parameter named 'underlying' instead of 'token'
     */
    function approveUnderlying(IERC20 underlying, address spender) external {
        underlying.approve(spender, type(uint256).max);
    }

    /**
     * VAR4: Parameter named 'asset'
     */
    function approveAsset(IERC20 asset, address target) external {
        asset.approve(target, type(uint256).max);
    }

    /**
     * VAR5: Parameter named 'erc20'
     */
    function approveERC20(IERC20 erc20, address destination) external {
        erc20.approve(destination, type(uint256).max);
    }

    /**
     * VAR6: Spender named 'contract' instead of 'spender'
     */
    function approveContract(IERC20 _token, address contractAddress) external {
        _token.approve(contractAddress, type(uint256).max);
    }

    /**
     * VAR7: Spender named 'router'
     */
    function approveRouter(IERC20 _token, address router) external {
        _token.approve(router, type(uint256).max);
    }

    /**
     * VAR8: Different max value representation
     * Using negation of zero
     */
    function approveMaxNegation(IERC20 _token, address spender) external {
        uint256 maxUint = ~uint256(0);
        _token.approve(spender, maxUint);
    }
}
