# Fixes: Delegatecall Control

## Remediation Strategies

### Fix 1: Whitelist Validation (Recommended)

**Effectiveness:** High
**Complexity:** Medium

**Safe Pattern:**
```solidity
contract SafeDelegateCall {
    mapping(address => bool) public trustedTargets;
    address public owner;

    event TargetAdded(address indexed target);
    event TargetRemoved(address indexed target);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function addTrustedTarget(address target) external onlyOwner {
        require(target != address(0), "Zero address");
        require(target.code.length > 0, "Not a contract");

        trustedTargets[target] = true;
        emit TargetAdded(target);
    }

    function removeTrustedTarget(address target) external onlyOwner {
        trustedTargets[target] = false;
        emit TargetRemoved(target);
    }

    function delegate(address target, bytes calldata data) external {
        require(trustedTargets[target], "Target not trusted");
        (bool success, ) = target.delegatecall(data);
        require(success, "Delegatecall failed");
    }
}
```

**Properties:**
- `delegatecall_target_whitelisted: true`
- `has_access_gate: true` (on whitelist management)
- Events for monitoring

---

### Fix 2: Hardcoded/Immutable Target

**Effectiveness:** High
**Complexity:** Low

**Safe Pattern:**
```solidity
contract SafeProxy {
    address public immutable implementation;

    constructor(address _implementation) {
        require(_implementation != address(0), "Zero address");
        require(_implementation.code.length > 0, "Not a contract");
        implementation = _implementation;
    }

    function execute(bytes calldata data) external returns (bytes memory) {
        (bool success, bytes memory result) = implementation.delegatecall(data);
        require(success, "Execution failed");
        return result;
    }
}
```

**Properties:**
- `delegatecall_target_immutable: true`
- Set once in constructor
- Cannot be changed

---

### Fix 3: Access Control on Target Setter

**Effectiveness:** High
**Complexity:** Low

**Safe Pattern:**
```solidity
import "@openzeppelin/contracts/access/Ownable.sol";

contract SafeUpgradeable is Ownable {
    address public implementation;

    event ImplementationUpgraded(address indexed oldImpl, address indexed newImpl);

    function upgradeImplementation(address newImpl) external onlyOwner {
        require(newImpl != address(0), "Zero address");
        require(newImpl.code.length > 0, "Not a contract");
        require(newImpl != implementation, "Same implementation");

        address oldImpl = implementation;
        implementation = newImpl;

        emit ImplementationUpgraded(oldImpl, newImpl);
    }

    function delegateCall(bytes calldata data) external returns (bytes memory) {
        require(implementation != address(0), "No implementation");
        (bool success, bytes memory result) = implementation.delegatecall(data);
        require(success, "Delegatecall failed");
        return result;
    }
}
```

**Library:** `Ownable` from OpenZeppelin

---

### Fix 4: Use Regular Call Instead

**Effectiveness:** High (if delegatecall not needed)
**Complexity:** Low

**Rationale:**
If storage access in target context is not required, use regular `call` instead.

**Before (Vulnerable):**
```solidity
function delegate(address target, bytes calldata data) external {
    target.delegatecall(data);  // VULNERABLE
}
```

**After (Safe):**
```solidity
function regularCall(address target, bytes calldata data) external {
    (bool success, ) = target.call(data);  // ✓ SAFE
    require(success, "Call failed");
}
```

**Trade-off:**
- Regular `call` executes in target's context, not caller's
- Cannot modify caller's storage
- Safer for most use cases

---

### Fix 5: Proxy with Timelock

**Effectiveness:** High
**Complexity:** High

**Safe Pattern:**
```solidity
import "@openzeppelin/contracts/governance/TimelockController.sol";

contract TimelockProxy {
    address public implementation;
    address public pendingImplementation;
    uint256 public upgradeDelay = 2 days;
    uint256 public upgradeETA;

    event UpgradeScheduled(address indexed newImpl, uint256 eta);
    event UpgradeExecuted(address indexed oldImpl, address indexed newImpl);

    function scheduleUpgrade(address newImpl) external onlyOwner {
        require(newImpl != address(0), "Zero address");
        require(newImpl.code.length > 0, "Not a contract");

        pendingImplementation = newImpl;
        upgradeETA = block.timestamp + upgradeDelay;

        emit UpgradeScheduled(newImpl, upgradeETA);
    }

    function executeUpgrade() external onlyOwner {
        require(pendingImplementation != address(0), "No pending upgrade");
        require(block.timestamp >= upgradeETA, "Timelock not expired");

        address oldImpl = implementation;
        implementation = pendingImplementation;

        pendingImplementation = address(0);
        upgradeETA = 0;

        emit UpgradeExecuted(oldImpl, implementation);
    }

    function delegateCall(bytes calldata data) external returns (bytes memory) {
        require(implementation != address(0), "No implementation");
        (bool success, bytes memory result) = implementation.delegatecall(data);
        require(success, "Delegatecall failed");
        return result;
    }
}
```

