// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title IFlashLoanEtherReceiver
 * @dev Interface for flash loan receivers
 */
interface IFlashLoanEtherReceiver {
    function execute() external payable;
}

/**
 * @title SideEntranceLenderPool
 * @notice A pool offering flash loans with a critical accounting bug
 * @dev Source: Damn Vulnerable DeFi - side-entrance challenge
 *      https://github.com/tinchoabbate/damn-vulnerable-defi
 *
 * KNOWN VULNERABILITIES (Ground Truth):
 *
 * DVD-SE-001: Flash Loan Accounting Manipulation
 *   - Type: accounting-manipulation / flash-loan-vulnerability
 *   - Severity: CRITICAL
 *   - Functions: flashLoan + deposit interaction
 *   - Description: The flash loan repayment check only verifies the pool's
 *                  ETH balance hasn't decreased. This allows an attacker to
 *                  call deposit() during the flash loan callback, which both
 *                  returns the borrowed ETH AND credits it to their balance.
 *
 * DVD-SE-002: Potential Reentrancy in withdraw
 *   - Type: reentrancy
 *   - Severity: HIGH
 *   - Function: withdraw
 *   - Description: External call after state update, but CEI pattern followed.
 *                  The primary exploit uses the accounting bug, not reentrancy.
 *
 * EXPLOIT PATH (DVD-SE-001):
 *   1. Attacker deploys contract implementing IFlashLoanEtherReceiver
 *   2. Attacker calls flashLoan(pool.balance)
 *   3. In execute() callback, attacker calls deposit() with all received ETH
 *   4. deposit() credits the ETH to attacker's balance AND returns it to pool
 *   5. After callback, pool balance check passes (balance unchanged)
 *   6. Attacker calls withdraw() to drain their now-credited balance
 */
contract SideEntranceLenderPool {
    mapping(address => uint256) public balances;

    error RepayFailed();

    /**
     * @notice Deposit ETH into the pool
     * @dev PART OF VULNERABILITY: Can be called during flash loan callback
     *      to credit borrowed funds to caller's balance
     *
     * EXPECTED DETECTION:
     * - Pattern: deposit-during-callback (state modification during callback)
     * - BSKG: Public function that writes user balance
     */
    function deposit() external payable {
        unchecked {
            balances[msg.sender] += msg.value;
        }
    }

    /**
     * @notice Withdraw deposited ETH
     * @dev Secondary vulnerability: CEI pattern followed but external call exists
     *
     * EXPECTED DETECTION:
     * - Pattern: reentrancy-potential (external call after state update - safe CEI)
     * - BSKG: has_external_calls = true, CEI pattern followed
     */
    function withdraw() external {
        uint256 amount = balances[msg.sender];

        // CEI: Check-Effects-Interactions pattern (SAFE for reentrancy)
        balances[msg.sender] = 0;

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Withdraw failed");
    }

    /**
     * @notice Execute a flash loan
     * @dev VULNERABLE: Repayment check is insufficient - only checks balance
     *      doesn't decrease, allowing deposit() to satisfy repayment
     *
     * EXPECTED DETECTION:
     * - Pattern: flash-loan-accounting
     * - BSKG: Balance check after external callback, deposit() accessible during callback
     */
    function flashLoan(uint256 amount) external {
        uint256 balanceBefore = address(this).balance;

        // External call to borrower - they can call deposit() here
        IFlashLoanEtherReceiver(msg.sender).execute{value: amount}();

        // BUG: Only checks balance, not HOW it was returned
        // deposit() during execute() satisfies this check
        if (address(this).balance < balanceBefore) {
            revert RepayFailed();
        }
    }

    receive() external payable {}
}
