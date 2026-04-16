# Parameter Confusion - Code Patterns

## Vulnerable Pattern: Nested Mapping Parameter Swap

### ERC20 burnFrom Parameter Confusion
```solidity
// VULNERABLE: Swapped parameters in allowance read
function burnFrom(address account, uint256 amount) public virtual {
    // WRONG: Reads msgSender's allowance for account
    uint256 currentAllowance = _allowances[_msgSender()][account];

    // This inadvertently approves account to spend msgSender's tokens
    _approve(account, _msgSender(), currentAllowance - amount);
    _burn(account, amount);
}
```

**Operations**: `READS_ALLOWANCE[wrong_key]` → `MODIFIES_APPROVAL[swapped]` → `BURNS_TOKENS`

**Attack Path**:
1. Attacker calls `approve(victim, N)` giving victim N tokens allowance
2. Attacker calls `burnFrom(victim, 0)` with zero amount
3. Function reads `_allowances[attacker][victim]` (= N)
4. Function calls `_approve(victim, attacker, N - 0)`
5. Result: Victim now approved to spend N of attacker's tokens → REVERSES to attacker approved for victim's N tokens

## Safe Pattern: Correct Parameter Order

### Correct ERC20 burnFrom
```solidity
// SAFE: Correct parameter order
function burnFrom(address account, uint256 amount) public virtual {
    // CORRECT: Reads account's allowance for msgSender
    uint256 currentAllowance = _allowances[account][_msgSender()];

    // Properly decreases allowance account gave to msgSender
    _approve(account, _msgSender(), currentAllowance - amount);
    _burn(account, amount);
}
```

**Operations**: `READS_ALLOWANCE[correct_key]` → `MODIFIES_APPROVAL[correct]` → `BURNS_TOKENS`

## Vulnerable Pattern: Access Control Role Confusion

```solidity
// VULNERABLE: Swapped role check parameters
function grantRole(bytes32 role, address account) public {
    // WRONG: Checks if role has account permission, not if account has role
    require(hasRole[role][account], "Not authorized");
    roles[account][role] = true;
}
```

## Safe Pattern: Correct Role Check

```solidity
// SAFE: Correct role check order
function grantRole(bytes32 role, address account) public {
    // CORRECT: Checks if msgSender has admin role
    require(hasRole[msg.sender][ADMIN_ROLE], "Not admin");
    roles[account][role] = true;
}
```

## Comparison: Standard vs Confused

| Aspect | Standard ERC20 | Confused Implementation |
|--------|----------------|------------------------|
| Allowance Read | `allowances[owner][spender]` | `allowances[spender][owner]` |
| Approval Logic | Decrease owner's allowance for spender | Decrease spender's allowance for owner |
| Attack Vector | None | Reverse approval exploitation |
| Impact | Secure | Critical vulnerability |
