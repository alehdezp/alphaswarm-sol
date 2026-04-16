# Parameter Confusion - Detection

## Core Detection Signals

### Operations
- **READS_NESTED_MAPPING**: Accesses mapping[key1][key2] structure
- **CHECKS_PERMISSION**: Reads from access control mappings
- **MODIFIES_APPROVAL**: Updates approval/allowance state
- **MODIFIES_ROLES**: Changes role assignments

### Properties
- `has_nested_mapping_access: true` - Function accesses nested mappings
- `parameter_order_mismatch: true` - Parameter positions don't match intent
- `reads_wrong_mapping_key: true` - Uses incorrect key order in mapping access

### Behavioral Signatures
- **Vulnerable**: `R:mapping[paramA][paramB]` where business logic requires `mapping[paramB][paramA]`
- **Safe**: `R:mapping[owner][spender]` matches ERC20 allowance pattern

## Preconditions
- Function with nested mapping access (allowances, roles, approvals)
- Multiple parameters used as mapping keys
- No validation of parameter order correctness

## Postconditions
- Attacker gains unintended permissions
- Access control bypassed via parameter confusion
- State modifications affect wrong entities

## Detection Strategy

### Static Analysis
1. Identify all nested mapping accesses: `mapping[X][Y]`
2. Extract function parameters used as keys
3. Compare parameter usage order with similar functions (e.g., ERC20 standard)
4. Flag mismatches where `_allowances[msgSender][account]` appears instead of `_allowances[account][msgSender]`

### Manual Review Checklist
- Verify mapping key order matches business logic
- Check that `_allowances[owner][spender]` pattern is consistent
- Confirm `hasRole[role][user]` vs `hasRole[user][role]` aligns with intent
- Review all overridden ERC functions for parameter consistency

### Formal Verification
Use specifications to catch parameter confusion:
```solidity
/// #if_succeeds "Only owner may increase allowance"
///   old(allowances[owner][spender]) < allowances[owner][spender]
///   ==> msg.sender == owner
```

## Common Locations
- ERC20 `burnFrom`, `transferFrom` implementations
- Access control role assignment functions
- Multi-signature approval tracking
- Delegation pattern implementations
- Proxy authorization checks

## Detection Difficulty
**Medium** - Requires understanding business logic intent, not just syntax correctness

## False Positives
- Intentional parameter swap for specific use cases
- Symmetric relationships where order doesn't matter
- Custom mapping structures with different semantics
