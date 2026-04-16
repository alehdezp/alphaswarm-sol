// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title FeeOnTransferToken
 * @dev Demonstrates vulnerabilities when interacting with fee-on-transfer tokens
 *
 * Some tokens (like STA, PAXG) deduct fees during transfer.
 * If a contract assumes the full amount arrives, it can be exploited leading to:
 * - Incorrect accounting
 * - Insolvency
 * - Theft of funds
 *
 * REAL EXAMPLES: STA (Statera), PAXG (Paxos Gold)
 */

// Example fee-on-transfer token
contract FeeOnTransferToken {
    string public name = "FeeToken";
    string public symbol = "FEE";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    uint256 public constant FEE_PERCENT = 1; // 1% fee

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);

    constructor(uint256 _initialSupply) {
        totalSupply = _initialSupply;
        balanceOf[msg.sender] = _initialSupply;
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        uint256 fee = (amount * FEE_PERCENT) / 100;
        uint256 amountAfterFee = amount - fee;

        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amountAfterFee;
        balanceOf[address(0)] += fee;  // Burn fee

        emit Transfer(msg.sender, to, amountAfterFee);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        allowance[from][msg.sender] -= amount;

        uint256 fee = (amount * FEE_PERCENT) / 100;
        uint256 amountAfterFee = amount - fee;

        balanceOf[from] -= amount;
        balanceOf[to] += amountAfterFee;
        balanceOf[address(0)] += fee;

        emit Transfer(from, to, amountAfterFee);
        return true;
    }

    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }
}

// VULNERABLE: Vault assumes full amount arrives
contract VulnerableVault {
    mapping(address => mapping(address => uint256)) public deposits;

    function deposit(address token, uint256 amount) public {
        IERC20(token).transferFrom(msg.sender, address(this), amount);
        // PROBLEM: Credits user with full 'amount', but less arrived!
        deposits[msg.sender][token] += amount;
    }

    function withdraw(address token, uint256 amount) public {
        require(deposits[msg.sender][token] >= amount, "Insufficient balance");
        deposits[msg.sender][token] -= amount;
        IERC20(token).transfer(msg.sender, amount);
        // PROBLEM: Vault will become insolvent as it tracks more than it has!
    }
}

// SAFE: Check actual balance change
contract SafeVault {
    mapping(address => mapping(address => uint256)) public deposits;

    function deposit(address token, uint256 amount) public {
        uint256 balanceBefore = IERC20(token).balanceOf(address(this));
        IERC20(token).transferFrom(msg.sender, address(this), amount);
        uint256 balanceAfter = IERC20(token).balanceOf(address(this));

        uint256 actualReceived = balanceAfter - balanceBefore;
        deposits[msg.sender][token] += actualReceived;
    }

    function withdraw(address token, uint256 amount) public {
        require(deposits[msg.sender][token] >= amount, "Insufficient balance");
        deposits[msg.sender][token] -= amount;

        uint256 balanceBefore = IERC20(token).balanceOf(address(this));
        IERC20(token).transfer(msg.sender, amount);
        uint256 balanceAfter = IERC20(token).balanceOf(address(this));

        uint256 actualSent = balanceBefore - balanceAfter;
        // Verify the full amount was sent (accounting for potential fees)
        require(actualSent >= amount, "Transfer failed");
    }
}

// VULNERABLE: DEX assumes 1:1 transfer
contract VulnerableDEX {
    mapping(address => uint256) public reserves;

    function swap(address tokenIn, address tokenOut, uint256 amountIn) public {
        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        reserves[tokenIn] += amountIn;  // WRONG!

        uint256 amountOut = getAmountOut(amountIn, reserves[tokenIn], reserves[tokenOut]);
        reserves[tokenOut] -= amountOut;
        IERC20(tokenOut).transfer(msg.sender, amountOut);
    }

    function getAmountOut(uint256 amountIn, uint256 reserveIn, uint256 reserveOut) public pure returns (uint256) {
        return (amountIn * reserveOut) / reserveIn;
    }
}

// SAFE: DEX with balance check
contract SafeDEX {
    mapping(address => uint256) public reserves;

    function swap(address tokenIn, address tokenOut, uint256 amountIn) public {
        uint256 balanceBefore = IERC20(tokenIn).balanceOf(address(this));
        IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        uint256 balanceAfter = IERC20(tokenIn).balanceOf(address(this));

        uint256 actualAmountIn = balanceAfter - balanceBefore;
        reserves[tokenIn] += actualAmountIn;

        uint256 amountOut = getAmountOut(actualAmountIn, reserves[tokenIn], reserves[tokenOut]);
        reserves[tokenOut] -= amountOut;

        balanceBefore = IERC20(tokenOut).balanceOf(address(this));
        IERC20(tokenOut).transfer(msg.sender, amountOut);
        balanceAfter = IERC20(tokenOut).balanceOf(address(this));

        uint256 actualAmountOut = balanceBefore - balanceAfter;
        require(actualAmountOut >= amountOut, "Transfer failed");
    }

    function getAmountOut(uint256 amountIn, uint256 reserveIn, uint256 reserveOut) public pure returns (uint256) {
        return (amountIn * reserveOut) / reserveIn;
    }
}

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}
