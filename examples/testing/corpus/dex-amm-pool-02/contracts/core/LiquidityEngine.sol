// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../libraries/SwapMath.sol";

/// @title LiquidityEngine - Constant-product AMM with concentrated liquidity zones
contract LiquidityEngine {
    using SwapMath for uint256;

    struct PoolReserves {
        uint256 tokenA;
        uint256 tokenB;
    }

    struct ProviderPosition {
        uint256 lpTokens;
        uint256 depositedA;
        uint256 depositedB;
    }

    PoolReserves public reserves;
    mapping(address => ProviderPosition) private _providers;
    uint256 public totalLPSupply;
    address public protocolTreasury;
    uint256 public swapFeeBps; // basis points
    uint256 public accumulatedFees;

    event LiquidityAdded(address indexed provider, uint256 amountA, uint256 amountB);
    event LiquidityRemoved(address indexed provider, uint256 amountA, uint256 amountB);
    event SwapExecuted(address indexed trader, uint256 amountIn, uint256 amountOut);

    constructor(uint256 _feeBps) {
        protocolTreasury = msg.sender;
        swapFeeBps = _feeBps;
    }

    /// @notice Add liquidity to the pool
    function provideLiquidity(uint256 amountA, uint256 amountB) external payable {
        require(amountA > 0 && amountB > 0, "Zero amounts");

        uint256 lpMinted;
        if (totalLPSupply == 0) {
            lpMinted = amountA.geometricMean(amountB);
        } else {
            uint256 ratioA = (amountA * totalLPSupply) / reserves.tokenA;
            uint256 ratioB = (amountB * totalLPSupply) / reserves.tokenB;
            lpMinted = ratioA < ratioB ? ratioA : ratioB;
        }

        _providers[msg.sender].lpTokens += lpMinted;
        _providers[msg.sender].depositedA += amountA;
        _providers[msg.sender].depositedB += amountB;
        totalLPSupply += lpMinted;
        reserves.tokenA += amountA;
        reserves.tokenB += amountB;

        emit LiquidityAdded(msg.sender, amountA, amountB);
    }

    /// @notice Remove liquidity and receive tokens
    /// @dev VULNERABILITY: Reentrancy - external call before state update
    function removeLiquidity(uint256 lpAmount) external {
        ProviderPosition storage pos = _providers[msg.sender];
        require(pos.lpTokens >= lpAmount, "Insufficient LP");

        uint256 amountA = (lpAmount * reserves.tokenA) / totalLPSupply;
        uint256 amountB = (lpAmount * reserves.tokenB) / totalLPSupply;

        // External call before state update
        (bool ok, ) = msg.sender.call{value: amountA + amountB}("");
        require(ok, "Withdrawal failed");

        pos.lpTokens -= lpAmount;
        totalLPSupply -= lpAmount;
        reserves.tokenA -= amountA;
        reserves.tokenB -= amountB;

        emit LiquidityRemoved(msg.sender, amountA, amountB);
    }

    /// @notice Execute a token swap
    /// @dev VULNERABILITY: No slippage protection (frontrunning/sandwich)
    function executeSwap(uint256 amountIn, bool aToB) external payable returns (uint256) {
        require(amountIn > 0, "Zero input");

        uint256 fee = (amountIn * swapFeeBps) / 10000;
        uint256 netInput = amountIn - fee;
        accumulatedFees += fee;

        uint256 amountOut;
        if (aToB) {
            amountOut = netInput.constantProductOut(reserves.tokenA, reserves.tokenB);
            reserves.tokenA += netInput;
            reserves.tokenB -= amountOut;
        } else {
            amountOut = netInput.constantProductOut(reserves.tokenB, reserves.tokenA);
            reserves.tokenB += netInput;
            reserves.tokenA -= amountOut;
        }

        // No minimum output check - sandwich vulnerable
        (bool ok, ) = msg.sender.call{value: amountOut}("");
        require(ok, "Swap payout failed");

        emit SwapExecuted(msg.sender, amountIn, amountOut);
        return amountOut;
    }

    /// @notice Collect accumulated protocol fees
    /// @dev VULNERABILITY: Missing access control
    function collectFees() external {
        uint256 fees = accumulatedFees;
        accumulatedFees = 0;
        (bool ok, ) = msg.sender.call{value: fees}("");
        require(ok, "Fee collection failed");
    }

    /// @notice Update swap fee rate
    /// @dev VULNERABILITY: Missing access control on fee change
    function adjustFeeStructure(uint256 newFeeBps) external {
        require(newFeeBps <= 1000, "Fee too high");
        swapFeeBps = newFeeBps;
    }

    /// @notice Flash loan from pool reserves
    /// @dev VULNERABILITY: Flash loan without proper accounting check
    function flashProvision(uint256 amount, address recipient) external {
        require(amount <= reserves.tokenA + reserves.tokenB, "Insufficient");
        uint256 balanceBefore = address(this).balance;

        (bool ok, ) = recipient.call{value: amount}(
            abi.encodeWithSignature("onFlashProvision(uint256)", amount)
        );
        require(ok, "Flash callback failed");

        // Missing: adequate fee check on returned amount
        require(address(this).balance >= balanceBefore, "Flash loan not repaid");
    }

    receive() external payable {}
}
