# Signature Duplication Attack

## Vulnerability Pattern

**Core Issue:** Threshold signature validation counts same signature multiple times or accepts duplicates.

**Vulnerable Pattern:**
```solidity
function executeMultisig(bytes32 hash, bytes[] calldata sigs) external {
    uint256 validCount;
    for (uint i = 0; i < sigs.length; i++) {
        address signer = recoverSigner(hash, sigs[i]);
        if (isValidator(signer)) {
            validCount++;  // NO deduplication check
        }
    }
    require(validCount >= threshold);
    // Attacker: submit same valid signature N times
}
```

**Why Vulnerable:**
- Same signer counted multiple times
- Attacker with 1 key can reach any threshold
- No tracking of which signers already signed

**Safe Pattern:**
```solidity
function executeMultisig(bytes32 hash, bytes[] calldata sigs) external {
    address lastSigner;
    for (uint i = 0; i < sigs.length; i++) {
        address signer = recoverSigner(hash, sigs[i]);
        require(signer > lastSigner, "Duplicate or unsorted");  // Strict ordering
        require(isValidator(signer), "Invalid signer");
        lastSigner = signer;
    }
    require(sigs.length >= threshold);
}
```

## Detection Signals

**Tier A (Deterministic):**
- `validates_signatures_in_loop: true`
- `deduplicates_signers: false`
- `threshold_based_execution: true`

**Behavioral Signature:**
```
CHECKS_SIG(loop) -> (missing_DEDUPE) -> COUNTS -> THRESHOLD_MET
```

## Fix

1. Require sorted signatures by signer address
2. Track used signers in mapping (cleared after execution)
3. Validate sigs.length <= validators.length
4. Verify ascending order: current > previous

**Real-world:** Chakra Protocol (2024)
