# Rounding Direction Fixes

## Remediation Approaches

### 1. Explicit Rounding Direction (High Effectiveness)

**Fix**: Always specify rounding direction explicitly based on security model.

**Rule**: Round in favor of the protocol, not the user.

```solidity
// For user withdrawals: round DOWN (user gets less, protocol protected)
function convertToAssets(uint shares) public view returns (uint) {
    uint supply = totalSupply();
    // Round down: user receives less
    return shares * totalAssets() / supply;
}

// For protocol deposits: round UP (protocol gets more value)
function convertToShares(uint assets) public view returns (uint) {
    uint supply = totalSupply();
    uint result = assets * supply;
    // Round up: (a + (b-1)) / b
    return (result + totalAssets() - 1) / totalAssets();
}
```

**Operations**: `ROUNDS_EXPLICIT` → `FAVORS_PROTOCOL`

**Library Recommendation**:
- OpenZeppelin's `Math.Rounding` enum
- Solady's `FixedPointMathLib.mulDivUp/mulDivDown`
- PRBMath's explicit rounding functions

### 2. Minimum Thresholds (High Effectiveness)

**Fix**: Implement minimum deposit/withdrawal amounts.

```solidity
uint constant MIN_DEPOSIT = 1e6;   // 1 USDC minimum
uint constant MIN_WITHDRAW = 1e6;  // 1 USDC minimum

function deposit(uint assets) external {
    require(assets >= MIN_DEPOSIT, "Below minimum");
    require(assets > 0 && shares > 0, "Zero amount");

    uint shares = convertToShares(assets);
    require(shares >= 1e3, "Dust shares");  // Minimum 0.001 shares

    MINTS_SHARES(msg.sender, shares);
}
```

**Safe Properties**:
- Prevents dust-level manipulations
- Ensures meaningful rounding behavior
- Blocks accumulation attacks

### 3. Balanced Pair of Rounding libraries (Medium Effectiveness)

**Fix**: Use safe math libraries with explicit rounding.

```solidity
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

function withdraw(uint shares) external {
    // Round DOWN for user withdrawals (protocol favor)
    uint assets = shares.mulDiv(totalAssets(), totalSupply(), Math.Rounding.Floor);

    require(assets > 0, "Zero withdrawal");
    BURNS_SHARES(msg.sender, shares);
    TRANSFERS_ASSETS(msg.sender, assets);
}
```

**Libraries**:
- OpenZeppelin `Math.mulDiv` with `Rounding` parameter
- Solady `FixedPointMathLib.mulDivUp/Down`
- PRBMath for advanced fixed-point arithmetic

### 4. Scaling Factor Validation (Medium Effectiveness)

**Fix**: Validate and bound scaling factors.

```solidity
uint constant MAX_SCALING_FACTOR = 1e36;
uint constant MIN_SCALING_FACTOR = 1e6;

function setScalingFactor(uint newFactor) external onlyAdmin {
    require(newFactor >= MIN_SCALING_FACTOR, "Too small");
    require(newFactor <= MAX_SCALING_FACTOR, "Too large");

    scalingFactor = newFactor;
}

function scaleAmount(uint amount) internal view returns (uint) {
    // Explicit rounding up
    return Math.mulDiv(amount, scalingFactor, 1e18, Math.Rounding.Ceil);
}
```

**Safe Properties**:
- Bounds prevent extreme scaling
- Explicit rounding direction
- Admin-only updates with validation

### 5. Donation Prevention (High Effectiveness)

**Fix**: Track internal accounting separately from token balances.

```solidity
// Internal accounting - separate from actual token balance
uint private internalBalance;

function deposit(uint amount) external {
    TRANSFERS_TOKEN_IN(msg.sender, amount);

    // Use internal balance, not token.balanceOf(this)
    uint shares = amount * totalSupply() / internalBalance;

    internalBalance += amount;  // Update internal tracking
    MINTS_SHARES(msg.sender, shares);
}

// Donations don't affect calculations
function actualBalance() public view returns (uint) {
    return token.balanceOf(address(this));
}
```

**Safe Properties**:
- Separates accounting from actual balances
- Prevents donation-based manipulation
- Can detect and handle excess tokens separately

## Audit Checklist

- [ ] All division operations have explicit rounding direction
- [ ] Rounding favors protocol security (not user benefit)
- [ ] Minimum thresholds prevent dust-level exploits
- [ ] Scaling factors are bounded and validated
- [ ] Internal accounting separated from token balances
- [ ] Zero-amount checks on all calculations
- [ ] Edge cases tested: empty pool, large numbers, dust amounts
- [ ] Fuzzing performed on rounding-sensitive functions
