# Detection: Precision Accounting Vulnerabilities

**Subcategory**: logic/precision-accounting
**Severity**: High
**Pattern ID**: log-008 (to be created)
**Discovered**: 2026-01-09 via Sherlock AI ($2M prevented)

---

## Overview

Precision accounting vulnerabilities occur when integer division causes rounding that creates accounting inconsistencies between internal ledger and actual token transfers. Attackers exploit this by executing thousands of micro-operations where:
1. Internal accounting rounds down to zero (no deduction)
2. Actual tokens are still transferred (value flows out)
3. Accounting drift accumulates until reserves are drained

**Key Characteristic**: The vulnerability is only exploitable through LOOP AMPLIFICATION. Single operations may be economically insignificant, but mass repetition creates profitable attack.

---

## Graph Signals

| Property | Expected | Critical? | Description |
|----------|----------|-----------|-------------|
| `uses_integer_division` | `true` | YES | Function performs division (scaling) |
| `precision_loss_possible` | `true` | YES | Result can round to zero (NEW PROPERTY) |
| `transfers_value_out` | `true` | YES | Transfers tokens/value after scaling |
| `accounting_validation` | `false` | YES | No post-transfer balance check |
| `allows_micro_operations` | `true` | YES | No minimum operation threshold (NEW PROPERTY) |
| `loop_potential` | `true` | NO | Function can be called repeatedly |
| `visibility` | `["public", "external"]` | YES | Externally callable |

---

## Operation Sequences

### VULNERABLE Pattern
```
R:bal → SCALE_DOWN(value / factor → 0) → W:bal (no-op) → X:out(original value)
```

**Behavioral Signature**: `R:bal→SCALE_DOWN(→0)→W:bal(no-op)→X:out(actual)`

**Attack Flow**:
1. User calls withdraw with very small amount (e.g., 1 wei)
2. Function converts face value to "scaled units" via division
3. Result rounds down to 0 (1 wei / 1e18 = 0)
4. Internal balance decremented by 0 (no change)
5. Actual tokens transferred (1 wei sent)
6. Repeat 1,000,000 times → drain reserves

### SAFE Pattern
```
require(amount >= MINIMUM_THRESHOLD);
R:bal → SCALE_DOWN(value / factor) → W:bal(scaled) → VALIDATE_CONSISTENCY → X:out
```

**Safety Mechanisms**:
- Enforce minimum operation amount
- Validate internal balance matches actual balance
- Use higher precision accounting (e.g., fixed-point)
- Round UP for debits, DOWN for credits
- Add consistency checks after transfer

---

## Real-World Detection: Sherlock AI

