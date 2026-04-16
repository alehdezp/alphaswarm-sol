// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ERC777ReentrancyTest
 * @notice Test contract for token-002-erc777-reentrancy pattern
 *
 * Pattern: token-002-erc777-reentrancy
 * Detects: Functions using ERC-777 send/operatorSend that write state AFTER transfer
 *
 * ERC-777 Reentrancy: ERC-777 tokens call tokensReceived() or tokensToSend() hooks
 * DURING the transfer, allowing callback reentrancy before state is updated.
 *
 * Real Exploits:
 * - Lendf.Me (April 2020): $25M loss via imBTC (ERC-777) reentrancy
 * - dForce (April 2020): $25M loss, same attack vector
 * - Uniswap V1 + imBTC: $300K loss
 *
 * Test Coverage:
 * - TRUE POSITIVES: ERC-777 send WITHOUT reentrancy guard + state write after
 * - TRUE NEGATIVES: WITH reentrancy guard OR CEI pattern OR ERC-20 only
 * - EDGE CASES: Internal functions, view functions, no state write
 * - VARIATIONS: Different function names, token operations, state patterns
 */

// Minimal ERC-777 interface for testing
interface IERC777 {
    function send(address recipient, uint256 amount, bytes memory data) external;
    function operatorSend(
        address sender,
        address recipient,
        uint256 amount,
        bytes memory data,
        bytes memory operatorData
    ) external;
    function burn(uint256 amount, bytes memory data) external;
}

