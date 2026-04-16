// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title NonStandardTokens
 * @dev Demonstrates vulnerabilities with non-standard ERC-20 implementations
 *
 * Not all ERC-20 tokens follow the standard exactly:
 * - Missing return values (USDT, BNB)
 * - Non-standard decimals (USDC=6, WBTC=8, most=18)
 * - Revert on zero-value transfers
 * - Non-standard approval behavior
 *
 * These can cause:
 * - Transaction failures
 * - Incorrect calculations
 * - Precision loss
 * - Integration failures
 */

// USDT-like token: No return value on transfer/approve
contract USDTLikeToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    // DOES NOT return bool! (breaks ERC-20 interface)
    function transfer(address to, uint256 amount) public {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
    }

    // DOES NOT return bool!
    function approve(address spender, uint256 amount) public {
        allowance[msg.sender][spender] = amount;
    }

    function transferFrom(address from, address to, uint256 amount) public {
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
    }

    function mint(address to, uint256 amount) public {
        balanceOf[to] += amount;
    }
}

// Token with non-standard decimals
contract SixDecimalToken {
    string public name = "SixDecimal";
    uint8 public constant decimals = 6;  // NOT 18!
    mapping(address => uint256) public balanceOf;

    function mint(address to, uint256 amount) public {
        balanceOf[to] += amount;
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

// Token that reverts on zero-value transfers
contract RevertOnZeroToken {
    mapping(address => uint256) public balanceOf;

    function transfer(address to, uint256 amount) public returns (bool) {
        require(amount > 0, "Cannot transfer zero");  // Reverts on zero!
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function mint(address to, uint256 amount) public {
        balanceOf[to] += amount;
    }
}

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function decimals() external view returns (uint8);
}

// VULNERABLE: Assumes all tokens return bool
contract VulnerableTokenHandler {
    function unsafeTransfer(address token, address to, uint256 amount) public {
        // PROBLEM: USDT doesn't return bool - this will revert!
        bool success = IERC20(token).transfer(to, amount);
        require(success, "Transfer failed");
    }

    function unsafeApprove(address token, address spender, uint256 amount) public {
        // PROBLEM: USDT doesn't return bool - this will revert!
        bool success = IERC20(token).approve(spender, amount);
        require(success, "Approve failed");
    }
}

// SAFE: Using low-level call with SafeERC20 pattern
contract SafeTokenHandler {
    function safeTransfer(address token, address to, uint256 amount) public {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transfer.selector, to, amount)
        );

        // Check if call succeeded
        require(success, "Transfer call failed");

        // If data is returned, verify it's true
        // If no data returned (like USDT), accept it
        if (data.length > 0) {
            require(abi.decode(data, (bool)), "Transfer returned false");
        }
    }

    function safeApprove(address token, address spender, uint256 amount) public {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.approve.selector, spender, amount)
        );

        require(success, "Approve call failed");
        if (data.length > 0) {
            require(abi.decode(data, (bool)), "Approve returned false");
        }
    }

    function safeTransferFrom(address token, address from, address to, uint256 amount) public {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transferFrom.selector, from, to, amount)
        );

        require(success, "TransferFrom call failed");
        if (data.length > 0) {
            require(abi.decode(data, (bool)), "TransferFrom returned false");
        }
    }
}

// VULNERABLE: Assumes 18 decimals
contract VulnerableDecimalHandling {
    function swap(address tokenIn, address tokenOut, uint256 amountIn) public {
        // PROBLEM: Assumes both tokens have same decimals!
        // If tokenIn has 6 decimals and tokenOut has 18, calculations are wrong

        uint256 amountOut = amountIn;  // 1:1 ratio assumed
        // This is catastrophically wrong for different decimal tokens!

        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenOut).transfer(msg.sender, amountOut);
    }
}

// SAFE: Proper decimal handling
contract SafeDecimalHandling {
    function swap(address tokenIn, address tokenOut, uint256 amountIn) public {
        uint8 decimalsIn = IERC20(tokenIn).decimals();
        uint8 decimalsOut = IERC20(tokenOut).decimals();

        // Normalize to 18 decimals for calculation
        uint256 normalizedAmountIn = amountIn * (10 ** (18 - decimalsIn));

        // Calculate output in 18 decimals
        uint256 normalizedAmountOut = calculateSwap(normalizedAmountIn);

        // Convert to output token's decimals
        uint256 amountOut = normalizedAmountOut / (10 ** (18 - decimalsOut));

        safeTransferFrom(tokenIn, msg.sender, address(this), amountIn);
        safeTransfer(tokenOut, msg.sender, amountOut);
    }

    function calculateSwap(uint256 amount) internal pure returns (uint256) {
        return amount;  // Simplified
    }

    function safeTransfer(address token, address to, uint256 amount) internal {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transfer.selector, to, amount)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "Transfer failed");
    }

    function safeTransferFrom(address token, address from, address to, uint256 amount) internal {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transferFrom.selector, from, to, amount)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "TransferFrom failed");
    }
}

// VULNERABLE: Doesn't handle zero-value transfer rejection
contract VulnerableZeroTransfer {
    function distribute(address token, address[] memory recipients, uint256[] memory amounts) public {
        for (uint i = 0; i < recipients.length; i++) {
            // PROBLEM: If amount is 0 and token reverts on zero, this fails!
            IERC20(token).transfer(recipients[i], amounts[i]);
        }
    }
}

// SAFE: Skip zero transfers
contract SafeZeroTransfer {
    function distribute(address token, address[] memory recipients, uint256[] memory amounts) public {
        for (uint i = 0; i < recipients.length; i++) {
            // Skip zero transfers
            if (amounts[i] > 0) {
                safeTransfer(token, recipients[i], amounts[i]);
            }
        }
    }

    function safeTransfer(address token, address to, uint256 amount) internal {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transfer.selector, to, amount)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "Transfer failed");
    }
}

// VULNERABLE: Precision loss with different decimals
contract VulnerablePrecisionLoss {
    function convertAmount(uint256 amount, uint8 fromDecimals, uint8 toDecimals) public pure returns (uint256) {
        // PROBLEM: If toDecimals < fromDecimals, this loses precision!
        // Example: 1.123456789 USDC (6 decimals) to WBTC (8 decimals)
        if (fromDecimals > toDecimals) {
            return amount / (10 ** (fromDecimals - toDecimals));  // Truncation!
        } else {
            return amount * (10 ** (toDecimals - fromDecimals));
        }
    }
}

// SAFE: Precision tracking
contract SafePrecisionHandling {
    function convertAmount(uint256 amount, uint8 fromDecimals, uint8 toDecimals) public pure returns (uint256, uint256) {
        if (fromDecimals > toDecimals) {
            uint256 divisor = 10 ** (fromDecimals - toDecimals);
            uint256 converted = amount / divisor;
            uint256 dust = amount % divisor;  // Track dust for refund or accumulation
            return (converted, dust);
        } else {
            return (amount * (10 ** (toDecimals - fromDecimals)), 0);
        }
    }
}
