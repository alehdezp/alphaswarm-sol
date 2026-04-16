// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../libraries/SwapMath.sol";

/// @title LiquidityEngine (SAFE VARIANT)
contract LiquidityEngine_safe {
    using SwapMath for uint256;

    struct PoolReserves { uint256 tokenA; uint256 tokenB; }
    struct ProviderPosition { uint256 lpTokens; uint256 depositedA; uint256 depositedB; }

    PoolReserves public reserves;
    mapping(address => ProviderPosition) private _providers;
    uint256 public totalLPSupply;
    address public protocolTreasury;
    uint256 public swapFeeBps;
    uint256 public accumulatedFees;
    bool private _locked;

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyTreasury() { require(msg.sender == protocolTreasury, "Not treasury"); _; }

    event LiquidityAdded(address indexed provider, uint256 amountA, uint256 amountB);
    event LiquidityRemoved(address indexed provider, uint256 amountA, uint256 amountB);
    event SwapExecuted(address indexed trader, uint256 amountIn, uint256 amountOut);

    constructor(uint256 _feeBps) { protocolTreasury = msg.sender; swapFeeBps = _feeBps; }

    function provideLiquidity(uint256 amountA, uint256 amountB) external payable {
        require(amountA > 0 && amountB > 0, "Zero amounts");
        uint256 lpMinted;
        if (totalLPSupply == 0) { lpMinted = amountA.geometricMean(amountB); }
        else {
            uint256 ratioA = (amountA * totalLPSupply) / reserves.tokenA;
            uint256 ratioB = (amountB * totalLPSupply) / reserves.tokenB;
            lpMinted = ratioA < ratioB ? ratioA : ratioB;
        }
        _providers[msg.sender].lpTokens += lpMinted;
        totalLPSupply += lpMinted;
        reserves.tokenA += amountA;
        reserves.tokenB += amountB;
        emit LiquidityAdded(msg.sender, amountA, amountB);
    }

    function removeLiquidity(uint256 lpAmount) external nonReentrant { // FIXED
        ProviderPosition storage pos = _providers[msg.sender];
        require(pos.lpTokens >= lpAmount, "Insufficient LP");
        uint256 amountA = (lpAmount * reserves.tokenA) / totalLPSupply;
        uint256 amountB = (lpAmount * reserves.tokenB) / totalLPSupply;
        pos.lpTokens -= lpAmount;
        totalLPSupply -= lpAmount;
        reserves.tokenA -= amountA;
        reserves.tokenB -= amountB;
        (bool ok, ) = msg.sender.call{value: amountA + amountB}("");
        require(ok, "Withdrawal failed");
        emit LiquidityRemoved(msg.sender, amountA, amountB);
    }

    function executeSwap(uint256 amountIn, bool aToB, uint256 minOutput) external payable returns (uint256) {
        require(amountIn > 0, "Zero input");
        uint256 fee = (amountIn * swapFeeBps) / 10000;
        uint256 netInput = amountIn - fee;
        accumulatedFees += fee;
        uint256 amountOut;
        if (aToB) {
            amountOut = netInput.constantProductOut(reserves.tokenA, reserves.tokenB);
            reserves.tokenA += netInput; reserves.tokenB -= amountOut;
        } else {
            amountOut = netInput.constantProductOut(reserves.tokenB, reserves.tokenA);
            reserves.tokenB += netInput; reserves.tokenA -= amountOut;
        }
        require(amountOut >= minOutput, "Slippage exceeded"); // FIXED
        (bool ok, ) = msg.sender.call{value: amountOut}("");
        require(ok, "Swap payout failed");
        emit SwapExecuted(msg.sender, amountIn, amountOut);
        return amountOut;
    }

    function collectFees() external onlyTreasury { // FIXED
        uint256 fees = accumulatedFees;
        accumulatedFees = 0;
        (bool ok, ) = msg.sender.call{value: fees}("");
        require(ok, "Fee collection failed");
    }

    function adjustFeeStructure(uint256 newFeeBps) external onlyTreasury { // FIXED
        require(newFeeBps <= 1000, "Fee too high");
        swapFeeBps = newFeeBps;
    }

    function flashProvision(uint256 amount, address recipient) external nonReentrant {
        require(amount <= reserves.tokenA + reserves.tokenB, "Insufficient");
        uint256 balanceBefore = address(this).balance;
        uint256 flashFee = (amount * 9) / 10000; // 0.09% flash fee
        (bool ok, ) = recipient.call{value: amount}(
            abi.encodeWithSignature("onFlashProvision(uint256)", amount)
        );
        require(ok, "Flash callback failed");
        require(address(this).balance >= balanceBefore + flashFee, "Flash loan not repaid with fee"); // FIXED
    }

    receive() external payable {}
}
