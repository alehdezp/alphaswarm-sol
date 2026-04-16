# Incorrect Overflow Check Threshold

## Vulnerability Pattern

**Core Issue:** Overflow check uses wrong threshold constant, allowing values that will overflow to pass validation.

**Vulnerable Pattern (Move/Rust):**
```rust
const MAX_U128: u128 = 0xFFFFFFFFFFFFFFFF; // Wrong: This is 2^64-1, not u128 max

pub fun checked_shl(value: u128, shift: u8): u128 {
    assert!(value < (MAX_U128 << shift), E_OVERFLOW); // WRONG THRESHOLD
    value << shift  // Can overflow
}
```

**Vulnerable Pattern (Solidity):**
```solidity
uint256 constant SCALE = 1e18;
uint256 constant WRONG_MAX = type(uint256).max >> 10; // Too permissive

function scale(uint256 value) internal pure returns (uint256) {
    require(value < WRONG_MAX, "Overflow"); // WRONG
    return value * SCALE; // Can overflow
}
```

**Why Vulnerable:**
- Threshold constant doesn't match operation
- For N-bit shift on M-bit type: threshold must be `2^(M-N)`
- Wrong constant allows overflow values to pass check

**Safe Pattern:**
```rust
// Correct threshold for 64-bit shift on u128
const MAX_SAFE: u128 = 0x1 << (128 - 64); // 2^64

pub fun checked_shl(value: u128, shift: u8): u128 {
    let threshold = 0x1u128 << (128 - shift);
    assert!(value < threshold, E_OVERFLOW); // CORRECT
    value << shift
}
```

```solidity
uint256 constant SCALE = 1e18;
uint256 constant MAX_SAFE = type(uint256).max / SCALE; // Correct

function scale(uint256 value) internal pure returns (uint256) {
    require(value <= MAX_SAFE, "Overflow");
    return value * SCALE; // Safe
}
```

## Detection Signals

**Tier A:**
- `uses_bit_shift_operations: true`
- `has_overflow_check: true`
- `threshold_constant_incorrect: true`
- `uses_third_party_library: true`

**Formula Check:**
- For bit-shift: `threshold = 0x1 << (type_bits - shift_amount)`
- For multiplication: `threshold = type_max / multiplier`

## Fix

1. Calculate correct threshold: `2^(M-N)` for N-bit shift on M-bit type
2. Add sanity bounds on results (min/max validation)
3. Test at exact boundary values
4. Use native checked arithmetic when available (Solidity 0.8+)

**Real-world:** Cetus Protocol (2025), integer-mate library bug
