# Hash Collision via abi.encodePacked - Code Patterns

## Vulnerable Patterns

### Pattern 1: Multiple Strings

```solidity
// VULNERABLE
keccak256(abi.encodePacked(string1, string2))
// "ab" + "c" == "a" + "bc"
```

### Pattern 2: Signature with Dynamic Args

```solidity
// VULNERABLE
bytes32 hash = keccak256(abi.encodePacked(msg, nonce));
address signer = ecrecover(hash, v, r, s);
```

### Pattern 3: Merkle Leaves

```solidity
// VULNERABLE
bytes32 leaf = keccak256(abi.encodePacked(data1, data2));
```

## Safe Patterns

### Pattern 1: Use abi.encode

```solidity
// SAFE: Length-prefixed encoding
keccak256(abi.encode(string1, string2))
```

### Pattern 2: Fixed-Length Separator

```solidity
// SAFE: Separator prevents collision
keccak256(abi.encodePacked(str1, uint256(0), str2))
```

### Pattern 3: Only Fixed-Length

```solidity
// SAFE: All fixed-length types
keccak256(abi.encodePacked(address, uint256, bytes32))
```

## Comparison

| Pattern | Collision Risk | Safe? |
|---------|---------------|-------|
| encodePacked(str, str) | HIGH | No |
| encodePacked(bytes, bytes) | HIGH | No |
| encode(str, str) | NONE | Yes |
| encodePacked(addr, str) | NONE | Yes |
| encodePacked(str, 0, str) | LOW | Yes |
