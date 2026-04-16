# Detection: Cetus Protocol SUI Overflow Pattern

This document describes how to detect the arithmetic overflow vulnerability pattern exploited in the Cetus Protocol attack.

## Graph Signals

| Property | Expected | Critical | Confidence | Description |
|----------|----------|----------|------------|-------------|
| `has_arithmetic_operations` | true | Yes | 0.95 | Function performs multiplication or division |
| `performs_multiplication` | true | Yes | 0.90 | Unchecked multiplication detected |
| `performs_division` | true | No | 0.70 | Division operation detected |
| `writes_privileged_state` | true | Yes | 0.95 | Modifies critical balance/position state |
| `validates_input` | false | Yes | 0.90 | No input bounds checking |
| `uses_safe_math` | false | Yes | 0.85 | No SafeMath pattern detected |
| `reads_user_input` | true | No | 0.75 | Accepts user-provided values |
| `visibility` | public, external | No | 0.80 | Externally callable |

## Operation Sequences

### Vulnerable Signature
```
R:input -> C:mul{unchecked} -> W:critical_state
```

This pattern indicates:
1. **R:input** - Function reads user-provided input value
2. **C:mul{unchecked}** - Performs multiplication without bounds validation
3. **W:critical_state** - Writes result to critical state variable

### Safe Signature
```
R:input -> C:validate_bounds -> C:mul -> W:state
```

This pattern indicates proper protection:
1. **R:input** - Reads input
2. **C:validate_bounds** - Validates input is within safe range
3. **C:mul** - Performs multiplication (now safe due to bounds)
4. **W:state** - Writes to state

## Behavioral Signatures

### Pattern 1: Unchecked Multiplication in Position Calculation
```
function calculatePosition(input: uint256) -> state {
  result = input * multiplier
  state.position = result
}
```

**Detection**: Look for multiplication followed immediately by state write without intermediate bounds checking.

### Pattern 2: Division Without Precision Check
```
function getPortion(total: uint256, input: uint256) -> state {
  portion = total / input
  state.balance = portion
}
```

**Detection**: Division where the divisor comes from user input or untrusted source.

### Pattern 3: Multiplication Chain
```
function complexCalculation(a: uint256, b: uint256) -> state {
  temp = a * b
  result = temp * c
  state.value = result
}
```

**Detection**: Multiple multiplication operations in sequence without intermediate validation.

## False Positive Indicators

These indicators suggest the code is NOT vulnerable:

1. **SafeMath Library Usage**
   ```solidity
   using SafeMath for uint256;
   uint256 result = value.mul(multiplier);
   ```

2. **Solidity 0.8.0+ with Built-in Checks**
   - Solidity 0.8.0 and later have checked arithmetic by default
   - Overflows/underflows automatically revert

3. **Explicit Bounds Validation**
   ```solidity
   require(input <= MAX_INPUT, "Input too large");
   require(input <= type(uint256).max / multiplier, "Would overflow");
   uint256 result = input * multiplier;
   ```

4. **OpenZeppelin or Standard Libraries**
   - Use of `SafeMath`, `Math.mulDiv`, or similar

5. **Internal Helper Functions with Checked Math**
   ```solidity
   function _safeMultiply(uint256 a, uint256 b) internal pure returns (uint256) {
       if (a == 0) return 0;
       require(b <= type(uint256).max / a, "Overflow");
       return a * b;
   }
   ```

6. **Require Statements Before State Write**
   ```solidity
   uint256 position = amount * pricePerUnit;
   require(position <= MAX_POSITION, "Position too large");
   state.position = position;
   ```

## Detection Checklist

When analyzing a contract for this vulnerability:

- [ ] Identify all multiplication/division operations
- [ ] For each arithmetic operation:
  - [ ] Check if inputs come from external/user sources
  - [ ] Verify bounds checking exists before operation
  - [ ] Confirm SafeMath or checked arithmetic is used
  - [ ] Check intermediate results for overflow risk
- [ ] Look for state writes immediately after unchecked arithmetic
- [ ] Check Solidity version (0.8.0+ is safer by default)
- [ ] Verify MAX_* constant definitions match operation requirements
- [ ] Test with maximum input values (2^256-1, near limits)

## Code Analysis Patterns

### High-Risk Pattern
```solidity
// HIGH RISK: Direct multiplication without validation
function updatePosition(uint256 amount) public {
    positions[msg.sender] = amount * MULTIPLIER;
}
```

Detection score: **90%** - Clear vulnerability signal

### Medium-Risk Pattern
```solidity
// MEDIUM RISK: Some validation but incomplete
function updatePosition(uint256 amount) public {
    require(amount > 0, "Amount must be positive");
    positions[msg.sender] = amount * MULTIPLIER;
}
```

Detection score: **70%** - Positive check present but not comprehensive

### Low-Risk Pattern
```solidity
// LOW RISK: Comprehensive validation
function updatePosition(uint256 amount) public {
    require(amount > 0 && amount <= MAX_AMOUNT, "Invalid amount");
    require(amount <= type(uint256).max / MULTIPLIER, "Would overflow");
    positions[msg.sender] = amount * MULTIPLIER;
}
```

Detection score: **5%** - Properly protected

## BSKG Graph Query

To query contracts for this vulnerability pattern:

```vql
FIND functions WHERE
  has_arithmetic_operations = true
  AND performs_multiplication = true
  AND validates_input = false
  AND writes_privileged_state = true
  AND NOT has_reentrancy_guard = true
```

## Related Detection Patterns

- **logic-001**: Generic overflow/underflow pattern
- **dos-002**: Integer arithmetic attacks
- **ac-005**: Unchecked state modification
