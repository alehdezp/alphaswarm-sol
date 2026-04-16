// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ValueMovementIntegerIssues
 * @dev Demonstrates integer overflow/underflow and precision issues in value calculations
 *
 * While Solidity 0.8+ has built-in overflow protection, unsafe operations
 * (unchecked blocks) and precision loss can still cause value calculation issues.
 *
 * REAL EXAMPLES:
 * - BeautyChain (BEC) token overflow - $1M loss
 * - ProxyOverflow attack - Integer overflow in proxy contracts
 * - Precision loss in reward calculations
 * - Rounding errors in DeFi protocols
 *
 * REFERENCES:
 * - https://coinsbench.com/when-math-goes-mad-how-integer-overflows-turn-1-wei-into-1-million-eth-6fcb0930a895
 * - CWE-190: Integer Overflow
 * - CWE-191: Integer Underflow
 * - CWE-1339: Insufficient Precision
 */

// VULNERABLE: Unchecked math in critical calculations
contract VulnerableUncheckedMath {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        // SAFE: Default checked math
        balances[msg.sender] += msg.value;
    }

    function unsafeWithdraw(uint256 amount) external {
        // Unchecked block bypasses overflow protection
        unchecked {
            balances[msg.sender] -= amount; // Can underflow!
        }
        payable(msg.sender).transfer(amount);
    }

    function unsafeTransfer(address to, uint256 amount) external {
        unchecked {
            // Underflow could make balances[msg.sender] huge
            balances[msg.sender] -= amount;
            // Overflow could wrap around
            balances[to] += amount;
        }
    }
}

