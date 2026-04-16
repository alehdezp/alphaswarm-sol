// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title BlacklistPausableTokens
 * @dev Demonstrates vulnerabilities with blacklist and pausable tokens
 *
 * Tokens like USDC and USDT have centralized blacklist and pause
 * mechanisms. Contracts that don't account for this can:
 * - Lock user funds permanently
 * - Fail to execute critical operations
 * - Experience DoS
 *
 * REAL EXAMPLES:
 * - USDC: Can blacklist addresses and pause transfers
 * - USDT: Can blacklist and pause
 * - Many others with admin controls
 */

// Example blacklist token (like USDC/USDT)
contract BlacklistToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => bool) public isBlacklisted;
    bool public paused;
    address public admin;

    modifier notBlacklisted(address account) {
        require(!isBlacklisted[account], "Address blacklisted");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "Token paused");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function transfer(address to, uint256 amount)
        public
        notBlacklisted(msg.sender)
        notBlacklisted(to)
        whenNotPaused
        returns (bool)
    {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function blacklist(address account) public {
        require(msg.sender == admin, "Not admin");
        isBlacklisted[account] = true;
    }

    function pause() public {
        require(msg.sender == admin, "Not admin");
        paused = true;
    }

    function mint(address to, uint256 amount) public {
        balanceOf[to] += amount;
    }
}

// VULNERABLE: Vault doesn't handle blacklisted users
contract VulnerableVaultBlacklist {
    mapping(address => uint256) public deposits;
    BlacklistToken public token;

    constructor(address _token) {
        token = BlacklistToken(_token);
    }

    function deposit(uint256 amount) public {
        token.transfer(address(this), amount);
        deposits[msg.sender] += amount;
    }

    function withdraw(uint256 amount) public {
        require(deposits[msg.sender] >= amount, "Insufficient balance");
        deposits[msg.sender] -= amount;

        // PROBLEM: If msg.sender is blacklisted, this will fail!
        // User's funds are permanently locked in the contract
        token.transfer(msg.sender, amount);
    }

    // PROBLEM: If contract itself gets blacklisted, everyone's funds are locked!
}

// SAFE: Vault with withdrawal to alternate address
contract SafeVaultBlacklist {
    mapping(address => uint256) public deposits;
    BlacklistToken public token;

    constructor(address _token) {
        token = BlacklistToken(_token);
    }

    function deposit(uint256 amount) public {
        token.transfer(address(this), amount);
        deposits[msg.sender] += amount;
    }

    // Allow withdrawal to different address in case user is blacklisted
    function withdraw(uint256 amount, address recipient) public {
        require(deposits[msg.sender] >= amount, "Insufficient balance");
        deposits[msg.sender] -= amount;

        // Try to send to recipient
        // User can specify non-blacklisted address
        token.transfer(recipient, amount);
    }

    // Emergency withdrawal with try-catch
    function emergencyWithdraw(uint256 amount, address recipient) public {
        require(deposits[msg.sender] >= amount, "Insufficient balance");

        try token.transfer(recipient, amount) returns (bool success) {
            if (success) {
                deposits[msg.sender] -= amount;
            } else {
                revert("Transfer failed");
            }
        } catch {
            // Token transfer failed (blacklist or pause)
            // Keep deposit intact, user can try again later with different address
            revert("Transfer blocked - try different recipient or wait for unpause");
        }
    }
}

// VULNERABLE: DEX pool with blacklist token
contract VulnerableDEXBlacklist {
    BlacklistToken public token0;
    address public token1;
    uint256 public reserve0;
    uint256 public reserve1;

    constructor(address _token0, address _token1) {
        token0 = BlacklistToken(_token0);
        token1 = _token1;
    }

    function swap(uint256 amount0In, uint256 amount1Out) public {
        if (amount0In > 0) {
            // PROBLEM: If pool gets blacklisted, all swaps fail - total DoS!
            token0.transfer(address(this), amount0In);
            reserve0 += amount0In;
        }

        if (amount1Out > 0) {
            reserve1 -= amount1Out;
            // Transfer token1
        }
    }

    function addLiquidity(uint256 amount0, uint256 amount1) public {
        // PROBLEM: If token paused, liquidity provision fails
        token0.transfer(address(this), amount0);
        reserve0 += amount0;
    }

    // PROBLEM: No emergency withdrawal if contract blacklisted
}

