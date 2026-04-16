// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ApprovalRaceTest
 * @notice Test contract for token-006-approval-race-condition pattern
 *
 * Pattern: ERC20 Approval Race Condition (SWC-114)
 * Detects: Functions using approve() without increaseAllowance/decreaseAllowance
 *
 * Match Conditions:
 * - visibility: public/external
 * - uses_erc20_approve: true
 * - uses_allowance_adjust: false
 * - NOT view/pure
 * - NOT internal/private
 *
 * Test Coverage:
 * - TRUE POSITIVES: Direct approve() calls without safe allowance adjustment
 * - TRUE NEGATIVES: increaseAllowance/decreaseAllowance, SafeERC20, permit
 * - EDGE CASES: Internal helpers, view functions, conditional approvals
 * - VARIATIONS: Different function names, approval contexts
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function increaseAllowance(address spender, uint256 addedValue) external returns (bool);
    function decreaseAllowance(address spender, uint256 subtractedValue) external returns (bool);
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
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

library SafeERC20 {
    function safeApprove(IERC20 token, address spender, uint256 value) internal {
        (bool success, bytes memory data) = address(token).call(
            abi.encodeWithSelector(token.approve.selector, spender, value)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "SafeERC20: approve failed");
    }

    function safeIncreaseAllowance(IERC20 token, address spender, uint256 value) internal {
        uint256 newAllowance = token.allowance(address(this), spender) + value;
        (bool success, bytes memory data) = address(token).call(
            abi.encodeWithSelector(token.approve.selector, spender, newAllowance)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "SafeERC20: approve failed");
    }

    function safeDecreaseAllowance(IERC20 token, address spender, uint256 value) internal {
        uint256 oldAllowance = token.allowance(address(this), spender);
        require(oldAllowance >= value, "SafeERC20: decreased allowance below zero");
        uint256 newAllowance = oldAllowance - value;
        (bool success, bytes memory data) = address(token).call(
            abi.encodeWithSelector(token.approve.selector, spender, newAllowance)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "SafeERC20: approve failed");
    }
}

