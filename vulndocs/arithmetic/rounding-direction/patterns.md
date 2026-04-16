# Rounding Direction Patterns

## Vulnerable Pattern: Implicit Rounding Down

### Code Structure (Semantic)

```solidity
// VULNERABLE: Rounding down in value calculation
// Read pool state
uint totalAssets = READS_POOL_STATE();
uint totalSupply = READS_SUPPLY();

// Division rounds down implicitly
uint userAmount = depositedShares * totalAssets / totalSupply;  // DANGEROUS

// Transfer calculated amount
TRANSFERS_VALUE_OUT(user, userAmount);
```

**Operations**: `READS_POOL_STATE` → `PERFORMS_DIVISION` → `TRANSFERS_VALUE_OUT`

**Signature**: `R:supply->DIV:down->T:out`

**Why Vulnerable**:
- Division rounds down by default in Solidity
- User receives less than entitled (protocol gains)
- OR user receives more than entitled (protocol loses)
- Direction depends on context - both are dangerous

## Vulnerable Pattern: Scaling Without Rounding Control

### Code Structure (Semantic)

```solidity
// VULNERABLE: Scaling factor without rounding specification
function scaleAmount(uint amount, uint scalingFactor) internal pure returns (uint) {
    // Rounds down: amount * scalingFactor / 1e18
    return amount * scalingFactor / 1e18;  // DANGEROUS
}

// Usage in withdrawal
uint scaledAmount = scaleAmount(withdrawAmount, pool.scalingFactor);
TRANSFERS_VALUE_OUT(user, scaledAmount);
```

**Operations**: `READS_SCALING_FACTOR` → `PERFORMS_MULTIPLICATION` → `PERFORMS_DIVISION` → `TRANSFERS_VALUE_OUT`

**Why Vulnerable**:
- No explicit rounding direction
- Attacker can manipulate scaling factor via donations
- Accumulation of rounding errors across transactions

## Safe Pattern: Explicit Rounding Up (Protocol Favor)

### Code Structure (Semantic)

```solidity
// SAFE: Explicit rounding up for withdrawals (protocol favor)
function scaleAmountUp(uint amount, uint scalingFactor) internal pure returns (uint) {
    uint result = amount * scalingFactor;
    // Round up: (a + (b-1)) / b
    return (result + 1e18 - 1) / 1e18;
}

// Safe withdrawal
uint scaledAmount = scaleAmountUp(withdrawAmount, pool.scalingFactor);
require(scaledAmount <= maxWithdrawable, "Exceeds limit");
TRANSFERS_VALUE_OUT(user, scaledAmount);
```

**Operations**: `READS_SCALING_FACTOR` → `PERFORMS_MULTIPLICATION` → `ROUNDS_UP` → `CHECKS_LIMIT` → `TRANSFERS_VALUE_OUT`

**Signature**: `R:scale->MUL->ROUND_UP->CHECK->T:out`

**Safe Properties**:
- Explicit rounding up protects protocol
- Maximum withdrawal check prevents over-transfer
- Clear rounding direction in code

## Safe Pattern: Minimum Threshold

### Code Structure (Semantic)

```solidity
// SAFE: Minimum threshold prevents dust exploitation
uint constant MIN_DEPOSIT = 1e6;  // Minimum 1 USDC

function deposit(uint amount) external {
    require(amount >= MIN_DEPOSIT, "Below minimum");

    uint shares = amount * totalSupply() / totalAssets();
    require(shares > 0, "Zero shares");  // Additional safety

    MINTS_SHARES(msg.sender, shares);
}
```

**Safe Properties**:
- Minimum deposit threshold prevents dust attacks
- Zero-share check ensures meaningful transactions
- Prevents rounding-to-zero exploits

## Variation: Decimal Mismatch Rounding

### Vulnerable Code (Semantic)

```solidity
// VULNERABLE: Token decimal mismatch without proper rounding
// token0: 18 decimals, token1: 6 decimals
uint token0Amount = READS_BALANCE_TOKEN0();  // 1e18 precision
uint token1Amount = READS_BALANCE_TOKEN1();  // 1e6 precision

// Incorrect scaling: loses precision
uint normalizedAmount = token1Amount * 1e18 / 1e6;  // DANGEROUS
```

**Why Vulnerable**:
- Decimal scaling without rounding consideration
- Precision loss can be exploited
- Different tokens have different rounding impacts
