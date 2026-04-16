# Fixes: Role/Privilege Escalation

## Recommended Fixes

### 1. Use OpenZeppelin AccessControl

**Effectiveness:** High
**Complexity:** Medium

Properly structured role hierarchy with admin roles.

```solidity
import "@openzeppelin/contracts/access/AccessControl.sol";

contract SecureRoles is AccessControl {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    constructor() {
        // Set up role hierarchy
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);

        // ADMIN_ROLE is the admin of MINTER and PAUSER
        _setRoleAdmin(MINTER_ROLE, ADMIN_ROLE);
        _setRoleAdmin(PAUSER_ROLE, ADMIN_ROLE);
    }

    // Only DEFAULT_ADMIN_ROLE can grant ADMIN_ROLE
    // Only ADMIN_ROLE can grant MINTER_ROLE and PAUSER_ROLE
}
```

### 2. Implement Two-Step Role Assignment

**Effectiveness:** High
**Complexity:** Medium

Require acceptance for critical role assignments.

```solidity
contract TwoStepRoles {
    mapping(address => bool) public admins;
    mapping(address => address) public pendingAdmins;

    function proposeAdmin(address newAdmin) external {
        require(admins[msg.sender], "Not admin");
        pendingAdmins[newAdmin] = msg.sender;
    }

    function acceptAdmin() external {
        require(pendingAdmins[msg.sender] != address(0), "Not proposed");
        admins[msg.sender] = true;
        delete pendingAdmins[msg.sender];
    }
}
```

### 3. Prevent Self-Assignment

**Effectiveness:** High
**Complexity:** Low

Explicitly prevent users from granting roles to themselves.

```solidity
contract NoSelfAssignment {
    mapping(address => bool) public admins;

    function setAdmin(address user, bool isAdmin) external {
        require(admins[msg.sender], "Not admin");
        require(user != msg.sender, "Cannot self-assign");  // Prevent self-assignment
        admins[user] = isAdmin;
    }
}
```

### 4. Use Timelock for Critical Role Changes

**Effectiveness:** High
**Complexity:** High

Add delay to critical role assignments for monitoring.

```solidity
import "@openzeppelin/contracts/governance/TimelockController.sol";

contract TimelockRoles is AccessControl {
    TimelockController public timelock;

    // Role changes must go through timelock
    function scheduleRoleChange(
        address target,
        bytes32 role,
        bool grant
    ) external onlyRole(ADMIN_ROLE) {
        bytes memory data = grant
            ? abi.encodeCall(this.grantRole, (role, target))
            : abi.encodeCall(this.revokeRole, (role, target));

        timelock.schedule(
            address(this),
            0,
            data,
            bytes32(0),
            bytes32(0),
            2 days  // 2 day delay
        );
    }
}
```

## Best Practices

1. **Establish clear role hierarchy** - Document who can grant which roles
2. **Use principle of least privilege** - Grant minimum necessary permissions
3. **Prevent self-assignment** - Users should not grant roles to themselves
4. **Add monitoring** - Emit events for all role changes
5. **Use timelock for admin roles** - Add delay for critical changes
6. **Limit role holders** - Cap maximum number of admins

## Testing Recommendations

1. Test that users cannot escalate their own privileges
2. Test role hierarchy is properly enforced
3. Verify self-assignment is prevented
4. Test role revocation works correctly
5. Verify events are emitted for role changes
6. Test timelock delays are enforced
