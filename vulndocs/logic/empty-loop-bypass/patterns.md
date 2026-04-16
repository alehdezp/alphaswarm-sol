# Empty Loop Bypass - Patterns

## Vulnerable: Signature Verification

```solidity
// VULNERABLE
function executeWithSigs(bytes[] memory sigs) external {
    for (uint i = 0; i < sigs.length; i++) {
        require(verify(sigs[i]));
    }
    _execute();  // Bypassed with empty array
}
```

## Vulnerable: Permission Check

```solidity
// VULNERABLE
function batchTransfer(address[] memory approvers) external {
    for (uint i = 0; i < approvers.length; i++) {
        require(isApprover(approvers[i]));
    }
    _transferFunds();  // Bypassed
}
```

## Safe: Length Check

```solidity
// SAFE
function executeWithSigs(bytes[] memory sigs) external {
    require(sigs.length > 0);  // FIX
    for (uint i = 0; i < sigs.length; i++) {
        require(verify(sigs[i]));
    }
    _execute();
}
```

## Safe: Validation Outside Loop

```solidity
// SAFE
function executeWithSig(bytes memory sig) external {
    require(verify(sig));  // Single signature, no loop
    _execute();
}
```
