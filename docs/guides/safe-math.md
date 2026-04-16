# Pattern Guide: lib-004-safe-math

**SafeMath Library Usage / Checked Arithmetic Protection**

## Quick Summary

Detects arithmetic operations without proper overflow/underflow protection:
- **Solidity < 0.8.0**: Arithmetic WITHOUT SafeMath library
- **Solidity >= 0.8.0**: Arithmetic in `unchecked` blocks without guards

**Severity**: HIGH
**Test Contracts**: `SafeMathTest.sol`, `SafeMathTest080.sol`

---

## The Vulnerability

### Pre-0.8.0: Silent Integer Overflow

In Solidity versions before 0.8.0, integer overflow happens silently:

```solidity
// VULNERABLE (pre-0.8.0)
pragma solidity ^0.7.0;

function add(uint256 a, uint256 b) external pure returns (uint256) {
    return a + b;  // Can overflow silently!
}

// Example: add(2^256 - 1, 1) returns 0, not error
```

**Why it's dangerous:**
- `uint256 max = 2^256 - 1`
- `max + 1 = 0` (wraps around silently)
- No exception is thrown
- Users can exploit this to drain balances

### 0.8.0+: Disabled Overflow Checks

Solidity 0.8.0 added automatic overflow detection, but you can disable it:

```solidity
// SAFE (0.8.0+)
pragma solidity ^0.8.0;

function add(uint256 a, uint256 b) external pure returns (uint256) {
    return a + b;  // Automatically checks for overflow
}

// VULNERABLE (0.8.0+, but intentionally disabled)
pragma solidity ^0.8.0;

function addUnchecked(uint256 a, uint256 b) external pure returns (uint256) {
    unchecked {
        return a + b;  // Overflow check is DISABLED here
    }
}
```

The `unchecked` block disables overflow checks for performance. You must manually ensure no overflow occurs.

---

## Detection Scenarios

The pattern matches THREE vulnerability scenarios:

### Scenario A: Pre-0.8.0 Without SafeMath

**Condition**: Compiler version < 0.8.0 AND arithmetic operations AND NO SafeMath

```solidity
// VULNERABLE
pragma solidity ^0.7.6;

contract Vault {
    mapping(address => uint256) balances;

    function deposit(uint256 amount) external {
        balances[msg.sender] += amount;  // ❌ Can overflow without SafeMath
    }

    function calculateReward(uint256 blocks) external pure returns (uint256) {
        uint256 rate = 1000000000;  // 10^9
        return rate * blocks;        // ❌ Large number multiplication risk
    }
}
```

**Fix**:
```solidity
pragma solidity ^0.7.6;
import "@openzeppelin/contracts/math/SafeMath.sol";

using SafeMath for uint256;

contract Vault {
    function deposit(uint256 amount) external {
        balances[msg.sender] = balances[msg.sender].add(amount);  // ✅ SafeMath
    }

    function calculateReward(uint256 blocks) external pure returns (uint256) {
        uint256 rate = 1000000000;
        return rate.mul(blocks);  // ✅ SafeMath
    }
}
```

### Scenario B: 0.8.0+ Unchecked Arithmetic

**Condition**: Solidity 0.8.0+ AND `unchecked` block AND (user input OR balance state modification)

```solidity
// VULNERABLE
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) balances;

    // Problem 1: unchecked + user input
    function depositUnchecked(uint256 amount) external {
        unchecked {
            balances[msg.sender] += amount;  // ❌ User input without overflow check
        }
    }

    // Problem 2: unchecked + balance state
    function mintUnchecked(uint256 newSupply) external {
        unchecked {
            balances[msg.sender] = newSupply;  // ❌ Affects balance state
        }
    }

    // Problem 3: Fee calculation in unchecked (precision loss)
    function takeFeeUnchecked(uint256 amount) external {
        unchecked {
            uint256 fee = amount * 25 / 100;  // ❌ Intermediate multiplication
            balances[msg.sender] -= fee;
        }
    }
}
```

**Fix**:
```solidity
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) balances;

    // OPTION 1: Remove unchecked (use native checks)
    function deposit(uint256 amount) external {
        balances[msg.sender] += amount;  // ✅ Native overflow check
    }

    // OPTION 2: Keep unchecked but guard with require
    function depositGuarded(uint256 amount) external {
        require(amount < type(uint256).max - balances[msg.sender], "Overflow");
        unchecked {
            balances[msg.sender] += amount;  // ✅ Guarded by require
        }
    }

    // OPTION 3: Use math library for complex operations
    function takeFee(uint256 amount) external returns (uint256) {
        uint256 fee = (amount * 25) / 100;  // ✅ No unchecked, native checks
        balances[msg.sender] -= fee;
        return fee;
    }
}
```

