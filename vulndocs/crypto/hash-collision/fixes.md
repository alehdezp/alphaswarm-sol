# Hash Collision via abi.encodePacked - Remediation

## Fix Strategy 1: Use abi.encode (Recommended)

**Effectiveness:** High | **Complexity:** Low | **Gas:** +~100-200 gas

```solidity
// Before (Vulnerable)
keccak256(abi.encodePacked(a, b))

// After (Safe)
keccak256(abi.encode(a, b))
```

## Fix Strategy 2: Add Fixed-Length Separator

**Effectiveness:** Medium | **Complexity:** Low | **Gas:** Similar

```solidity
// Safe with separator
keccak256(abi.encodePacked(a, uint256(0), b))
```

## Fix Strategy 3: Restrict to Fixed-Length Types

**Effectiveness:** High | **Complexity:** Medium | **Gas:** Lowest

```solidity
// Convert dynamic to fixed
bytes32 aHash = keccak256(bytes(a));
bytes32 bHash = keccak256(bytes(b));
keccak256(abi.encodePacked(aHash, bHash))
```

## Migration Example

### Before
```solidity
function verifyMessage(string memory msg, string memory nonce, bytes memory sig) {
    bytes32 hash = keccak256(abi.encodePacked(msg, nonce));
    require(ecrecover(hash, ...) == signer);
}
```

### After
```solidity
function verifyMessage(string memory msg, string memory nonce, bytes memory sig) {
    bytes32 hash = keccak256(abi.encode(msg, nonce));  // FIXED
    require(ecrecover(hash, ...) == signer);
}
```

## Best Practice

**Default to abi.encode() for all security-critical hashing.**

Reserve abi.encodePacked() for gas optimization in non-security contexts only.
