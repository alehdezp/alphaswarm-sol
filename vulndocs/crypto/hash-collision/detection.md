# Hash Collision via abi.encodePacked - Detection Guide

## Overview

`abi.encodePacked()` concatenates arguments without length encoding. When used with multiple variable-length arguments (strings, bytes, arrays), different input combinations can produce identical outputs, leading to hash collisions.

## Detection Signals

### Tier A: Deterministic Detection

**Primary Signals (VKG Properties):**

1. **Uses abi.encodePacked**
   - Property: `uses_abi_encode_packed`
   - Detection: Function calls abi.encodePacked()
   - Confidence: 95%

2. **Multiple Dynamic Arguments**
   - Property: `multiple_dynamic_args_to_encode_packed`
   - Detection: 2+ variable-length arguments to abi.encodePacked
   - Confidence: 90%

3. **Hash Used for Security**
   - Property: `hash_used_for_security`
   - Detection: Result passed to keccak256, used in signature verification, merkle proof, or access control
   - Confidence: 85%

**Semantic Operations:**

- `COMPUTES_HASH` - Hashing operation present
- `VERIFIES_SIGNATURE` - Result used in signature check
- `CHECKS_MERKLE_PROOF` - Result used in merkle verification
- `CHECKS_PERMISSION` - Result used for authorization

**Behavioral Signature:**

Vulnerable: `EP:multi{dynamic}->H:hash->V:sig`
- encodePacked with multiple dynamic args
- Result hashed
- Hash used for signature verification

Safe: `E:multi{dynamic}->H:hash->V:sig`
- encode (not packed) with dynamic args
- Result hashed
- Hash used for verification

### Tier B: LLM Reasoning Required

**Context Questions:**

1. Are the arguments to abi.encodePacked all fixed-length?
2. Is the hash result used for security decisions?
3. Can an attacker control the content or ordering of inputs?
4. Are there fixed-length separators between dynamic arguments?

**False Positive Indicators:**

- All arguments are fixed-length types (uint256, address, bool)
- Hash only used for logging/events, not security
- Fixed-length separator added between dynamic args
- Only one dynamic argument to abi.encodePacked

## Manual Checks

Auditors should verify:

1. **Identify abi.encodePacked Usage**
   - Search codebase for `abi.encodePacked`
   - List all call sites with their arguments

2. **Classify Argument Types**
   - Fixed-length: uint, address, bool, fixed-size bytes (bytes32)
   - Variable-length: string, bytes, arrays

3. **Check for Collision Risk**
   - HIGH RISK: 2+ variable-length args
   - MEDIUM RISK: 1 variable + 1 fixed (fixed should come first)
   - LOW RISK: All fixed-length

4. **Trace Hash Usage**
   - Where is the hash result used?
   - Signature verification? → HIGH SEVERITY
   - Merkle proof? → HIGH SEVERITY
   - Authorization? → HIGH SEVERITY
   - Logging only? → LOW SEVERITY

5. **Test for Collisions**
   - Create test inputs that should produce same hash
   - Verify collision is possible

## Automated Checks

```yaml
check_1:
  type: function_call_pattern
  pattern: abi.encodePacked
  conditions:
    - arg_count >= 2
    - any_arg_is_dynamic_type
  risk: medium

check_2:
  type: data_flow
  source: abi.encodePacked(multiple_dynamic)
  sink: [keccak256, ecrecover, require]
  risk: high

check_3:
  type: property_match
  conditions:
    - uses_abi_encode_packed: true
    - hash_used_for_security: true
    - multiple_dynamic_args: true
  risk: critical
```

## Collision Examples

### Example 1: String Concatenation

```solidity
// Both produce "helloworld"
bytes memory collision1 = abi.encodePacked("hello", "world");
bytes memory collision2 = abi.encodePacked("hellow", "orld");

// Same hash!
bytes32 hash1 = keccak256(collision1);
bytes32 hash2 = keccak256(collision2);
// hash1 == hash2
```

### Example 2: Array Boundaries

```solidity
string[] memory a = ["a", "bc"];
string[] memory b = ["ab", "c"];

// Both produce "abc"
bytes memory packed1 = abi.encodePacked(a[0], a[1]);
bytes memory packed2 = abi.encodePacked(b[0], b[1]);

// Collision
keccak256(packed1) == keccak256(packed2);  // true
```

### Example 3: Signature Verification