// SAFE: Use checked math for value operations
contract SafeCheckedMath {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        // SAFE: Checked addition
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        // SAFE: Checked subtraction - reverts on underflow
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    function transfer(address to, uint256 amount) external {
        // SAFE: Checked operations
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}

// VULNERABLE: Precision loss in reward calculations
contract VulnerablePrecisionLoss {
    uint256 public totalStaked;
    uint256 public rewardRate = 5; // 5% annual rate
    mapping(address => uint256) public stakes;
    mapping(address => uint256) public lastClaimTime;

    function stake() external payable {
        stakes[msg.sender] += msg.value;
        totalStaked += msg.value;
        lastClaimTime[msg.sender] = block.timestamp;
    }

    function claimRewards() external {
        uint256 timeElapsed = block.timestamp - lastClaimTime[msg.sender];
        uint256 stakedAmount = stakes[msg.sender];

        // Division before multiplication causes precision loss
        // Small stakes may receive 0 rewards due to rounding down
        uint256 reward = (stakedAmount / 100) * rewardRate * (timeElapsed / 365 days);

        lastClaimTime[msg.sender] = block.timestamp;
        payable(msg.sender).transfer(reward);
    }
}

// SAFE: Use scaling factor to preserve precision
contract SafePrecisionPreserved {
    uint256 public constant PRECISION = 1e18;
    uint256 public totalStaked;
    uint256 public rewardRate = 5 * PRECISION / 100; // 5% with precision
    mapping(address => uint256) public stakes;
    mapping(address => uint256) public lastClaimTime;

    function stake() external payable {
        stakes[msg.sender] += msg.value;
        totalStaked += msg.value;
        lastClaimTime[msg.sender] = block.timestamp;
    }

    function claimRewards() external {
        uint256 timeElapsed = block.timestamp - lastClaimTime[msg.sender];
        uint256 stakedAmount = stakes[msg.sender];

        // SAFE: Multiply before divide to preserve precision
        uint256 reward = (stakedAmount * rewardRate * timeElapsed) / (365 days * PRECISION);

        lastClaimTime[msg.sender] = block.timestamp;
        payable(msg.sender).transfer(reward);
    }
}

// VULNERABLE: Percentage calculation with precision loss
contract VulnerableFeeCalculation {
    uint256 public feePercent = 25; // 0.25% fee

    function swap(uint256 amountIn) external view returns (uint256) {
        // Fee calculation loses precision for small amounts
        // 100 * 25 / 10000 = 0 (rounds down to zero)
        uint256 fee = (amountIn * feePercent) / 10000;
        return amountIn - fee;
    }

    function calculateFee(uint256 amount) external view returns (uint256) {
        // PROBLEM: Small amounts return 0 fee
        return (amount * feePercent) / 10000;
    }
}

// SAFE: Use basis points with proper scaling
contract SafeFeeCalculation {
    uint256 public constant FEE_DENOMINATOR = 10000;
    uint256 public feePercent = 25; // 25 basis points = 0.25%

    function swap(uint256 amountIn) external view returns (uint256 amountOut) {
        // SAFE: Proper fee calculation with explicit checks
        uint256 fee = (amountIn * feePercent + FEE_DENOMINATOR - 1) / FEE_DENOMINATOR; // Round up
        amountOut = amountIn - fee;
    }

    function calculateFee(uint256 amount) external view returns (uint256) {
        // SAFE: Round up to ensure fee is never 0 when it should apply
        return (amount * feePercent + FEE_DENOMINATOR - 1) / FEE_DENOMINATOR;
    }
}

// VULNERABLE: Share calculation rounding
contract VulnerableShareRounding {
    uint256 public totalShares;
    uint256 public totalAssets;
    mapping(address => uint256) public shares;

    function deposit(uint256 assets) external {
        uint256 sharesToMint;
        if (totalShares == 0) {
            sharesToMint = assets;
        } else {
            // Can round down to 0 for small deposits
            sharesToMint = (assets * totalShares) / totalAssets;
        }

        shares[msg.sender] += sharesToMint;
        totalShares += sharesToMint;
        totalAssets += assets;
    }

    function withdraw(uint256 sharesToBurn) external {
        // Can round down, user loses value
        uint256 assets = (sharesToBurn * totalAssets) / totalShares;

        shares[msg.sender] -= sharesToBurn;
        totalShares -= sharesToBurn;
        totalAssets -= assets;
    }
}

// SAFE: Prevent zero-share minting and enforce minimums
contract SafeShareRounding {
    uint256 public totalShares;
    uint256 public totalAssets;
    uint256 public constant MIN_DEPOSIT = 1000; // Minimum deposit to prevent rounding issues
    mapping(address => uint256) public shares;

    function deposit(uint256 assets) external {
        require(assets >= MIN_DEPOSIT, "Deposit too small");

        uint256 sharesToMint;
        if (totalShares == 0) {
            sharesToMint = assets;
        } else {
            sharesToMint = (assets * totalShares) / totalAssets;
            // SAFE: Ensure shares are actually minted
            require(sharesToMint > 0, "Deposit too small for shares");
        }

        shares[msg.sender] += sharesToMint;
        totalShares += sharesToMint;
        totalAssets += assets;
    }

    function withdraw(uint256 sharesToBurn) external {
        uint256 assets = (sharesToBurn * totalAssets) / totalShares;
        // SAFE: Ensure user gets something back
        require(assets > 0, "Withdrawal too small");

        shares[msg.sender] -= sharesToBurn;
        totalShares -= sharesToBurn;
        totalAssets -= assets;
    }
}

// VULNERABLE: Cast from larger to smaller type
contract VulnerableTypeCast {
    function convertAmount(uint256 largeAmount) external pure returns (uint128) {
        // Silently truncates if largeAmount > type(uint128).max
        return uint128(largeAmount);
    }

    function storeAmount(uint256 amount) external pure returns (uint64) {
        // Unsafe downcast
        return uint64(amount);
    }
}

// SAFE: Check bounds before casting
contract SafeTypeCast {
    function convertAmount(uint256 largeAmount) external pure returns (uint128) {
        // SAFE: Check bounds before casting
        require(largeAmount <= type(uint128).max, "Amount too large");
        return uint128(largeAmount);
    }

    function storeAmount(uint256 amount) external pure returns (uint64) {
        // SAFE: Explicit bounds check
        require(amount <= type(uint64).max, "Amount exceeds uint64");
        return uint64(amount);
    }
}

// VULNERABLE: Multiplication before validation
contract VulnerableMultiplication {
    function calculateTotal(uint256 price, uint256 quantity) external pure returns (uint256) {
        // Multiplication could overflow in unchecked context
        unchecked {
            return price * quantity;
        }
    }

    function allocate(uint256 perUser, uint256 userCount) external pure returns (uint256) {
        unchecked {
            // Could overflow
            return perUser * userCount;
        }
    }
}

// SAFE: Check for overflow before multiplication
contract SafeMultiplication {
    function calculateTotal(uint256 price, uint256 quantity) external pure returns (uint256) {
        // SAFE: Checked multiplication in Solidity 0.8+
        return price * quantity; // Reverts on overflow
    }

    function allocate(uint256 perUser, uint256 userCount) external pure returns (uint256) {
        // SAFE: Explicit overflow check before unchecked block
        require(userCount == 0 || perUser <= type(uint256).max / userCount, "Overflow");
        return perUser * userCount;
    }
}
