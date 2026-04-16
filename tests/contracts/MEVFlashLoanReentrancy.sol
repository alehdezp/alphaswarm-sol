// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MEVFlashLoanReentrancy
 * @notice Demonstrates flash loan attack combined with reentrancy for MEV extraction
 *
 * Flash loan callback can reenter contract to manipulate state
 * or exploit check-effects-interactions violations.
 *
 * Flash Loan + Reentrancy Flow:
 * 1. Attacker borrows large amount via flash loan
 * 2. During flash loan callback, attacker reenters vulnerable function
 * 3. State is manipulated (e.g., inflated balance, skewed ratio)
 * 4. Attacker completes primary action at manipulated state
 * 5. Flash loan is repaid, profit is extracted
 *
 * Related: CWE-841 (Improper Enforcement of Behavioral Workflow)
 * Protection: Reentrancy guards, CEI pattern, flash loan guards
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IFlashLoanReceiver {
    function executeOperation(uint256 amount, uint256 fee, bytes calldata params) external;
}

contract MEVFlashLoanReentrancy {
    mapping(address => uint256) public balances;
    IERC20 public token;

    constructor(IERC20 _token) {
        token = _token;
    }

    // VULNERABLE: State written after external call (flash loan callback)
    function flashLoanWithdraw(uint256 borrowAmount, bytes calldata params) external {
        uint256 balanceBefore = token.balanceOf(address(this));

        // External call to attacker-controlled contract
        IFlashLoanReceiver(msg.sender).executeOperation(borrowAmount, 0, params);

        uint256 balanceAfter = token.balanceOf(address(this));
        require(balanceAfter >= balanceBefore, "flash loan not repaid");

        // VULNERABLE: State update after external call
        // Attacker could have reentered during executeOperation
        balances[msg.sender] -= borrowAmount;
    }

    // VULNERABLE: No reentrancy guard on withdrawal
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient balance");

        // VULNERABLE: External call before state update
        token.transfer(msg.sender, amount);

        // State update after external call - reentrancy risk
        balances[msg.sender] -= amount;
    }
}
