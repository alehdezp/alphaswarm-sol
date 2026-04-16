# Empty Loop Bypass - Fixes

## Fix 1: Require Non-Empty (Recommended)

```solidity
require(array.length > 0, "Empty array");
```

**Effectiveness:** High | **Gas:** ~100

## Fix 2: Minimum Length Check

```solidity
require(array.length >= MIN_REQUIRED, "Insufficient items");
```

**Effectiveness:** High | **Gas:** ~100

## Fix 3: Default Rejection

```solidity
bool validated = false;
for (uint i = 0; i < array.length; i++) {
    require(verify(array[i]));
    validated = true;
}
require(validated, "No validation performed");
```

**Effectiveness:** High | **Gas:** ~200

## Best Practice

Add `require(arr.length > 0)` before any loop containing security validation.
