# Configuration Issues - Quick Reference

## Overview

This subcategory covers low-level assembly and unsafe configuration handling vulnerabilities, including pointer corruption, unsafe arithmetic in Yul/assembly, and memory corruption exploits.

## Related Exploits

### 1inch Yul Calldata Corruption (March 2025)
- **Severity:** Critical
- **Loss:** $5,000,000 USD
- **Root Cause:** Integer underflow in pointer arithmetic (`ptr + interactionOffset + interactionLength`)
- **Attack:** Attacker set `interactionLength = 0xffffffff fe00 (-512)` causing pointer underflow
- **Result:** Resolver address overwritten, arbitrary fund extraction via order manipulation

## Detection Pattern

### BSKG Graph Signals (Property-Based)
Look for functions with:
- `uses_assembly = true` (0.95 confidence)
- `lacks_input_validation = true` (0.92 confidence)
- `performs_arithmetic_operations = true` (0.90 confidence)
- `writes_privileged_state = true` (0.88 confidence)
- `calls_untrusted = true` (0.87 confidence)

### Semantic Operations (Behavior-Based)
Functions exhibiting:
1. `VALIDATES_INPUT` - Insufficient validation
2. `PERFORMS_ARITHMETIC` - Unsafe arithmetic
3. `MODIFIES_CRITICAL_STATE` - Writes to privileged state
4. `CALLS_EXTERNAL` - External calls
5. `CALLS_UNTRUSTED` - Calls to untrusted addresses

### Behavioral Signatures
Watch for these patterns:
```
VULNERABLE:  V:in{incomplete} -> A:add -> W:crit
             (incomplete validation, unsafe arithmetic, write critical state)

VULNERABLE:  R:calldata -> A:ptr_arithmetic -> W:resolver
             (read calldata, calculate pointer, write resolver)

VULNERABLE:  X:resolver{corrupted} -> X:unk -> W:bal
             (corrupted resolver, untrusted call, write balance)

SAFE:        V:bounds -> A:arithmetic -> V:range -> W:state
             (bounds validation, arithmetic, range check, write)
```

## Red Flags

1. **Unsafe Pointer Arithmetic**
   - User-controlled values added to pointers without validation
   - No overflow/underflow checks

2. **Unvalidated Length Parameters**
   - Length/size parameters from calldata used directly
   - No bounds checking before use

3. **Resolver/Handler Address from Untrusted Source**
   - Address derived from calldata or user input
   - No whitelist or immutability protection

4. **Memory Corruption Risk**
   - Calldata offsets not bounded
   - Pointer arithmetic results not verified

## Remediation Quick Fixes

### 1. Add Bounds Checking (CRITICAL)
```solidity
require(interactionLength <= MAX_INTERACTION_LENGTH, "Length overflow");
```

### 2. Check for Arithmetic Overflow (CRITICAL)
```assembly
if lt(add(ptr, interactionOffset), ptr) {
  revert(0, 0)  // Overflow detected
}
```

### 3. Isolate Critical Addresses (CRITICAL)
- Use immutable addresses for resolvers
- Maintain whitelist of valid addresses
- Never derive from user input

### 4. Validate Memory Regions (HIGH)
- Document memory layout
- Enforce bounds before read/write
- Check pointer is within safe region

### 5. Migrate from Assembly (MEDIUM)
- Move critical logic to high-level Solidity
- Use Solidity 0.8.0+ automatic overflow detection
- Reserve assembly for gas optimization only

## False Positives Indicators

These features REDUCE vulnerability risk:
- ✓ All length/offset parameters bounds-checked
- ✓ Pointer arithmetic explicitly checks for overflow/underflow
- ✓ Calldata offsets relative to fixed base addresses
- ✓ Resolver address from immutable/initialized-once storage
- ✓ External calls to whitelisted addresses only
- ✓ Minimal assembly blocks, only for gas optimization
- ✓ Strong input validation on all parameters
- ✓ High-level Solidity for critical logic

## Related Vulnerabilities

- Integer Overflow/Underflow (CWE-190, CWE-191)
- Memory Buffer Corruption (CWE-119)
- Unsafe Assembly Code (SWC-101)
- Privileged State Modification
- Calldata Validation Bypass

## References

- **Postmortem:** https://blog.decurity.io/yul-calldata-corruption-1inch-postmortem-a7ea7a53bfd9
- **Analysis:** https://www.halborn.com/blog/post/explained-the-1inch-hack-march-2025
- **Timeline:** https://rekt.news/1inch-rekt
- **Official:** https://blog.1inch.com/vulnerability-discovered-in-resolver-contract/

## Key Takeaways

1. **Assembly is Dangerous** - Pointer arithmetic requires expert-level security review
2. **Bounds Matter** - Every input used in arithmetic must be validated
3. **Deprecated Code Liability** - Disable or remove deprecated features, don't leave them "for compatibility"
4. **Audit Gaps** - Rewritten code needs fresh audits, not just re-review of high-level logic
5. **Long Tail** - Vulnerability existed 2 years before exploitation (Nov 2022 → Mar 2025)

---

For detailed analysis, see `/knowledge/vulndocs/categories/logic/subcategories/configuration/specifics/1inch-calldata-corruption/index.yaml`