// SAFE: DEX with pause detection and emergency mode
contract SafeDEXBlacklist {
    BlacklistToken public token0;
    address public token1;
    uint256 public reserve0;
    uint256 public reserve1;
    bool public emergencyMode;
    address public admin;

    mapping(address => uint256) public emergencyBalance0;
    mapping(address => uint256) public emergencyBalance1;

    constructor(address _token0, address _token1) {
        token0 = BlacklistToken(_token0);
        token1 = _token1;
        admin = msg.sender;
    }

    function enableEmergencyMode() public {
        require(msg.sender == admin, "Not admin");
        emergencyMode = true;
    }

    function swap(uint256 amount0In, uint256 amount1Out) public {
        require(!emergencyMode, "Emergency mode active");

        if (amount0In > 0) {
            // Try-catch to detect blacklist/pause
            try token0.transfer(address(this), amount0In) returns (bool success) {
                require(success, "Transfer failed");
                reserve0 += amount0In;
            } catch {
                // Token transfer failed - enter emergency mode
                emergencyMode = true;
                revert("Token blocked - emergency mode activated");
            }
        }
    }

    // Emergency withdrawal if pool is blacklisted/paused
    function emergencyWithdrawLP(address recipient) public {
        require(emergencyMode, "Not in emergency mode");

        // Calculate user's share and allow withdrawal
        // This allows recovery even if token is blocked
    }
}

// VULNERABLE: Lending protocol with pausable collateral
contract VulnerableLendingPausable {
    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debt;
    BlacklistToken public collateralToken;

    constructor(address _collateral) {
        collateralToken = BlacklistToken(_collateral);
    }

    function depositCollateral(uint256 amount) public {
        collateralToken.transfer(address(this), amount);
        collateral[msg.sender] += amount;
    }

    function liquidate(address user) public {
        require(isUnderCollateralized(user), "Not under-collateralized");

        uint256 collateralAmount = collateral[user];
        collateral[user] = 0;

        // PROBLEM: If token is paused or liquidator is blacklisted,
        // liquidation fails and protocol becomes insolvent!
        collateralToken.transfer(msg.sender, collateralAmount);
    }

    function isUnderCollateralized(address user) public view returns (bool) {
        return debt[user] > collateral[user];
    }
}

// SAFE: Lending with alternative liquidation
contract SafeLendingPausable {
    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debt;
    mapping(address => uint256) public pendingLiquidationRewards;
    BlacklistToken public collateralToken;

    function liquidate(address user) public {
        require(isUnderCollateralized(user), "Not under-collateralized");

        uint256 collateralAmount = collateral[user];
        collateral[user] = 0;

        // Try to transfer collateral
        try collateralToken.transfer(msg.sender, collateralAmount) returns (bool success) {
            require(success, "Transfer failed");
        } catch {
            // Token blocked - record pending reward
            // Liquidator can claim later when token is unpaused
            pendingLiquidationRewards[msg.sender] += collateralAmount;
        }
    }

    function claimPendingRewards() public {
        uint256 pending = pendingLiquidationRewards[msg.sender];
        require(pending > 0, "No pending rewards");

        pendingLiquidationRewards[msg.sender] = 0;
        collateralToken.transfer(msg.sender, pending);
    }

    function isUnderCollateralized(address user) public view returns (bool) {
        return debt[user] > collateral[user];
    }
}

// VULNERABLE: Using blacklist token as fee payment
contract VulnerableFeesBlacklist {
    BlacklistToken public feeToken;

    function performAction() public {
        // PROBLEM: If user is blacklisted, they can't pay fees
        // Function becomes inaccessible to them
        feeToken.transfer(address(this), 100);

        // Perform action
    }
}

// SAFE: Alternative payment method
contract SafeFeesBlacklist {
    BlacklistToken public feeToken;

    function performAction() public payable {
        // Try token payment first
        try feeToken.transfer(address(this), 100) returns (bool success) {
            require(success, "Token transfer failed");
        } catch {
            // Token blocked - accept ETH payment instead
            require(msg.value >= 0.01 ether, "Insufficient ETH payment");
        }

        // Perform action
    }
}
