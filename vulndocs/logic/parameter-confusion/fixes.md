# Parameter Confusion - Remediation

## Primary Fix: Correct Parameter Order

### For ERC20 burnFrom
```solidity
// FIX: Use correct mapping key order
function burnFrom(address account, uint256 amount) public virtual {
    // BEFORE: uint256 currentAllowance = _allowances[_msgSender()][account];
    // AFTER:  uint256 currentAllowance = _allowances[account][_msgSender()];

    uint256 currentAllowance = _allowances[account][_msgSender()];
    _approve(account, _msgSender(), currentAllowance - amount);
    _burn(account, amount);
}
```

**Effectiveness**: High - Single line change eliminates vulnerability

## Formal Specification Approach

### Using Scribble for Verification
```solidity
/// #if_succeeds "Only owner may increase allowance for their tokens"
///   old(_allowances[owner][spender]) < _allowances[owner][spender]
///   ==> msg.sender == owner
function _approve(address owner, address spender, uint256 amount) internal {
    _allowances[owner][spender] = amount;
    emit Approval(owner, spender, amount);
}
```

**Benefits**:
- Catches parameter confusion via fuzzing
- Verifies business logic, not just syntax
- Detected DeusDao bug in 20 minutes of fuzzing

## Reference Implementation Pattern

### Use OpenZeppelin as Template
```solidity
// Always reference standard implementations
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

// For custom implementations, verify against standard
function burnFrom(address account, uint256 amount) public virtual override {
    // Match OpenZeppelin's parameter order exactly
    uint256 currentAllowance = allowance(account, _msgSender());
    require(currentAllowance >= amount, "ERC20: insufficient allowance");
    unchecked {
        _approve(account, _msgSender(), currentAllowance - amount);
    }
    _burn(account, amount);
}
```

## Development Practices

### 1. Consistent Mapping Convention
```solidity
// Establish and document mapping key order
mapping(address owner => mapping(address spender => uint256)) private _allowances;

// Always use: _allowances[owner][spender]
// Never use: _allowances[spender][owner]
```

### 2. Helper Functions
```solidity
// Encapsulate nested mapping access
function getAllowance(address owner, address spender) internal view returns (uint256) {
    return _allowances[owner][spender];
}

function burnFrom(address account, uint256 amount) public virtual {
    uint256 currentAllowance = getAllowance(account, _msgSender());  // ← Correct by design
    _approve(account, _msgSender(), currentAllowance - amount);
    _burn(account, amount);
}
```

### 3. Unit Tests with Edge Cases
```solidity
// Test parameter order explicitly
function testBurnFromParameterOrder() public {
    // Setup: User A approves User B
    vm.prank(userA);
    token.approve(userB, 100);

    // Verify: userB can burn from userA (not reverse)
    vm.prank(userB);
    token.burnFrom(userA, 50);

    assertEq(token.allowance(userA, userB), 50);  // Allowance decreased
    assertEq(token.allowance(userB, userA), 0);   // Reverse allowance unchanged
}
```

## Audit Checklist

- [ ] All nested mapping accesses reviewed for parameter order
- [ ] Allowance pattern matches `_allowances[owner][spender]`
- [ ] Role checks use `hasRole[user][role]` consistently
- [ ] Compared implementation with standard reference (OpenZeppelin)
- [ ] Added formal specifications for critical functions
- [ ] Unit tests verify parameter order explicitly
- [ ] Fuzzing campaign run with property-based assertions

## Prevention Strategy

### Code Review
1. Flag all nested mapping access for manual review
2. Compare parameter order with standard implementations
3. Verify business logic matches technical implementation

### Automated Tools
- **Scribble**: Write formal specifications
- **Diligence Fuzzing**: Property-based testing
- **Slither**: Custom detector for parameter order patterns
- **Mythril**: Symbolic execution with assertions

### Long-term Solutions
- Use helper functions to encapsulate nested mapping access
- Adopt standard library implementations (OpenZeppelin)
- Enforce formal verification in CI/CD pipeline
- Regular comparison audits against reference implementations
