# Detection: Missing Access Control Modifier

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| has_access_gate | false | YES |
| writes_privileged_state | true | YES |
| visibility | public, external | YES |
| modifies_owner | true | NO |
| modifies_roles | true | NO |

## Semantic Operations

**Vulnerable Pattern:**
- `MODIFIES_OWNER` without `CHECKS_PERMISSION`
- `MODIFIES_ROLES` without `CHECKS_PERMISSION`
- `MODIFIES_CRITICAL_STATE` without `CHECKS_PERMISSION`

**Safe Pattern:**
- `CHECKS_PERMISSION -> MODIFIES_OWNER`
- `CHECKS_PERMISSION -> MODIFIES_ROLES`

## Behavioral Signatures

- `W:owner->!G:access` - Owner write without access gate
- `W:role->!G:access` - Role write without access gate
- `W:critical->!G:access` - Critical state write without access gate

## Detection Checklist

1. Function is public/external
2. Function modifies privileged state (owner, admin, role, fee, treasury)
3. No modifier that checks msg.sender or role
4. No inline access control check (require(msg.sender == owner))
5. Function is not a constructor
6. Function is not intentionally permissionless

## False Positive Indicators

- onlyOwner, onlyAdmin, onlyRole modifier present
- Inline msg.sender check against stored owner/admin
- Function is internal or private
- Function is constructor setting initial owner
- Function is view/pure (cannot modify state)
- Access control delegated to parent contract

## Manual Audit Checks (Solcurity Standard)

### F9: Access Control Verification
- Verify correct modifiers applied: `onlyOwner`, `requiresAuth`, etc.
- Check modifier logic implements intended access control
- Ensure modifiers don't have unexpected side effects

### F5: Parameter Validation
- Validate all parameters within safe bounds
- Apply validation even for trusted/owner-only functions
- Prevent privilege escalation via invalid parameters
- Check for address(0), overflow, underflow bounds

### F6: Checks-Effects-Interactions Pattern
- Access checks performed BEFORE state changes
- State effects completed BEFORE external calls
- Prevents reentrancy and state inconsistency
- Critical for functions with access control + external calls

### F16: Multi-User Operations
- If function operates on another user, don't assume `msg.sender` is target
- Validate target user explicitly
- Check permissions for both caller and target user
- Prevent unauthorized operations on other accounts

### Additional Checks
- F17: Explicit initialization check (not `owner == address(0)`)
- F3: Should function be `payable`? Prevents accidental ETH loss
- F2: Should function be `internal` instead of public?
- F18: Use `private` only to prevent child access, prefer `internal`
