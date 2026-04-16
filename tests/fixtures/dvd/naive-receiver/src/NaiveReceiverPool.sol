// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title IERC3156FlashBorrower
 * @dev Interface for ERC-3156 flash loan receivers
 */
interface IERC3156FlashBorrower {
    function onFlashLoan(
        address initiator,
        address token,
        uint256 amount,
        uint256 fee,
        bytes calldata data
    ) external returns (bytes32);
}

/**
 * @title NaiveReceiverPool
 * @notice A pool offering flash loans with a critical design flaw
 * @dev Source: Damn Vulnerable DeFi - naive-receiver challenge
 *      https://github.com/tinchoabbate/damn-vulnerable-defi
 *
 * KNOWN VULNERABILITY (Ground Truth):
 *
 * DVD-NR-001: Unauthorized Flash Loan Initiation
 *   - Type: access-control
 *   - Severity: CRITICAL
 *   - Function: flashLoan
 *   - Description: Anyone can call flashLoan() specifying ANY receiver address.
 *                  This allows attackers to drain victim receiver contracts by
 *                  repeatedly forcing them to pay the 1 ETH fee.
 *
 * EXPLOIT PATH:
 *   1. Attacker identifies a receiver contract with ETH balance
 *   2. Attacker calls flashLoan(victimReceiver, ETH, 0, "") repeatedly
 *   3. Each call costs victim 1 ETH in fees (paid to pool)
 *   4. After 10 calls, victim's 10 ETH balance is drained
 */
contract NaiveReceiverPool {
    address public constant ETH = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;
    uint256 private constant FIXED_FEE = 1 ether;

    error RepayFailed();
    error UnsupportedCurrency();
    error CallbackFailed();

    constructor() payable {}

    function maxFlashLoan(address token) external view returns (uint256) {
        if (token != ETH) return 0;
        return address(this).balance;
    }

    function flashFee(address token, uint256) external pure returns (uint256) {
        if (token != ETH) revert UnsupportedCurrency();
        return FIXED_FEE;
    }

    /**
     * @notice Execute a flash loan
     * @dev VULNERABLE: No check that msg.sender is authorized to request loan for receiver
     *
     * EXPECTED DETECTION:
     * - Pattern: unauthorized-action-on-behalf
     * - BSKG: receiver parameter is used for external call without sender validation
     */
    function flashLoan(
        IERC3156FlashBorrower receiver,
        address token,
        uint256 amount,
        bytes calldata data
    ) external returns (bool) {
        if (token != ETH) revert UnsupportedCurrency();

        uint256 balanceBefore = address(this).balance;

        // Send ETH to receiver
        (bool sent, ) = address(receiver).call{value: amount}("");
        require(sent, "Transfer failed");

        // Callback - receiver must pay back loan + fee
        // BUG: No check that msg.sender == receiver or is authorized
        if (receiver.onFlashLoan(msg.sender, token, amount, FIXED_FEE, data)
            != keccak256("ERC3156FlashBorrower.onFlashLoan")) {
            revert CallbackFailed();
        }

        // Check repayment
        if (address(this).balance < balanceBefore + FIXED_FEE) {
            revert RepayFailed();
        }

        return true;
    }

    receive() external payable {}
}