**Date**: October 1, 2025
**Loss**: $2M (prevented)
**Source**: [Sherlock AI Blog](https://sherlock.xyz/post/how-sherlock-ai-uncovered-a-2m-vulnerability-before-launch)

**Vulnerability**:
```solidity
// VULNERABLE: Withdrawal with scaling
function withdraw(uint256 faceValue) external {
    // Convert face value to scaled units (internal ledger)
    uint256 scaledAmount = faceValue / SCALE_FACTOR; // Can round to 0!

    // Update internal balance (may be 0 deduction)
    balances[msg.sender] -= scaledAmount; // No-op if scaledAmount == 0

    // Transfer actual tokens (uses original faceValue)
    token.transfer(msg.sender, faceValue); // Still transfers!
}
```

**Attack Steps**:
1. Attacker calls `withdraw(1)` (1 wei)
2. `scaledAmount = 1 / 1e18 = 0` (rounds down)
3. `balances[msg.sender] -= 0` (balance unchanged)
4. `token.transfer(msg.sender, 1)` (1 wei transferred)
5. Loop 1,000,000 times → drain 1M wei from reserves
6. Scale up attack size as reserves deplete

**Root Cause**:
- Integer division with large scale factor
- No minimum withdrawal amount
- Accounting uses scaled value, transfer uses face value
- No consistency check between internal balance and actual balance

---

## Mathematical Analysis

### Precision Loss Calculation

For scaling factor `S` and withdrawal amount `W`:
- Internal deduction: `floor(W / S)`
- Actual transfer: `W`
- Accounting drift: `W - floor(W / S) * S`

**Example** (S = 1e18):
| W | floor(W/S) | Actual | Drift |
|---|------------|--------|-------|
| 1 | 0 | 1 | 1 |
| 1e17 | 0 | 1e17 | 1e17 |
| 1e18-1 | 0 | 1e18-1 | 1e18-1 |
| 1e18 | 1 | 1e18 | 0 |

**Attack Profitability**:
- Gas cost per call: ~30K gas
- Value extracted per call: `W` (where `floor(W/S) = 0`)
- Break-even: `W > gas_cost * gas_price`
- Maximum drift per call: `S - 1`

### Amplification Factor

For `N` calls with `W = S - 1`:
- Total extracted: `N * (S - 1)`
- Total accounting drift: `N * (S - 1)`
- Gas cost: `N * 30K * gas_price`

**Realistic Attack** (ETH, 50 gwei gas):
- `N = 10,000` calls
- Extract: `10,000 * 0.999 ETH = 9,990 ETH`
- Gas cost: `10,000 * 30K * 50 = 15 ETH`
- Profit: `9,975 ETH (~$20M at $2K/ETH)`

---

## False Positive Indicators

1. **Minimum Amount Enforced**:
   ```solidity
   require(amount >= MINIMUM_AMOUNT, "too small");
   ```

2. **Consistency Validation**:
   ```solidity
   uint balanceBefore = token.balanceOf(address(this));
   // ... operations ...
   uint balanceAfter = token.balanceOf(address(this));
   require(balanceAfter == balanceBefore - amount);
   ```

3. **Scaled Transfer**:
   ```solidity
   uint256 scaledAmount = amount / SCALE;
   balances[msg.sender] -= scaledAmount;
   token.transfer(msg.sender, scaledAmount * SCALE); // Transfer scaled value
   ```

4. **Higher Precision Accounting**:
   ```solidity
   // Use 256-bit fixed point instead of integer division
   uint256 scaledAmount = (amount * PRECISION) / SCALE;
   balances[msg.sender] -= scaledAmount;
   ```

5. **Round Up for Debits**:
   ```solidity
   // Round UP when calculating user debit
   uint256 scaledAmount = (amount + SCALE - 1) / SCALE;
   ```

---

## Detection Checklist

- [ ] Function performs division (scaling operation)?
- [ ] Division result can round to zero for small inputs?
- [ ] Transfers actual value (not scaled value)?
- [ ] Internal accounting uses scaled value?
- [ ] No minimum amount threshold enforced?
- [ ] No post-transfer balance validation?
- [ ] Function publicly callable?
- [ ] Can be called repeatedly without rate limit?

**If 6+ checks are YES** → HIGH CONFIDENCE precision accounting vulnerability

---

## Recommended Fixes

### Fix 1: Enforce Minimum Amount (Best)
```solidity
uint256 constant MINIMUM_AMOUNT = 1e16; // 0.01 ETH

function withdraw(uint256 amount) external {
    require(amount >= MINIMUM_AMOUNT, "amount too small");
    uint256 scaledAmount = amount / SCALE_FACTOR;
    balances[msg.sender] -= scaledAmount;
    token.transfer(msg.sender, amount);
}
```

### Fix 2: Consistency Validation
```solidity
function withdraw(uint256 amount) external {
    uint256 balanceBefore = token.balanceOf(address(this));
    uint256 scaledAmount = amount / SCALE_FACTOR;

    balances[msg.sender] -= scaledAmount;
    token.transfer(msg.sender, amount);

    uint256 balanceAfter = token.balanceOf(address(this));
    require(balanceAfter >= balanceBefore - amount, "accounting inconsistency");
}
```

### Fix 3: Transfer Scaled Value
```solidity
function withdraw(uint256 faceValue) external {
    uint256 scaledAmount = faceValue / SCALE_FACTOR;
    require(scaledAmount > 0, "rounds to zero");

    balances[msg.sender] -= scaledAmount;
    // Transfer scaled value (consistent with accounting)
    uint256 actualAmount = scaledAmount * SCALE_FACTOR;
    token.transfer(msg.sender, actualAmount);
}
```

### Fix 4: Round Up for Debits
```solidity
function withdraw(uint256 amount) external {
    // Round UP when debiting user
    uint256 scaledAmount = (amount + SCALE_FACTOR - 1) / SCALE_FACTOR;
    require(scaledAmount > 0, "rounds to zero");

    balances[msg.sender] -= scaledAmount;
    token.transfer(msg.sender, amount);
}
```

---

## Related Vulnerabilities

- **Rounding Errors** (general): Integer division issues
- **Accounting Inconsistencies**: Mismatched internal/external state
- **DoS via Gas** (dos-005): Related loop amplification concept
- **Token Drain**: General category for reserve depletion

---

## BSKG Properties Used

### Primary Detection (Existing)
- `uses_integer_division = true` (if detectable)
- `transfers_value_out = true`

### Proposed New Properties
- `precision_loss_possible = true`: Division can round to zero
- `allows_micro_operations = true`: No minimum threshold
- `accounting_validation = false`: No consistency check

### Operations
- `TRANSFERS_VALUE_OUT`
- `READS_USER_BALANCE`
- `WRITES_USER_BALANCE`

---

## Implementation Challenges

**Difficulty**: High (requires arithmetic analysis)

This vulnerability is HARD to detect via static analysis because it requires:
1. Identifying division operations
2. Determining when result can be zero
3. Tracking which value is used for accounting vs transfer
4. Detecting lack of minimum thresholds

**Suggested Heuristics**:
- Flag any function with division + transfer
- Check for minimum amount validation
- Look for consistency checks
- Identify accounting/transfer value mismatch

---

## Testing Guidance

Create test contracts with:
1. **True Positive**: Withdrawal using scaled accounting, face value transfer, no minimum
2. **True Negative**: Withdrawal with minimum amount enforced
3. **Edge Case**: Scaling with consistency validation
4. **Variation**: Fixed-point arithmetic instead of integer division

Example test:
```python
def test_precision_accounting_vulnerability():
    graph = load_graph("PrecisionAccountingVulnerable")
    func = graph.get_function("withdraw")

    # Check for division (may need manual verification)
    assert func.transfers_value_out == True
    # NEW properties needed:
    # assert func.precision_loss_possible == True
    # assert func.allows_micro_operations == True
    # assert func.accounting_validation == False
```

---

**Last Updated**: 2026-01-09
**Status**: Documented, pattern creation pending
**Note**: Requires new properties in builder.py for full detection