```solidity
// VULNERABLE
function verify(
    address user,
    string memory action,
    string memory resource,
    bytes memory signature
) external {
    bytes32 hash = keccak256(
        abi.encodePacked(user, action, resource)
    );

    // VULNERABLE TO COLLISION
    // ("user", "delete", "file") == ("user", "deletef", "ile")
    require(recoverSigner(hash, signature) == trustedSigner);

    _executeAction(action, resource);
}
```

## Code Patterns

### Vulnerable Pattern 1: Multiple Strings

```solidity
// VULNERABLE: Multiple strings
function createId(string memory a, string memory b) external pure returns (bytes32) {
    return keccak256(abi.encodePacked(a, b));
    // "hello" + "world" == "hellow" + "orld"
}
```

**Operations:** `COMPUTES_HASH`
**Signature:** `EP:str+str->H:hash`

### Vulnerable Pattern 2: Signature Verification

```solidity
// VULNERABLE: Dynamic args in signature
function verifyMessage(
    string memory message,
    string memory nonce,
    bytes memory signature
) external view returns (bool) {
    bytes32 hash = keccak256(
        abi.encodePacked(message, nonce)
    );

    // Collision allows signature reuse
    return ecrecover(hash, ...) == signer;
}
```

**Operations:** `COMPUTES_HASH`, `VERIFIES_SIGNATURE`
**Signature:** `EP:str+str->H:hash->V:ecrecover`

### Vulnerable Pattern 3: Merkle Proof

```solidity
// VULNERABLE: Dynamic leaves
function verifyProof(
    bytes32[] memory proof,
    string memory leaf1,
    string memory leaf2
) external pure returns (bool) {
    bytes32 leaf = keccak256(
        abi.encodePacked(leaf1, leaf2)
    );

    // Collision breaks merkle tree
    return MerkleProof.verify(proof, root, leaf);
}
```

**Operations:** `COMPUTES_HASH`, `CHECKS_MERKLE_PROOF`
**Signature:** `EP:str+str->H:hash->M:verify`

### Safe Pattern 1: Use abi.encode

```solidity
// SAFE: abi.encode includes length prefixes
function createId(string memory a, string memory b) external pure returns (bytes32) {
    return keccak256(abi.encode(a, b));
    // "hello", "world" != "hellow", "orld" (different encoded lengths)
}
```

**Operations:** `COMPUTES_HASH`
**Signature:** `E:str+str->H:hash` (E = encode, not encodePacked)

### Safe Pattern 2: Fixed-Length Separator

```solidity
// SAFE: Fixed-length separator prevents collision
function createId(string memory a, string memory b) external pure returns (bytes32) {
    return keccak256(
        abi.encodePacked(
            a,
            uint256(0),  // Fixed-length separator
            b
        )
    );
}
```

**Operations:** `COMPUTES_HASH`
**Signature:** `EP:str+fixed+str->H:hash`

### Safe Pattern 3: Only Fixed-Length

```solidity
// SAFE: All arguments are fixed-length
function createId(address user, uint256 nonce, bytes32 action) external pure returns (bytes32) {
    return keccak256(abi.encodePacked(user, nonce, action));
    // All fixed-length, no collision risk
}
```

**Operations:** `COMPUTES_HASH`
**Signature:** `EP:fixed+fixed+fixed->H:hash`

### Safe Pattern 4: Single Dynamic Argument

```solidity
// SAFE: Only one dynamic argument
function createId(address user, string memory data) external pure returns (bytes32) {
    return keccak256(abi.encodePacked(user, data));
    // Fixed + dynamic (in that order) is safe from collision
}
```

**Operations:** `COMPUTES_HASH`
**Signature:** `EP:fixed+str->H:hash`

## Detection Tools

- **Slither**: Detects `abi.encodePacked` with multiple dynamic args
- **Mythril**: Symbolic execution can find collision paths
- **Manual Review**: Essential for understanding security impact

## Quick Reference

**High Risk:**
```solidity
❌ abi.encodePacked(string, string)
❌ abi.encodePacked(bytes, bytes)
❌ abi.encodePacked(string[], uint256[])
❌ abi.encodePacked(string, bytes)
```

**Low Risk:**
```solidity
✅ abi.encode(string, string)
✅ abi.encodePacked(address, uint256, bytes32)
✅ abi.encodePacked(uint256, string)
✅ abi.encodePacked(string, uint256(0), string)
```

## References

- Solidity Documentation: ABI Encoding
- SWC-133: Hash Collisions With Multiple Variable Length Arguments
- ConsenSys Best Practices: Hash Collisions
