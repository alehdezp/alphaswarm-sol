// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title TokenDecimalMismatch
 * @dev Demonstrates vulnerabilities from token decimal mismatches
 *
 * Tokens have different decimal places (USDC=6, WBTC=8, DAI=18)
 * Contracts that assume all tokens have 18 decimals can experience:
 * - Massive value loss (treating 6-decimal as 18-decimal)
 * - Precision errors
 * - Accounting bugs
 *
 * CWE-682: Incorrect Calculation
 *
 * REAL EXAMPLES:
 * - Multiple AMM exploits due to decimal mismatch
 * - Lending protocol insolvencies
 */

interface IERC20Decimals {
    function decimals() external view returns (uint8);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

// VULNERABLE: Assumes all tokens have 18 decimals
contract VulnerableDecimalSwap {
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) public returns (uint256 amountOut) {
        // PROBLEM: Assumes 1:1 ratio without accounting for decimals
        // If tokenIn is USDC (6 decimals) and tokenOut is DAI (18 decimals)
        // User sends 1000 USDC (1000 * 10^6) and expects 1000 DAI (1000 * 10^18)
        // But this gives them only 1000 * 10^6 DAI units = 0.000001 DAI!
        amountOut = amountIn;

        IERC20Decimals(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20Decimals(tokenOut).transfer(msg.sender, amountOut);
    }

    // PROBLEM: Price calculation ignores decimals
    function getPrice(address token0, address token1, uint256 reserve0, uint256 reserve1)
        public
        pure
        returns (uint256)
    {
        // This is wrong for tokens with different decimals
        return (reserve1 * 1e18) / reserve0;
    }
}

// SAFE: Proper decimal normalization
contract SafeDecimalSwap {
    function swap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) public returns (uint256 amountOut) {
        uint8 decimalsIn = IERC20Decimals(tokenIn).decimals();
        uint8 decimalsOut = IERC20Decimals(tokenOut).decimals();

        // Normalize to 18 decimals for calculation
        uint256 normalizedAmountIn;
        if (decimalsIn < 18) {
            normalizedAmountIn = amountIn * (10 ** (18 - decimalsIn));
        } else {
            normalizedAmountIn = amountIn / (10 ** (decimalsIn - 18));
        }

        // Calculate output in 18 decimals
        uint256 normalizedAmountOut = calculateSwap(normalizedAmountIn);

        // Convert to output token's decimals
        if (decimalsOut < 18) {
            amountOut = normalizedAmountOut / (10 ** (18 - decimalsOut));
        } else {
            amountOut = normalizedAmountOut * (10 ** (decimalsOut - 18));
        }

        IERC20Decimals(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20Decimals(tokenOut).transfer(msg.sender, amountOut);
    }

    function getPrice(address token0, address token1, uint256 reserve0, uint256 reserve1)
        public
        view
        returns (uint256)
    {
        uint8 decimals0 = IERC20Decimals(token0).decimals();
        uint8 decimals1 = IERC20Decimals(token1).decimals();

        // Normalize reserves to 18 decimals
        uint256 normalized0 = reserve0 * (10 ** (18 - decimals0));
        uint256 normalized1 = reserve1 * (10 ** (18 - decimals1));

        return (normalized1 * 1e18) / normalized0;
    }

    function calculateSwap(uint256 amount) internal pure returns (uint256) {
        return amount; // Simplified
    }
}

// VULNERABLE: LP token with decimal mismatch
contract VulnerableLPPool {
    address public token0;
    address public token1;
    uint256 public reserve0;
    uint256 public reserve1;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;

    constructor(address _token0, address _token1) {
        token0 = _token0;
        token1 = _token1;
    }

    function addLiquidity(uint256 amount0, uint256 amount1) public returns (uint256 liquidity) {
        IERC20Decimals(token0).transferFrom(msg.sender, address(this), amount0);
        IERC20Decimals(token1).transferFrom(msg.sender, address(this), amount1);

        // PROBLEM: Doesn't account for decimal differences
        // If token0 has 6 decimals and token1 has 18 decimals
        // LP shares calculation is completely wrong
        if (totalSupply == 0) {
            liquidity = sqrt(amount0 * amount1);
        } else {
            liquidity = min(
                (amount0 * totalSupply) / reserve0,
                (amount1 * totalSupply) / reserve1
            );
        }

        balanceOf[msg.sender] += liquidity;
        totalSupply += liquidity;
        reserve0 += amount0;
        reserve1 += amount1;
    }

    function sqrt(uint256 y) internal pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = y / 2 + 1;
            while (x < z) {
                z = x;
                x = (y / x + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }

    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}

// SAFE: LP pool with decimal normalization
contract SafeLPPool {
    address public token0;
    address public token1;
    uint256 public reserve0;
    uint256 public reserve1;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;

    uint8 private immutable decimals0;
    uint8 private immutable decimals1;
    uint8 private constant NORMALIZED_DECIMALS = 18;

    constructor(address _token0, address _token1) {
        token0 = _token0;
        token1 = _token1;
        decimals0 = IERC20Decimals(_token0).decimals();
        decimals1 = IERC20Decimals(_token1).decimals();
    }

    function addLiquidity(uint256 amount0, uint256 amount1) public returns (uint256 liquidity) {
        IERC20Decimals(token0).transferFrom(msg.sender, address(this), amount0);
        IERC20Decimals(token1).transferFrom(msg.sender, address(this), amount1);

        // Normalize to 18 decimals for calculation
        uint256 normalized0 = amount0 * (10 ** (NORMALIZED_DECIMALS - decimals0));
        uint256 normalized1 = amount1 * (10 ** (NORMALIZED_DECIMALS - decimals1));

        if (totalSupply == 0) {
            liquidity = sqrt(normalized0 * normalized1);
        } else {
            uint256 normalizedReserve0 = reserve0 * (10 ** (NORMALIZED_DECIMALS - decimals0));
            uint256 normalizedReserve1 = reserve1 * (10 ** (NORMALIZED_DECIMALS - decimals1));

            liquidity = min(
                (normalized0 * totalSupply) / normalizedReserve0,
                (normalized1 * totalSupply) / normalizedReserve1
            );
        }

        balanceOf[msg.sender] += liquidity;
        totalSupply += liquidity;
        reserve0 += amount0;
        reserve1 += amount1;
    }

    function sqrt(uint256 y) internal pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = y / 2 + 1;
            while (x < z) {
                z = x;
                x = (y / x + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }

    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}

// VULNERABLE: Precision loss in conversion
contract VulnerablePrecision {
    function convertTokenAmount(
        address fromToken,
        address toToken,
        uint256 amount
    ) public view returns (uint256) {
        uint8 fromDecimals = IERC20Decimals(fromToken).decimals();
        uint8 toDecimals = IERC20Decimals(toToken).decimals();

        // PROBLEM: Truncation when converting to lower decimals
        // Example: 1.123456789 USDC (6 decimals) to WBTC (8 decimals)
        // Small amounts get completely lost
        if (fromDecimals > toDecimals) {
            return amount / (10 ** (fromDecimals - toDecimals));
        } else {
            return amount * (10 ** (toDecimals - fromDecimals));
        }
    }
}

// SAFE: Track precision loss
contract SafePrecision {
    event PrecisionLoss(address indexed token, uint256 dustAmount);

    function convertTokenAmount(
        address fromToken,
        address toToken,
        uint256 amount
    ) public returns (uint256 converted, uint256 dust) {
        uint8 fromDecimals = IERC20Decimals(fromToken).decimals();
        uint8 toDecimals = IERC20Decimals(toToken).decimals();

        if (fromDecimals > toDecimals) {
            uint256 divisor = 10 ** (fromDecimals - toDecimals);
            converted = amount / divisor;
            dust = amount % divisor;

            if (dust > 0) {
                emit PrecisionLoss(fromToken, dust);
            }
        } else {
            converted = amount * (10 ** (toDecimals - fromDecimals));
            dust = 0;
        }
    }
}

// VULNERABLE: Hardcoded decimal assumption
contract VulnerableHardcodedDecimals {
    // PROBLEM: Assumes all tokens have 18 decimals
    uint256 private constant DECIMAL_MULTIPLIER = 1e18;

    function calculateValue(address token, uint256 amount) public pure returns (uint256) {
        // This only works for 18-decimal tokens!
        return (amount * DECIMAL_MULTIPLIER) / DECIMAL_MULTIPLIER;
    }

    function formatAmount(uint256 rawAmount) public pure returns (uint256) {
        // PROBLEM: Always divides by 1e18
        // For USDC (6 decimals), this is wrong!
        return rawAmount / 1e18;
    }
}

// SAFE: Dynamic decimal handling
contract SafeDynamicDecimals {
    function calculateValue(address token, uint256 amount) public view returns (uint256) {
        uint8 decimals = IERC20Decimals(token).decimals();
        uint256 multiplier = 10 ** decimals;
        return (amount * multiplier) / multiplier;
    }

    function formatAmount(address token, uint256 rawAmount) public view returns (uint256) {
        uint8 decimals = IERC20Decimals(token).decimals();
        return rawAmount / (10 ** decimals);
    }

    function normalizeToDecimals(
        address token,
        uint256 amount,
        uint8 targetDecimals
    ) public view returns (uint256) {
        uint8 tokenDecimals = IERC20Decimals(token).decimals();

        if (tokenDecimals > targetDecimals) {
            return amount / (10 ** (tokenDecimals - targetDecimals));
        } else if (tokenDecimals < targetDecimals) {
            return amount * (10 ** (targetDecimals - tokenDecimals));
        }
        return amount;
    }
}
