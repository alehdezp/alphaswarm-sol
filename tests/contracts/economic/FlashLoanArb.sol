// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IUniswapV2Pair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function swap(uint amount0Out, uint amount1Out, address to, bytes calldata data) external;
}

interface IERC20 {
    function transfer(address to, uint value) external returns (bool);
    function balanceOf(address owner) external view returns (uint);
}

/**
 * @title FlashLoanArb
 * @dev A simplified example of a contract vulnerable to economic exploitation via flash loans.
 * 
 *  * This contract allows users to deposit an asset and borrow against it based on the 
 * spot price of a Uniswap pool. It does not use a TWAP or Chainlink oracle.
 * 
 * AN AGENT SHOULD DETECT:
 * 1. Price dependence on `pool.getReserves()` (Spot Price).
 * 2. Ability to manipulate this price via a Flash Loan within a single transaction.
 * 3. Profitability: Manipulate price -> Borrow undercollateralized -> Default.
 * 
 * STATIC ANALYSIS:
 * Often misses this because "getReserves" is a valid view function. 
 * The bug is ECONOMIC, not syntactic.
 */
contract FlashLoanArb {
    IUniswapV2Pair public immutable pool;
    IERC20 public immutable collateralToken; // Token A
    IERC20 public immutable borrowToken;     // Token B

    mapping(address => uint256) public collateralBalance;
    mapping(address => uint256) public borrowBalance;

    constructor(address _pool, address _collateral, address _borrow) {
        pool = IUniswapV2Pair(_pool);
        collateralToken = IERC20(_collateral);
        borrowToken = IERC20(_borrow);
    }

    function deposit(uint256 amount) external {
        collateralToken.transfer(msg.sender, address(this)); // transfer usage (minor)
        collateralBalance[msg.sender] += amount;
    }

    // Vulnerable function: Calculates max borrow based on SPOT price
    function borrow(uint256 amount) external {
        (uint112 reserve0, uint112 reserve1, ) = pool.getReserves();
        
        // Assume collateral is token0, borrow is token1
        // Spot Price = reserve1 / reserve0
        uint256 spotPrice = (uint256(reserve1) * 1e18) / uint256(reserve0);
        
        uint256 collateralValue = (collateralBalance[msg.sender] * spotPrice) / 1e18;
        uint256 maxBorrow = (collateralValue * 80) / 100; // 80% LTV

        require(borrowBalance[msg.sender] + amount <= maxBorrow, "Insufficient collateral");

        borrowBalance[msg.sender] += amount;
        borrowToken.transfer(msg.sender, amount);
    }
}
