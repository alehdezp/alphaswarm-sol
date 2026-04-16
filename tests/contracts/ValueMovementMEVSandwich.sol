// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ValueMovementMEVSandwich
 * @dev Demonstrates MEV sandwich attack vulnerabilities and frontrunning patterns
 *
 * Transactions without slippage protection or deadline checks
 * can be sandwiched by MEV bots, causing users to receive unfavorable prices.
 *
 * ATTACK PATTERN:
 * 1. MEV bot sees user's swap transaction in mempool
 * 2. Frontrun: Bot submits swap with higher gas to execute first
 * 3. User's transaction executes at worse price
 * 4. Backrun: Bot submits reverse swap to profit
 *
 * REAL EXAMPLES:
 * - UniswapV2 swaps without slippage checks
 * - Large trades without deadline protection
 * - 2024-2025: $289.76M in sandwich attacks (51.56% of MEV volume)
 *
 * REFERENCES:
 * - https://bitquery.io/blog/different-mev-attacks
 * - https://cow.fi/learn/what-is-backrunning-mev-attacks-explained
 * - Medium: Implementing Effective MEV Protection in 2025
 */

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

// VULNERABLE: Swap without slippage protection
contract VulnerableSwapNoSlippage {
    IUniswapV2Router public router;

    constructor(address _router) {
        router = IUniswapV2Router(_router);
    }

    // amountOutMin = 0 allows unlimited slippage
    // MEV bot can sandwich this trade for profit
    function swapTokens(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) external {
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;

        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).transfer(address(router), amountIn);

        // PROBLEM: amountOutMin = 0 means no slippage protection
        router.swapExactTokensForTokens(
            amountIn,
            0, // No minimum output!
            path,
            msg.sender,
            block.timestamp + 1 hours
        );
    }
}

// SAFE: Swap with slippage protection
contract SafeSwapWithSlippage {
    IUniswapV2Router public router;

    constructor(address _router) {
        router = IUniswapV2Router(_router);
    }

    // SAFE: User specifies minimum output amount
    function swapTokens(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut // User-specified slippage tolerance
    ) external {
        require(minAmountOut > 0, "Must specify minimum output");

        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;

        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).transfer(address(router), amountIn);

        // SAFE: Reverts if output is less than minimum
        router.swapExactTokensForTokens(
            amountIn,
            minAmountOut,
            path,
            msg.sender,
            block.timestamp + 1 hours
        );
    }
}

// VULNERABLE: No deadline check
contract VulnerableSwapNoDeadline {
    IUniswapV2Router public router;

    constructor(address _router) {
        router = IUniswapV2Router(_router);
    }

    // No deadline or uses block.timestamp
    // Transaction can be held and executed at unfavorable time
    function swapTokens(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external {
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;

        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).transfer(address(router), amountIn);

        // PROBLEM: Using block.timestamp as deadline is ineffective
        // Miners can manipulate timestamp within bounds
        router.swapExactTokensForTokens(
            amountIn,
            minAmountOut,
            path,
            msg.sender,
            block.timestamp // Meaningless deadline!
        );
    }
}

// SAFE: User-specified deadline
contract SafeSwapWithDeadline {
    IUniswapV2Router public router;

    constructor(address _router) {
        router = IUniswapV2Router(_router);
    }

    // SAFE: User specifies deadline from off-chain
    function swapTokens(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline // User-specified deadline
    ) external {
        require(deadline >= block.timestamp, "Deadline expired");
        require(minAmountOut > 0, "Must specify minimum output");

        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;

        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).transfer(address(router), amountIn);

        // SAFE: Reverts if deadline passed
        router.swapExactTokensForTokens(
            amountIn,
            minAmountOut,
            path,
            msg.sender,
            deadline
        );
    }
}

// VULNERABLE: Large trade without protection
contract VulnerableLargeTrade {
    mapping(address => uint256) public reserves;

    // Large swap can be sandwiched
    // No checks on price impact or slippage
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) external returns (uint256 amountOut) {
        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        reserves[tokenIn] += amountIn;

        // Simple constant product formula
        // PROBLEM: No protection against unfavorable price impact
        amountOut = (amountIn * reserves[tokenOut]) / reserves[tokenIn];
        reserves[tokenOut] -= amountOut;

        IERC20(tokenOut).transfer(msg.sender, amountOut);
    }
}

