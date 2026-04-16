// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title RebasingToken
 * @dev Demonstrates vulnerabilities when interacting with rebasing tokens
 *
 * Rebasing tokens (like AMPL, stETH) change balances automatically
 * through supply adjustments or share mechanisms. Contracts that store balance
 * snapshots can experience:
 * - Insolvency (if balance decreases)
 * - Accounting errors
 * - Loss of rebase rewards
 *
 * REAL EXAMPLES:
 * - AMPL (Ampleforth): Daily supply adjustments
 * - stETH (Lido): Rebases as staking rewards accumulate
 * - aTokens (Aave): Continuously accrue interest
 */

// Simplified rebasing token (like AMPL)
contract RebasingToken {
    string public name = "Rebase Token";
    string public symbol = "REBASE";

    uint256 public totalSupply;
    mapping(address => uint256) private _shares;
    uint256 private _totalShares;

    event Rebase(uint256 newTotalSupply);

    constructor(uint256 _initialSupply) {
        totalSupply = _initialSupply;
        _totalShares = _initialSupply;
        _shares[msg.sender] = _initialSupply;
    }

    // Balance changes as totalSupply rebases!
    function balanceOf(address account) public view returns (uint256) {
        if (_totalShares == 0) return 0;
        return (_shares[account] * totalSupply) / _totalShares;
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        uint256 sharesToTransfer = (amount * _totalShares) / totalSupply;
        _shares[msg.sender] -= sharesToTransfer;
        _shares[to] += sharesToTransfer;
        return true;
    }

    // Simulate rebase (can increase or decrease)
    function rebase(int256 supplyDelta) public {
        if (supplyDelta > 0) {
            totalSupply += uint256(supplyDelta);
        } else {
            totalSupply -= uint256(-supplyDelta);
        }
        emit Rebase(totalSupply);
    }

    function sharesOf(address account) public view returns (uint256) {
        return _shares[account];
    }
}

// VULNERABLE: Vault stores balance snapshot
contract VulnerableRebasingVault {
    mapping(address => mapping(address => uint256)) public deposits;

    function deposit(address token, uint256 amount) public {
        RebasingToken(token).transfer(address(this), amount);
        // PROBLEM: Stores amount, but actual balance will change due to rebases!
        deposits[msg.sender][token] += amount;
    }

    function withdraw(address token, uint256 amount) public {
        require(deposits[msg.sender][token] >= amount, "Insufficient balance");
        deposits[msg.sender][token] -= amount;
        // PROBLEM: Contract may not have enough tokens if negative rebase occurred!
        RebasingToken(token).transfer(msg.sender, amount);
    }

    // After negative rebase, this will fail or drain other users' funds
}

// SAFE: Vault tracks shares instead of balance
contract SafeRebasingVault {
    mapping(address => mapping(address => uint256)) public userShares;
    mapping(address => uint256) public totalShares;

    function deposit(address token, uint256 amount) public {
        uint256 balanceBefore = RebasingToken(token).balanceOf(address(this));
        RebasingToken(token).transfer(address(this), amount);
        uint256 balanceAfter = RebasingToken(token).balanceOf(address(this));

        uint256 actualReceived = balanceAfter - balanceBefore;

        // Convert to shares
        uint256 shares;
        if (totalShares[token] == 0) {
            shares = actualReceived;
        } else {
            shares = (actualReceived * totalShares[token]) / balanceBefore;
        }

        userShares[msg.sender][token] += shares;
        totalShares[token] += shares;
    }

    function withdraw(address token, uint256 shares) public {
        require(userShares[msg.sender][token] >= shares, "Insufficient shares");

        uint256 totalBalance = RebasingToken(token).balanceOf(address(this));
        uint256 amount = (shares * totalBalance) / totalShares[token];

        userShares[msg.sender][token] -= shares;
        totalShares[token] -= shares;

        RebasingToken(token).transfer(msg.sender, amount);
    }

    function balanceOf(address user, address token) public view returns (uint256) {
        if (totalShares[token] == 0) return 0;
        uint256 totalBalance = RebasingToken(token).balanceOf(address(this));
        return (userShares[user][token] * totalBalance) / totalShares[token];
    }
}

// VULNERABLE: Using rebasing token as collateral without understanding mechanics
contract VulnerableLending {
    mapping(address => uint256) public collateral;
    mapping(address => uint256) public borrowed;

    function depositCollateral(address rebasingToken, uint256 amount) public {
        RebasingToken(rebasingToken).transfer(address(this), amount);
        collateral[msg.sender] += amount;
    }

    function borrow(uint256 amount) public {
        require(collateral[msg.sender] >= amount * 2, "Insufficient collateral");
        borrowed[msg.sender] += amount;
        // Send borrowed amount
    }

    // PROBLEM: If rebase is negative, collateral value drops but our
    // accounting doesn't reflect it - under-collateralized positions!
}

// VULNERABLE: LP token with rebasing asset
contract VulnerableRebasingLP {
    address public rebasingToken;
    address public stableToken;
    uint256 public rebasingReserve;
    uint256 public stableReserve;

    function addLiquidity(uint256 rebasingAmount, uint256 stableAmount) public {
        RebasingToken(rebasingToken).transfer(address(this), rebasingAmount);
        // PROBLEM: Reserve value will change due to rebases!
        rebasingReserve += rebasingAmount;
        stableReserve += stableAmount;
    }

    // Swap calculations will be wrong after rebase!
}

// SAFE: Sync reserves before operations
contract SafeRebasingLP {
    address public rebasingToken;
    address public stableToken;
    uint256 public rebasingReserve;
    uint256 public stableReserve;

    function sync() public {
        rebasingReserve = RebasingToken(rebasingToken).balanceOf(address(this));
        // stableReserve doesn't need sync
    }

    function addLiquidity(uint256 rebasingAmount, uint256 stableAmount) public {
        sync();  // Update reserves before operation
        RebasingToken(rebasingToken).transfer(address(this), rebasingAmount);
        rebasingReserve = RebasingToken(rebasingToken).balanceOf(address(this));
        stableReserve += stableAmount;
    }

    function swap() public {
        sync();  // Always sync before operations
        // Now calculations use actual current balances
    }
}