contract ApprovalRaceTest {
    using SafeERC20 for IERC20;

    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // =========================================================================
    // TRUE POSITIVES - Vulnerable approve() usage (should be flagged)
    // =========================================================================

    /// @notice TP1: Basic approve() without protection (VULNERABLE)
    function approveSpender(IERC20 token, address spender, uint256 amount) external {
        token.approve(spender, amount); // ❌ Race condition
    }

    /// @notice TP2: Approve in swap context (VULNERABLE)
    function swapWithApproval(IERC20 token, address router, uint256 amount) external {
        token.approve(router, amount); // ❌ Race condition
    }

    /// @notice TP3: Approve in deposit context (VULNERABLE)
    function depositWithApproval(IERC20 token, address vault, uint256 amount) external {
        token.approve(vault, amount); // ❌ Race condition
    }

    /// @notice TP4: Approve with different naming (VULNERABLE)
    function grantAllowance(IERC20 token, address spender, uint256 amount) external {
        token.approve(spender, amount); // ❌ Race condition
    }

    /// @notice TP5: Approve in staking context (VULNERABLE)
    function stakeWithApproval(IERC20 token, address stakingContract, uint256 amount) external {
        token.approve(stakingContract, amount); // ❌ Race condition
    }

    /// @notice TP6: Batch approve multiple tokens (VULNERABLE)
    function approveMultiple(IERC20[] calldata tokens, address spender, uint256 amount) external {
        for (uint256 i = 0; i < tokens.length; i++) {
            tokens[i].approve(spender, amount); // ❌ Race condition
        }
    }

    /// @notice TP7: Approve with event emission (VULNERABLE)
    function approveWithEvent(IERC20 token, address spender, uint256 amount) external {
        token.approve(spender, amount); // ❌ Race condition
        // Event would be here
    }

    /// @notice TP8: Conditional approve (VULNERABLE)
    function approveIfNeeded(IERC20 token, address spender, uint256 amount) external {
        uint256 currentAllowance = token.allowance(address(this), spender);
        if (currentAllowance < amount) {
            token.approve(spender, amount); // ❌ Race condition
        }
    }

    /// @notice TP9: Approve in constructor (VULNERABLE - public callable)
    function initialize(IERC20 token, address router) external {
        token.approve(router, type(uint256).max); // ❌ Race condition
    }

    /// @notice TP10: Approve for lending protocol (VULNERABLE)
    function approveLendingPool(IERC20 token, address pool, uint256 amount) external {
        token.approve(pool, amount); // ❌ Race condition
    }

    /// @notice TP11: Approve different naming variation (VULNERABLE)
    function authorizeSpender(IERC20 token, address spender, uint256 limit) external {
        token.approve(spender, limit); // ❌ Race condition
    }

    /// @notice TP12: Approve in AMM context (VULNERABLE)
    function addLiquidityWithApproval(IERC20 token, address amm, uint256 amount) external {
        token.approve(amm, amount); // ❌ Race condition
    }

    // =========================================================================
    // TRUE NEGATIVES - Safe patterns (should NOT be flagged)
    // =========================================================================

    /// @notice TN1: Use increaseAllowance (SAFE)
    function increaseSpenderAllowance(IERC20 token, address spender, uint256 addedAmount) external {
        token.increaseAllowance(spender, addedAmount); // ✓ Safe
    }

    /// @notice TN2: Use decreaseAllowance (SAFE)
    function decreaseSpenderAllowance(IERC20 token, address spender, uint256 subtractedAmount) external {
        token.decreaseAllowance(spender, subtractedAmount); // ✓ Safe
    }

    /// @notice TN3: Use SafeERC20 safeApprove (SAFE)
    function approveSafe(IERC20 token, address spender, uint256 amount) external {
        token.safeApprove(spender, amount); // ✓ SafeERC20 handles it
    }

    /// @notice TN4: Use SafeERC20 safeIncreaseAllowance (SAFE)
    function increaseAllowanceSafe(IERC20 token, address spender, uint256 amount) external {
        token.safeIncreaseAllowance(spender, amount); // ✓ Safe
    }

    /// @notice TN5: Use SafeERC20 safeDecreaseAllowance (SAFE)
    function decreaseAllowanceSafe(IERC20 token, address spender, uint256 amount) external {
        token.safeDecreaseAllowance(spender, amount); // ✓ Safe
    }

    /// @notice TN6: Use EIP-2612 permit (SAFE)
    function depositWithPermit(
        IERC20Permit token,
        uint256 amount,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        // No approve() call - uses permit signature
        token.permit(msg.sender, address(this), amount, deadline, v, r, s); // ✓ Safe
        token.transferFrom(msg.sender, address(this), amount);
    }

    /// @notice TN7: View function reading allowance (SAFE - view)
    function getAllowance(IERC20 token, address owner, address spender) external view returns (uint256) {
        return token.allowance(owner, spender); // ✓ View function
    }

    /// @notice TN8: Pure calculation function (SAFE - pure)
    function calculateApprovalAmount(uint256 amount, uint256 fee) external pure returns (uint256) {
        return amount + fee; // ✓ Pure function
    }

    /// @notice TN9: Internal approve helper (SAFE - internal not exploitable)
    function _approveInternal(IERC20 token, address spender, uint256 amount) internal {
        token.approve(spender, amount); // ✓ Internal - not externally callable
    }

    /// @notice TN10: Private approve helper (SAFE - private not exploitable)
    function _approvePrivate(IERC20 token, address spender, uint256 amount) private {
        token.approve(spender, amount); // ✓ Private - not externally callable
    }

    /// @notice TN11: Revoke approval by setting to zero (SAFE - security function)
    function revokeApproval(IERC20 token, address spender) external {
        token.approve(spender, 0); // ✓ Setting to zero (revocation)
    }

    /// @notice TN12: Batch increase allowances (SAFE)
    function increaseMultipleAllowances(IERC20 token, address[] calldata spenders, uint256 amount) external {
        for (uint256 i = 0; i < spenders.length; i++) {
            token.increaseAllowance(spenders[i], amount); // ✓ Safe
        }
    }

    // =========================================================================
    // EDGE CASES - Boundary conditions and special scenarios
    // =========================================================================

    /// @notice EDGE1: Approve with ownership check (still VULNERABLE but gated)
    function approveAsOwner(IERC20 token, address spender, uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        token.approve(spender, amount); // ❌ Still has race condition
    }

    /// @notice EDGE2: Approve in emergency function (VULNERABLE)
    function emergencyApprove(IERC20 token, address spender, uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        token.approve(spender, amount); // ❌ Race condition
    }

    /// @notice EDGE3: Two-step approval pattern (FALSE POSITIVE - VKG limitation)
    /// This implements the two-step zero reset pattern but VKG cannot detect it
    function changeApprovalSafe(IERC20 token, address spender, uint256 newAmount) external {
        // Step 1: Reset to zero
        token.approve(spender, 0);
        // Step 2: Set new amount
        token.approve(spender, newAmount); // ❌ VKG will flag this (known limitation)
    }

    /// @notice EDGE4: Approve only if current is zero (FALSE POSITIVE)
    function approveIfZero(IERC20 token, address spender, uint256 amount) external {
        uint256 current = token.allowance(address(this), spender);
        require(current == 0, "Must revoke first");
        token.approve(spender, amount); // ❌ VKG will flag (limitation)
    }

    /// @notice EDGE5: Self-approval (unusual but VULNERABLE)
    function approveSelf(IERC20 token, uint256 amount) external {
        token.approve(address(this), amount); // ❌ Race condition
    }

    /// @notice EDGE6: Approve with zero address check (still VULNERABLE)
    function approveWithCheck(IERC20 token, address spender, uint256 amount) external {
        require(spender != address(0), "Invalid spender");
        token.approve(spender, amount); // ❌ Race condition
    }

    // =========================================================================
    // VARIATIONS - Different naming conventions and contexts
    // =========================================================================

    /// @notice VAR1: updateAllowance naming (VULNERABLE)
    function updateAllowance(IERC20 token, address spender, uint256 amount) public {
        token.approve(spender, amount); // ❌ Race condition
    }

    /// @notice VAR2: setApproval naming (VULNERABLE)
    function setApproval(IERC20 token, address spender, uint256 amount) public {
        token.approve(spender, amount); // ❌ Race condition
    }

    /// @notice VAR3: configureAllowance naming (VULNERABLE)
    function configureAllowance(IERC20 token, address target, uint256 limit) public {
        token.approve(target, limit); // ❌ Race condition
    }

    /// @notice VAR4: increaseApprovalSafe - uses increaseAllowance (SAFE)
    function increaseApprovalSafe(IERC20 token, address spender, uint256 delta) public {
        token.increaseAllowance(spender, delta); // ✓ Safe
    }

    /// @notice VAR5: decreaseApprovalSafe - uses decreaseAllowance (SAFE)
    function decreaseApprovalSafe(IERC20 token, address spender, uint256 delta) public {
        token.decreaseAllowance(spender, delta); // ✓ Safe
    }

    /// @notice VAR6: Approve in bridge context (VULNERABLE)
    function bridgeApprove(IERC20 token, address bridge, uint256 amount) public {
        token.approve(bridge, amount); // ❌ Race condition
    }

    // =========================================================================
    // FALSE POSITIVE SCENARIOS (Pattern limitations)
    // =========================================================================

    /// @notice FP1: Two-step reset pattern in single transaction
    /// VKG cannot detect this safe pattern, will flag as vulnerable
    function changeApprovalTwoStep(IERC20 token, address spender, uint256 newAmount) external {
        uint256 current = token.allowance(address(this), spender);
        if (current > 0) {
            token.approve(spender, 0); // Reset to zero
        }
        token.approve(spender, newAmount); // ❌ Will be flagged (FP)
    }

    /// @notice FP2: Initial approval only (no change)
    /// Lower risk but VKG cannot distinguish from changing approvals
    function setInitialApproval(IERC20 token, address spender, uint256 amount) external {
        uint256 current = token.allowance(address(this), spender);
        require(current == 0, "Already approved");
        token.approve(spender, amount); // ❌ Will be flagged (FP - lower risk)
    }

    /// @notice FP3: Approve trusted immutable contract
    /// VKG cannot assess spender trust level
    function approveTrustedContract(IERC20 token, address trustedContract, uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        // Assume trustedContract is audited, immutable
        token.approve(trustedContract, amount); // ❌ Will be flagged (FP if trusted)
    }
}