### Scenario C: Large Number Multiplication

**Condition**: Pre-0.8.0 AND multiplication of large numbers (> 10^9 each) AND NO SafeMath

```solidity
// VULNERABLE
pragma solidity ^0.7.0;

contract RewardCalculator {
    // Large numbers: 10^9 * 10^9 can overflow
    function calculateReward(uint256 numBlocks) external pure returns (uint256) {
        uint256 rate = 1000000000;  // 10^9
        return rate * numBlocks;     // ❌ Large * large = overflow risk
    }

    // Another example: stake amount multiplication
    function calculateStakeReward(uint256 stakeAmount, uint256 yieldRate) external pure returns (uint256) {
        return stakeAmount * yieldRate;  // ❌ Both could be > 10^9
    }
}
```

**Fix**:
```solidity
pragma solidity ^0.7.0;
import "@openzeppelin/contracts/math/SafeMath.sol";

using SafeMath for uint256;

contract RewardCalculator {
    function calculateReward(uint256 numBlocks) external pure returns (uint256) {
        uint256 rate = 1000000000;
        return rate.mul(numBlocks);  // ✅ SafeMath handles overflow
    }

    function calculateStakeReward(uint256 stakeAmount, uint256 yieldRate) external pure returns (uint256) {
        return stakeAmount.mul(yieldRate);  // ✅ SafeMath
    }
}
```

---

## Real-World Examples

### BeautyChain (BEC) Token - 2018

**Loss**: $900M+ destroyed instantly

**What happened:**
```solidity
function batchTransfer(address[] _receivers, uint256 _value) {
    uint cnt = _receivers.length;
    uint256 amount = uint256(cnt) * _value;  // ❌ Can overflow without checks
    require(_value > 0 && msg.sender has amount);

    for (uint i = 0; i < cnt; i++) {
        _receivers[i].transfer(_value);
    }
}
```

**The attack:**
- Attacker calls `batchTransfer` with large number of recipients
- `amount = cnt * _value` overflows to small number
- Require check passes because overflow made `amount` tiny
- Attacker "transfers" tokens they don't own
- All BEC tokens instantly became worthless

### SmartMesh (SMT) Token - 2018

**Loss**: $350M+ in tokens destroyed/stolen

**Similar overflow in batchTransfer** allowed unlimited token generation.

### Balancer Labs - 2021+

Multiple flash loan attacks exploited unchecked arithmetic in:
- Price calculations
- Share minting
- Fee accounting

All could have been prevented with proper overflow protection.

---

## How the Pattern Works

### Properties Used

```yaml
# Core detection properties
compiler_version_lt_08         # pragma version < 0.8.0?
pre_08_arithmetic              # Has arithmetic without SafeMath + pre-0.8?
has_unchecked_block            # Uses unchecked { ... }?
unchecked_contains_arithmetic  # Arithmetic operations in unchecked?
unchecked_operand_from_user    # User input involved in unchecked arithmetic?
unchecked_affects_balance      # Unchecked arithmetic modifies balance state?
large_number_multiplication    # Multiplying numbers > 10^9?
multiplication_overflow_risk   # Large multiply without SafeMath + pre-0.8?
uses_safemath                  # Uses @openzeppelin/math/SafeMath?
uses_safe_erc20                # Uses OpenZeppelin SafeERC20?
```

### Match Logic (Disjunctive - OR)

```
VULNERABLE IF:
  (Scenario A) pre_08_arithmetic == true
  OR
  (Scenario B) (unchecked_contains_arithmetic AND
                (unchecked_operand_from_user OR unchecked_affects_balance))
  OR
  (Scenario C) (large_number_multiplication AND multiplication_overflow_risk)

UNLESS:
  state_mutability in [view, pure]
  OR uses_safemath == true
  OR uses_safe_erc20 == true
  OR is_constructor == true
  OR is_fallback/receive == true
```

---

## False Positive Prevention

### Why We Exclude These

**View/Pure Functions**
```solidity
function calculateFee(uint256 amount) external pure returns (uint256) {
    return amount * 25 / 100;  // ✅ No state change, no vulnerability
}
```
- Pure calculation functions don't affect state
- Overflow in output won't corrupt contract state
- Caller can verify result if needed