contract ERC777ReentrancyTest {

    // State variables
    mapping(address => uint256) public balances;
    mapping(address => uint256) public shares;
    mapping(address => uint256) public deposits;
    mapping(address => uint256) public stakes;

    IERC777 public token;
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "No reentrancy");
        locked = true;
        _;
        locked = false;
    }

    modifier onlyOwner() {
        require(msg.sender == address(0x123), "Not owner");
        _;
    }

    // =========================================================================
    // TRUE POSITIVES - Should be flagged as vulnerable
    // =========================================================================

    /**
     * TP1: Standard vulnerable withdraw using ERC-777 send
     * CEI VIOLATION: send() BEFORE balances update
     * Pattern should flag: uses_erc777_send + state_write_after_external_call + no guard
     */
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE: ERC-777 send triggers tokensReceived() callback BEFORE state update
        token.send(msg.sender, amount, "");
        // State write AFTER external call (CEI violation)
        balances[msg.sender] -= amount;
    }

    /**
     * TP2: Variation - redeem with ERC-777
     * Different function name, same vulnerability
     */
    function redeem(uint256 amount) external {
        require(shares[msg.sender] >= amount, "Insufficient shares");
        // VULNERABLE: send before state update
        token.send(msg.sender, amount, "");
        shares[msg.sender] -= amount;
    }

    /**
     * TP3: Variation - unstake with ERC-777
     * Uses stakes mapping instead of balances
     */
    function unstake(uint256 amount) external {
        require(stakes[msg.sender] >= amount, "Insufficient stake");
        // VULNERABLE
        token.send(msg.sender, amount, "");
        stakes[msg.sender] -= amount;
    }

    /**
     * TP4: Variation - claim with ERC-777
     * Reads and writes deposits mapping
     */
    function claim() external {
        uint256 amount = deposits[msg.sender];
        require(amount > 0, "Nothing to claim");
        // VULNERABLE
        token.send(msg.sender, amount, "");
        deposits[msg.sender] = 0;
    }

    /**
     * TP5: operatorSend variation (triggers tokensToSend hook)
     * Uses ERC-777 operatorSend instead of send
     */
    function withdrawViaOperator(address recipient, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE: operatorSend triggers tokensToSend() callback
        token.operatorSend(address(this), recipient, amount, "", "");
        balances[msg.sender] -= amount;
    }

    /**
     * TP6: Multi-step withdrawal with ERC-777
     * Intermediate variable doesn't prevent reentrancy
     */
    function withdrawMultiStep(uint256 amount) external {
        uint256 userBalance = balances[msg.sender];
        require(userBalance >= amount, "Insufficient balance");
        // VULNERABLE
        token.send(msg.sender, amount, "");
        balances[msg.sender] = userBalance - amount;
    }

    /**
     * TP7: Withdraw with event emission
     * Event doesn't prevent reentrancy
     */
    function withdrawWithEvent(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE
        token.send(msg.sender, amount, "");
        balances[msg.sender] -= amount;
        // Event after (doesn't help)
    }

    /**
     * TP8: Cross-mapping withdrawal
     * Writes to different mapping but still vulnerable
     */
    function withdrawToShares(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE
        token.send(msg.sender, amount, "");
        shares[msg.sender] += amount;  // Different mapping, still state write after
    }

    // =========================================================================
    // TRUE NEGATIVES - Safe patterns that should NOT be flagged
    // =========================================================================

    /**
     * TN1: Withdraw with reentrancy guard
     * nonReentrant modifier prevents callback reentrancy
     */
    function withdrawProtected(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // Safe: nonReentrant prevents reentrancy even with CEI violation
        token.send(msg.sender, amount, "");
        balances[msg.sender] -= amount;
    }

    /**
     * TN2: Withdraw following CEI pattern
     * State update BEFORE external call (safe ordering)
     */
    function withdrawCEI(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // State update FIRST (Checks-Effects-Interactions)
        balances[msg.sender] -= amount;
        // External call AFTER (safe)
        token.send(msg.sender, amount, "");
    }

    /**
     * TN3: Withdraw with both guard AND CEI
     * Defense in depth: guard + proper ordering
     */
    function withdrawFullySafe(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;  // CEI pattern
        token.send(msg.sender, amount, "");  // Guard protects
    }

    /**
     * TN4: View function (no state changes)
     * Should NOT be flagged - state_mutability=view
     */
    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }

    /**
     * TN5: Pure function (no state access)
     * Should NOT be flagged - state_mutability=pure
     */
    function calculateAmount(uint256 userShares, uint256 rate) external pure returns (uint256) {
        return userShares * rate / 1e18;
    }

    /**
     * TN6: Internal function (not externally callable)
     * Should NOT be flagged - visibility=internal
     */
    function _withdrawInternal(address user, uint256 amount) internal {
        token.send(user, amount, "");
        balances[user] -= amount;
    }

    /**
     * TN7: Private function (not externally callable)
     * Should NOT be flagged - visibility=private
     */
    function _withdrawPrivate(address user, uint256 amount) private {
        token.send(user, amount, "");
        balances[user] -= amount;
    }

    /**
     * TN8: Owner-only function with guard
     * Access control + reentrancy guard
     */
    function emergencyWithdraw(address user, uint256 amount) external onlyOwner nonReentrant {
        token.send(user, amount, "");
        balances[user] -= amount;
    }

    // =========================================================================
    // EDGE CASES - Boundary conditions
    // =========================================================================

    /**
     * EDGE1: ERC-777 send without balance write
     * Uses ERC-777 but doesn't write state (no accounting impact)
     * Should NOT be flagged - writes_balance_state=false
     */
    function sendTokensNoAccounting(address recipient, uint256 amount) external {
        // ERC-777 send but no state write (just forwarding)
        token.send(recipient, amount, "");
        // No balance update - not a reentrancy risk for accounting
    }

    /**
     * EDGE2: State write without ERC-777
     * Writes state but doesn't use ERC-777 operations
     * Should NOT be flagged - uses_erc777_send=false
     */
    function updateBalanceNoTransfer(address user, uint256 amount) external {
        // State write but no ERC-777 transfer
        balances[user] = amount;
        // No external call - not a token reentrancy issue
    }

    /**
     * EDGE3: Constructor (special visibility)
     * Should NOT be flagged - not a regular function
     */
    constructor(address _token) {
        token = IERC777(_token);
    }

    /**
     * EDGE4: Receive function for ETH
     * Should NOT be flagged - not related to ERC-777
     */
    receive() external payable {
        // Receive ETH, not related to ERC-777 tokens
    }

    /**
     * EDGE5: Burn instead of send
     * ERC-777 burn() also triggers callbacks (tokensToSend hook)
     * VULNERABLE if state write after
     */
    function burnTokens(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE: burn() triggers tokensToSend() callback
        token.burn(amount, "");
        balances[msg.sender] -= amount;
    }

    // =========================================================================
    // VARIATIONS - Different implementation patterns
    // =========================================================================

    /**
     * VAR1: Different token parameter name (erc777Token)
     * Pattern must be implementation-agnostic
     */
    function withdrawFromVault(uint256 amount) external {
        IERC777 erc777Token = token;  // Different variable name
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE
        erc777Token.send(msg.sender, amount, "");
        balances[msg.sender] -= amount;
    }

    /**
     * VAR2: Inline token reference
     * No intermediate variable
     */
    function withdrawDirect(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE: direct state variable reference
        token.send(msg.sender, amount, "");
        balances[msg.sender] -= amount;
    }

    /**
     * VAR3: Two-step state update
     * State update split across lines but still after call
     */
    function withdrawTwoStep(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE
        token.send(msg.sender, amount, "");
        uint256 newBalance = balances[msg.sender] - amount;
        balances[msg.sender] = newBalance;
    }

    /**
     * VAR4: State update via operator
     * Uses -= operator
     */
    function withdrawWithOperator(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE
        token.send(msg.sender, amount, "");
        balances[msg.sender] -= amount;
    }

    /**
     * VAR5: State update via assignment
     * Uses = operator instead of -=
     */
    function withdrawWithAssignment(uint256 amount) external {
        uint256 currentBalance = balances[msg.sender];
        require(currentBalance >= amount, "Insufficient balance");
        // VULNERABLE
        token.send(msg.sender, amount, "");
        balances[msg.sender] = currentBalance - amount;
    }

    /**
     * VAR6: Transfer to different recipient
     * Recipient is function parameter, not msg.sender
     */
    function withdrawTo(address recipient, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE: callback can re-enter even with different recipient
        token.send(recipient, amount, "");
        balances[msg.sender] -= amount;
    }

    /**
     * VAR7: operatorSend with custom data
     * Uses operatorSend with custom data parameters
     */
    function operatorWithdraw(address recipient, uint256 amount, bytes memory data) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // VULNERABLE
        token.operatorSend(address(this), recipient, amount, data, "operator");
        balances[msg.sender] -= amount;
    }

    /**
     * VAR8: Conditional withdrawal
     * Has require checks but still vulnerable
     */
    function withdrawConditional(uint256 amount) external {
        require(amount > 0, "Zero amount");
        require(balances[msg.sender] >= amount, "Insufficient balance");
        require(msg.sender != address(0), "Zero address");
        // VULNERABLE despite multiple checks
        token.send(msg.sender, amount, "");
        balances[msg.sender] -= amount;
    }

    // =========================================================================
    // ADDITIONAL SAFE PATTERNS
    // =========================================================================

    /**
     * SAFE1: Pull payment pattern (two-step withdrawal)
     * Step 1: Mark available for withdrawal (no external call)
     */
    mapping(address => uint256) public pendingWithdrawals;

    function requestWithdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // State update first (no external call yet)
        balances[msg.sender] -= amount;
        pendingWithdrawals[msg.sender] += amount;
    }

    /**
     * SAFE2: Pull payment step 2 (separate transaction)
     * Should NOT be flagged - uses separate state
     */
    function claimWithdrawal() external nonReentrant {
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "Nothing to claim");
        pendingWithdrawals[msg.sender] = 0;  // Clear first
        token.send(msg.sender, amount, "");  // Then send
    }

    // SAFE3: Manual mutex lock pattern
    // Custom reentrancy protection
    bool private customLock;

    function withdrawWithCustomLock(uint256 amount) external {
        require(!customLock, "Locked");
        customLock = true;

        require(balances[msg.sender] >= amount, "Insufficient balance");
        // Safe: custom lock prevents reentrancy
        token.send(msg.sender, amount, "");
        balances[msg.sender] -= amount;

        customLock = false;
    }
}