**Benefits:**
- Users have warning before upgrade
- Can exit if malicious upgrade detected
- Prevents instant rug pulls

---

### Fix 6: Storage Layout Validation

**Effectiveness:** Medium
**Complexity:** High

**Approach:**
Ensure target contract has compatible storage layout.

**Tools:**
- OpenZeppelin Upgrades Plugin
- Storage layout checks in tests

**Example (Hardhat):**
```javascript
const { upgradeProxy } = require('@openzeppelin/hardhat-upgrades');

// Validates storage layout compatibility
await upgradeProxy(proxyAddress, NewImplementation);
```

---

### Fix 7: Avoid Delegatecall Entirely

**Effectiveness:** Very High
**Complexity:** Varies

**Alternatives:**

1. **Diamond Pattern (EIP-2535):**
   - Structured approach to delegatecall
   - Facet registry with strict validation

2. **Minimal Proxy (EIP-1167):**
   - Clone pattern for identical instances
   - Fixed implementation

3. **Registry Pattern:**
   - Separate contracts, no delegatecall
   - Coordination via registry

---

## Fix Decision Tree

```
Do you NEED delegatecall?
├─ NO → Use regular call()
│
└─ YES
   ├─ Single fixed target?
   │  └─ YES → Use immutable/constant address
   │
   └─ Multiple or changing targets?
      ├─ User selectable?
      │  └─ YES → Implement whitelist + access control
      │
      └─ Admin only?
         └─ YES → Access control + timelock + events
```

---

## Safe Properties Checklist

**After implementing fixes, ensure:**

```yaml
safe_properties:
  - delegatecall_target_whitelisted: true OR
  - delegatecall_target_immutable: true OR
  - delegatecall_target_admin_controlled: true

  - has_access_gate: true  # On target setters
  - has_target_validation: true  # Non-zero, has code
  - emits_events: true  # For monitoring
  - has_emergency_pause: true  # Optional but recommended
```

---

## OpenZeppelin Libraries

### Recommended Libraries

1. **Ownable/AccessControl**
   ```solidity
   import "@openzeppelin/contracts/access/Ownable.sol";
   import "@openzeppelin/contracts/access/AccessControl.sol";
   ```

2. **UUPSUpgradeable**
   ```solidity
   import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
   ```
   - Built-in upgrade authorization
   - Storage layout validation

3. **TransparentUpgradeableProxy**
   ```solidity
   import "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
   ```
   - Separates admin and user calls
   - Prevents selector clashing

---

## Testing Recommendations

### Test Cases

```solidity
// 1. Test unauthorized delegatecall attempts
function testUnauthorizedDelegatecall() public {
    vm.prank(attacker);
    vm.expectRevert("Target not trusted");
    contract.delegate(maliciousAddress, data);
}

// 2. Test whitelist enforcement
function testWhitelistEnforcement() public {
    assertFalse(contract.trustedTargets(maliciousAddress));

    vm.prank(owner);
    contract.addTrustedTarget(trustedAddress);

    assertTrue(contract.trustedTargets(trustedAddress));
}

// 3. Test storage layout preservation
function testStorageLayoutPreserved() public {
    address originalOwner = contract.owner();

    contract.delegate(trustedTarget, data);

    assertEq(contract.owner(), originalOwner, "Owner changed!");
}

// 4. Test access control on setters
function testOnlyOwnerCanSetTarget() public {
    vm.prank(attacker);
    vm.expectRevert("Not owner");
    contract.addTrustedTarget(someAddress);
}
```

---

## Migration Guide

### From Vulnerable to Safe

**Step 1:** Identify all delegatecall usage
```bash
slither contract.sol --detect controlled-delegatecall
```

**Step 2:** Choose fix strategy (whitelist, immutable, or access control)

**Step 3:** Implement chosen fix

**Step 4:** Add events for monitoring

**Step 5:** Test thoroughly
- Unit tests for access control
- Fuzz testing for edge cases
- Storage layout tests

**Step 6:** Add monitoring
- Event monitoring for target changes
- Alerts on unexpected delegatecalls

**Step 7:** Consider timelock for upgrades

---

**Recommended Reading:**
- OpenZeppelin Proxy Patterns: https://docs.openzeppelin.com/contracts/4.x/api/proxy
- EIP-1967 (Proxy Storage Slots): https://eips.ethereum.org/EIPS/eip-1967
- SWC-112 (Delegatecall to Untrusted Callee): https://swcregistry.io/docs/SWC-112

**Added:** 2026-01-09
**Fix Strategies:** 7