**Constructors**
```solidity
constructor() {
    unchecked {
        totalSupply = 1000000000 + 500000000;  // ✅ Safe for initialization
    }
}
```
- Constructor runs once during deployment
- Lower risk than runtime operations
- Admin-controlled values

**Fallback/Receive**
```solidity
receive() external payable {
    unchecked {
        // Limited operations possible in fallback
    }
}
```
- Restricted functionality
- Can't do complex state operations

**With SafeMath/SafeERC20**
```solidity
using SafeMath for uint256;

function deposit(uint256 amount) external {
    balances[msg.sender] = balances[msg.sender].add(amount);  // ✅ Safe
}
```
- SafeMath wraps arithmetic and reverts on overflow
- Eliminates the vulnerability entirely

---

## Verification Checklist

When pattern flags a finding:

1. **Confirm Solidity version**
   - [ ] Check pragma statement (pragma solidity X.Y.Z)
   - [ ] Pre-0.8.0 or post-0.8.0?

2. **If pre-0.8.0**
   - [ ] Is SafeMath imported? (`import "@openzeppelin/contracts/math/SafeMath.sol"`)
   - [ ] Is it used correctly? (`using SafeMath for uint256`)
   - [ ] Are arithmetic operations wrapped? (e.g., `a.add(b)` not `a + b`)

3. **If 0.8.0+ with unchecked**
   - [ ] Is this arithmetic operation in an `unchecked { }` block?
   - [ ] Are values user-provided (parameters)?
   - [ ] Does it modify balance/share/supply state?
   - [ ] Are there require() guards before the unchecked block?

4. **Assess impact**
   - [ ] Can the arithmetic realistically overflow?
   - [ ] What's the impact? (balance corruption, infinite tokens, insolvency)
   - [ ] Can an attacker control the inputs?

---

## Testing Recommendations

### Unit Test Template

```solidity
// Test that SafeMath is used or overflow is guarded
function testOverflowProtection() external {
    // Pre-0.8.0: Should revert on overflow with SafeMath
    // 0.8.0+: Either revert naturally or be guarded
}

// Test boundary conditions
function testMaxValueHandling() external {
    uint256 max = type(uint256).max;
    // Should handle gracefully, not wrap around
}

// Test with large inputs
function testLargeNumberArithmetic() external {
    uint256 large = 1000000000 * 1000000000;  // 10^18
    // Should not overflow if arithmetic is protected
}
```

### Integration Test Template

```solidity
function testDepositThenWithdraw() external {
    deposit(largeAmount);
    // Balance should equal largeAmount, not wrapped
    assert(balances[user] == largeAmount);
}

function testFeeCalculation() external {
    uint256 amountAfterFee = takeFee(1000);
    // Should not lose precision or overflow
}
```

---

## Remediation Priority

### Critical (Fix Immediately)
- Pre-0.8.0 without SafeMath in user-facing functions
- Unchecked arithmetic on user balances/shares
- Any overflow that can cause fund loss

### High (Fix Soon)
- Unchecked arithmetic on supply/totals
- Fee calculations in unchecked blocks
- Unguarded unchecked blocks with user input

### Medium (Fix Before Production)
- View/pure function arithmetic (lower risk but still bad practice)
- Constants that might become variable in future

---

## Resources

**OpenZeppelin SafeMath Documentation**:
https://docs.openzeppelin.com/contracts/2.x/api/math#SafeMath

**Solidity 0.8.0 Release Notes** (Overflow Checks):
https://docs.soliditylang.org/en/latest/080-breaking-changes.html#arithmetic

**CWE-190: Integer Overflow**:
https://cwe.mitre.org/data/definitions/190.html

**CWE-191: Integer Underflow**:
https://cwe.mitre.org/data/definitions/191.html

**Real-World Examples**:
- BeautyChain (BEC) Overflow: https://rekt.news/bec-rekt/
- SmartMesh (SMT) Overflow: https://rekt.news/smartmesh-rekt/
- Balancer Flash Loan: https://rekt.news/balancer-rekt/

---

## Pattern Status

**Current Status**: DRAFT (awaiting workflow harness validation)

**Expected After Testing**:
- Precision: ~85%+ (accounts for legitimate unchecked uses)
- Recall: ~80%+ (catches most real vulnerabilities)
- Variation Score: ~80%+ (works across different code styles)
