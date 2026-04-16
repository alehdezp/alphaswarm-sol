# Rounding Direction Manipulation

## Vulnerability Pattern

**Core Issue:** Inconsistent rounding directions in scaling operations compound errors through repeated execution.

**Vulnerable Pattern:**
```solidity
function _upscale(uint256 amount, uint256 factor) internal pure returns (uint256) {
    return amount.mulDown(factor);  // Rounds DOWN
}

function _downscale(uint256 amount, uint256 factor) internal pure returns (uint256) {
    if (condition) {
        return amount.divUp(factor);    // Rounds UP
    } else {
        return amount.divDown(factor);  // Rounds DOWN - INCONSISTENT
    }
}
```

**Why Vulnerable:**
- Upscale rounds DOWN, downscale uses MIXED rounding
- Repeated operations compound error
- 1000 operations → 1-2% deviation
- Enables invariant manipulation

**Safe Pattern:**
```solidity
function _upscale(uint256 amount, uint256 factor) internal pure returns (uint256) {
    return amount.mulUp(factor);  // CONSISTENT: favor protocol
}

function _downscale(uint256 amount, uint256 factor) internal pure returns (uint256) {
    return amount.divDown(factor);  // CONSISTENT: favor protocol
}

// Add validation
function batchOp() external {
    uint256 invBefore = _invariant();
    // ... operations ...
    uint256 invAfter = _invariant();
    require(invAfter >= invBefore.mulDown(MIN_RATIO), "Invariant violation");
}
```

## Detection Signals

**Tier A (Deterministic):**
- `has_scaling_functions: true`
- `has_multiple_rounding_modes: true`
- `validates_invariant_after_operations: false`
- `has_batch_operations: true`

**Behavioral Signature:**
```
R:inv -> SCALE_UP(↓) -> CALC -> SCALE_DOWN(mixed) -> W:inv_low
```

## Fix

1. Consistent rounding: upscale UP, downscale DOWN
2. Invariant validation after batch ops (99.9% tolerance)
3. Limit batch size (max 50 operations)

**Real-world:** Balancer V2 (2025)
