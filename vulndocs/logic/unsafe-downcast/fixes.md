# Unsafe Downcasting - Fixes

## Fix 1: OpenZeppelin SafeCast (Recommended)

```solidity
import "@openzeppelin/contracts/utils/math/SafeCast.sol";

uint128 value = SafeCast.toUint128(largeValue);
```

**Effectiveness:** High | **Gas:** ~100 | **Complexity:** Low

Available for: `toUint248`, `toUint240`, ..., `toUint8`

## Fix 2: Manual Bounds Check

```solidity
require(value <= type(uint128).max, "Overflow");
uint128 smaller = uint128(value);
```

**Effectiveness:** High | **Gas:** ~50 | **Complexity:** Low

## Fix 3: Use Unchecked Only When Safe

```solidity
unchecked {
    // Only if value is PROVEN to fit
    uint128 smaller = uint128(value);
}
```

**Effectiveness:** Medium | **Complexity:** High | **Use:** Expert only

## Migration Example

### Before
```solidity
mapping(address => uint128) balances;

function deposit(uint256 amt) external {
    balances[msg.sender] = uint128(amt);  // VULNERABLE
}
```

### After
```solidity
import "@openzeppelin/contracts/utils/math/SafeCast.sol";

mapping(address => uint128) balances;

function deposit(uint256 amt) external {
    balances[msg.sender] = SafeCast.toUint128(amt);  // FIXED
}
```

## Best Practice

**Default to SafeCast for all downcasts unless you have explicit proof the value fits.**