// SAFE: Trade with price impact check
contract SafeLargeTradeProtected {
    mapping(address => uint256) public reserves;
    uint256 public constant MAX_PRICE_IMPACT = 100; // 1% in basis points

    // SAFE: Checks price impact before executing
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut
    ) external returns (uint256 amountOut) {
        uint256 reserveIn = reserves[tokenIn];
        uint256 reserveOut = reserves[tokenOut];

        // Calculate expected output
        amountOut = (amountIn * reserveOut) / reserveIn;

        // SAFE: Check price impact
        uint256 priceImpact = (amountIn * 10000) / reserveIn;
        require(priceImpact <= MAX_PRICE_IMPACT, "Price impact too high");

        // SAFE: Check minimum output
        require(amountOut >= minAmountOut, "Slippage too high");

        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        reserves[tokenIn] += amountIn;
        reserves[tokenOut] -= amountOut;

        IERC20(tokenOut).transfer(msg.sender, amountOut);
    }
}

// VULNERABLE: Liquidation without deadline
contract VulnerableLiquidation {
    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debt;

    function liquidate(address user) external {
        require(isUnderCollateralized(user), "User not under-collateralized");

        // Liquidation can be frontrun
        // MEV bot can frontrun to extract value before liquidator
        uint256 collateralAmount = collateral[user];
        uint256 debtAmount = debt[user];

        collateral[user] = 0;
        debt[user] = 0;

        // Transfer collateral to liquidator at potentially unfair price
        // No protection against frontrunning or deadline
    }

    function isUnderCollateralized(address user) internal view returns (bool) {
        return collateral[user] * 150 < debt[user] * 100;
    }
}

// SAFE: Liquidation with MEV protection
contract SafeLiquidation {
    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debt;
    mapping(bytes32 => bool) public usedCommitments;

    // SAFE: Commit-reveal scheme to prevent frontrunning
    function commitLiquidation(bytes32 commitment) external {
        usedCommitments[commitment] = true;
    }

    function liquidate(
        address user,
        bytes32 salt,
        uint256 deadline
    ) external {
        require(block.timestamp <= deadline, "Deadline expired");

        bytes32 commitment = keccak256(abi.encodePacked(msg.sender, user, salt));
        require(usedCommitments[commitment], "No commitment");

        require(isUnderCollateralized(user), "User not under-collateralized");

        uint256 collateralAmount = collateral[user];
        uint256 debtAmount = debt[user];

        collateral[user] = 0;
        debt[user] = 0;

        // Protected liquidation with deadline
    }

    function isUnderCollateralized(address user) internal view returns (bool) {
        return collateral[user] * 150 < debt[user] * 100;
    }
}

// VULNERABLE: Mempool-visible order that can be frontrun
contract VulnerableOrderBook {
    struct Order {
        address trader;
        uint256 amount;
        uint256 price;
    }

    Order[] public orders;

    // Order submission is public and can be frontrun
    function submitOrder(uint256 amount, uint256 price) external {
        orders.push(Order({
            trader: msg.sender,
            amount: amount,
            price: price
        }));
        // MEV bots can see this order and frontrun it
    }
}

// SAFE: Private order submission via flashbots or commitment scheme
contract SafeOrderBook {
    struct Order {
        address trader;
        uint256 amount;
        uint256 price;
    }

    Order[] public orders;
    mapping(bytes32 => bool) public commitments;

    // SAFE: Two-phase commit-reveal to hide order details
    function commitOrder(bytes32 orderHash) external {
        commitments[orderHash] = true;
    }

    function revealOrder(
        uint256 amount,
        uint256 price,
        bytes32 salt
    ) external {
        bytes32 orderHash = keccak256(abi.encodePacked(msg.sender, amount, price, salt));
        require(commitments[orderHash], "No commitment");

        orders.push(Order({
            trader: msg.sender,
            amount: amount,
            price: price
        }));
    }
}
