# Parameter Order Confusion

## Vulnerability Pattern

**Core Issue:** Swapped parameters in nested mapping access reads/writes wrong key, inverting intended logic.

**Vulnerable Pattern:**
```solidity
function burnFrom(address account, uint256 amount) public {
    // WRONG: mapping[spender][owner] instead of mapping[owner][spender]
    uint256 allowance = _allowances[msg.sender][account];
    _approve(account, msg.sender, allowance - amount);
    _burn(account, amount);
}
// Attacker: approve(victim,N) -> burnFrom(victim,0) -> victim approved for attacker's N
```

**Why Vulnerable:**
- Nested mapping `M[A][B]` confused with `M[B][A]`
- Reads wrong party's allowance/permission
- Writes back to wrong direction
- Inverts intended access control

**Safe Pattern:**
```solidity
function burnFrom(address account, uint256 amount) public {
    // CORRECT: mapping[owner][spender]
    uint256 allowance = _allowances[account][msg.sender];
    _approve(account, msg.sender, allowance - amount);
    _burn(account, amount);
}
```

## Detection Signals

**Tier A (Deterministic):**
- `uses_nested_mappings: true`
- `parameter_order_matches_spec: false`
- `modifies_approval: true`

**Behavioral Signature:**
```
R:mapping[B][A] -> MODIFY -> W:mapping[B][A] (inverted from spec)
```

## Fix

1. Document mapping semantics: `allowances[owner][spender]`
2. Formal specification for invariants
3. Fuzz test with role reversal scenarios
4. Static analysis for parameter order

**Real-world:** DeusDao ($6.5M, 2023)
