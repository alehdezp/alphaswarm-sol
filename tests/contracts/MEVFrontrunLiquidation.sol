// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MEVFrontrunLiquidation
 * @notice Demonstrates frontrunning of liquidations in lending protocols
 *
 * Public liquidation functions allow MEV bots to frontrun
 * legitimate liquidators, extracting liquidation bonuses.
 *
 * Liquidation Frontrunning Flow:
 * 1. Borrower becomes liquidatable (collateral value drops below threshold)
 * 2. Legitimate liquidator submits liquidation transaction
 * 3. MEV bot monitors mempool, sees liquidation transaction
 * 4. Bot submits same liquidation with higher gas price
 * 5. Bot's transaction executes first, claiming liquidation bonus
 * 6. Original liquidator's transaction reverts or receives nothing
 *
 * Impact: Reduces incentive for keeper networks, increases gas costs
 * Related: General MEV frontrunning (CWE-20, SCWE-037)
 */

interface IOracle {
    function getPrice(address token) external view returns (uint256);
}

contract MEVFrontrunLiquidation {
    struct Position {
        uint256 collateral;
        uint256 debt;
        address collateralToken;
        address debtToken;
    }

    mapping(address => Position) public positions;
    IOracle public oracle;
    uint256 public constant LIQUIDATION_THRESHOLD = 150; // 150%
    uint256 public constant LIQUIDATION_BONUS = 5; // 5%

    constructor(IOracle _oracle) {
        oracle = _oracle;
    }

    // VULNERABLE: Public liquidation function allows frontrunning
    // No protection for original liquidator
    function liquidate(address borrower) external {
        Position memory pos = positions[borrower];

        uint256 collateralValue = pos.collateral * oracle.getPrice(pos.collateralToken) / 1e18;
        uint256 debtValue = pos.debt * oracle.getPrice(pos.debtToken) / 1e18;

        // Check if position is liquidatable
        require(collateralValue * 100 < debtValue * LIQUIDATION_THRESHOLD, "not liquidatable");

        // VULNERABLE: Anyone can claim liquidation bonus by frontrunning
        // No commit-reveal, no FCFS protection, no liquidator queue
        uint256 bonus = pos.collateral * LIQUIDATION_BONUS / 100;
        uint256 totalReward = pos.collateral + bonus;

        // Transfer reward to msg.sender (can be frontrun)
        positions[borrower].collateral = 0;
        positions[borrower].debt = 0;

        // Reward goes to whoever executes first (MEV bot wins)
        // transfer(msg.sender, totalReward);
    }

    // VULNERABLE: Instant liquidation without protection mechanisms
    function instantLiquidate(address borrower, uint256 amount) external {
        // No time locks, no batching, no auction
        // Pure race condition for MEV extraction
        require(amount > 0, "invalid amount");
        // liquidation logic...
    }
}
