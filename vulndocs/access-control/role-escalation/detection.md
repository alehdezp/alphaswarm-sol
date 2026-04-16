# Detection: Role/Privilege Escalation

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| modifies_roles | true | YES |
| modifies_owner | true | YES |
| has_access_gate | false | YES |
| visibility | public, external | YES |
| writes_privileged_state | true | YES |

## Semantic Operations

**Vulnerable Pattern:**
- `MODIFIES_ROLES` without `CHECKS_PERMISSION`
- `MODIFIES_OWNER` without `CHECKS_PERMISSION`
- `grantRole(ADMIN)` without admin check

**Safe Pattern:**
- `CHECKS_PERMISSION` (admin) followed by `MODIFIES_ROLES`
- `CHECKS_PERMISSION` (owner) followed by `MODIFIES_OWNER`
- Role hierarchy properly enforced via AccessControl

## Behavioral Signatures

- `W:role->!G:admin` - Role write without admin gate
- `W:owner->!G:owner` - Owner write without owner gate
- `MODIFIES_ROLES->!CHECKS_PERMISSION` - Role modification without permission check
- `grantRole->!hasRole(ADMIN)` - Grant role without admin check

## Detection Checklist

1. Function can modify role assignments (grant/revoke)
2. Function can transfer or modify ownership
3. No access control check before role modification
4. Users can grant themselves higher privileges
5. Role hierarchy allows escalation
6. Self-assignment to admin roles possible

## False Positive Indicators

- Role assignment restricted to constructor
- Multi-sig or timelock required for role changes
- Role hierarchy properly enforced (only admin can grant admin)
- Self-assignment explicitly prevented
- Function is internal or private
- Governance vote required for role changes
