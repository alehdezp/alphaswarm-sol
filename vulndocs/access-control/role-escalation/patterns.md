# Patterns: Role/Privilege Escalation

## Vulnerable Pattern - Open Role Assignment

```solidity
contract VulnerableRoles {
    mapping(address => bool) public admins;
    mapping(address => bool) public minters;

    // VULNERABLE: Anyone can make themselves admin
    function setAdmin(address user, bool isAdmin) external {
        admins[user] = isAdmin;
    }

    // VULNERABLE: Anyone can grant minter role
    function setMinter(address user, bool isMinter) external {
        minters[user] = isMinter;
    }

    function mint(address to, uint256 amount) external {
        require(minters[msg.sender], "Not minter");
        // ... mint tokens
    }
}
```

## Vulnerable Pattern - Self-Escalation

```solidity
contract SelfEscalation {
    mapping(address => uint8) public roles;  // 0=user, 1=mod, 2=admin

    // VULNERABLE: Any role can escalate to any higher role
    function upgradeRole(uint8 newRole) external {
        require(newRole > roles[msg.sender], "Can only upgrade");
        roles[msg.sender] = newRole;  // Self-escalation!
    }
}
```

## Vulnerable Pattern - Weak Hierarchy

```solidity
contract WeakHierarchy {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER");

    mapping(bytes32 => mapping(address => bool)) public roles;

    // VULNERABLE: Minters can grant admin role
    function grantRole(bytes32 role, address user) external {
        require(roles[MINTER_ROLE][msg.sender], "Not minter");  // Wrong check!
        roles[role][user] = true;
    }
}
```

## Safe Pattern - Proper Role Hierarchy

```solidity
import "@openzeppelin/contracts/access/AccessControl.sol";

contract SafeRoles is AccessControl {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setRoleAdmin(MINTER_ROLE, ADMIN_ROLE);
    }

    // SAFE: Only admins can grant minter role
    function grantMinterRole(address user) external onlyRole(ADMIN_ROLE) {
        grantRole(MINTER_ROLE, user);
    }
}
```

## Safe Pattern - Two-Step Ownership

```solidity
import "@openzeppelin/contracts/access/Ownable2Step.sol";

contract SafeOwnership is Ownable2Step {
    // SAFE: Two-step process prevents accidental/malicious transfers
    // 1. Owner calls transferOwnership(newOwner)
    // 2. New owner must call acceptOwnership()
}
```

## Variations

### Hidden Admin Backdoor

```solidity
// Vulnerable - developer backdoor
function emergencyAdmin() external {
    if (msg.sender == 0x1234...dead) {  // Hardcoded address
        admins[msg.sender] = true;  // Hidden escalation
    }
}
```

### Race Condition in Role Update

```solidity
// Vulnerable - race condition
function updateAdmin(address newAdmin) external {
    require(admins[msg.sender], "Not admin");
    // Attacker front-runs to add themselves before removal
    admins[newAdmin] = true;
    admins[msg.sender] = false;
}
```
