# Patterns: Delegatecall Control

## Vulnerable Patterns

### Pattern 1: Direct Parameter Delegatecall

**Signature:** `R:param->DELEGATECALL`

```solidity
contract VulnerableDelegateCall {
    function delegate(address target, bytes calldata data) public {
        target.delegatecall(data);  // VULNERABLE
    }
}
```

**Operations:**
- `READS_USER_INPUT` (target parameter)
- `USES_DELEGATECALL`

**Why Vulnerable:**
- User directly controls target address
- No validation
- Public access
- Can execute arbitrary code in contract context

**Attack:**
```solidity
contract Exploit {
    address owner;

    function attack() external {
        // This will overwrite VulnerableDelegateCall's storage slot 0
        owner = msg.sender;
    }
}

// Attacker calls:
// vulnerable.delegate(exploitAddress, abi.encodeWithSignature("attack()"))
```

---

### Pattern 2: User-Set Implementation

**Signature:** `W:storage->DELEGATECALL`

```solidity
contract VulnerableProxy {
    address public implementation;

    function setImplementation(address newImpl) public {
        implementation = newImpl;  // VULNERABLE: No validation
    }

    function execute(bytes calldata data) public {
        implementation.delegatecall(data);  // Uses user-set address
    }
}
```

**Operations:**
- `WRITES_PRIVILEGED_STATE` (implementation address)
- `USES_DELEGATECALL`

**Why Vulnerable:**
- Anyone can set implementation
- No whitelist check
- Delegatecall uses attacker's address

---

### Pattern 3: Index-Based Target Selection

**Signature:** `R:array[index]->DELEGATECALL`

```solidity
contract VulnerableMulticall {
    address[] public targets;

    function addTarget(address target) public {
        targets.push(target);  // VULNERABLE: Anyone can add
    }

    function delegateToTarget(uint index, bytes calldata data) public {
        require(index < targets.length);
        targets[index].delegatecall(data);  // VULNERABLE
    }
}
```

**Operations:**
- `MODIFIES_ARRAY` (targets)
- `READS_ARRAY` (targets[index])
- `USES_DELEGATECALL`

**Why Vulnerable:**
- Attacker can add malicious target
- Then delegatecall to it via index

---

### Pattern 4: Library Delegatecall Without Validation

```solidity
contract VulnerableLibraryUser {
    mapping(string => address) public libraries;

    function setLibrary(string memory name, address lib) public {
        libraries[name] = lib;  // VULNERABLE
    }

    function callLibrary(string memory name, bytes calldata data) public {
        libraries[name].delegatecall(data);  // VULNERABLE
    }
}
```

**Operations:**
- `WRITES_MAPPING` (libraries)
- `READS_MAPPING` (libraries[name])
- `USES_DELEGATECALL`

---

## Safe Patterns

### Pattern 1: Whitelisted Targets

**Signature:** `CHECK:whitelist->DELEGATECALL`

```solidity
contract SafeDelegateCall {
    mapping(address => bool) public trustedTargets;
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }

    function addTrustedTarget(address target) public onlyOwner {
        trustedTargets[target] = true;
    }

    function delegate(address target, bytes calldata data) public {
        require(trustedTargets[target], "Untrusted target");  // ✓ SAFE
        target.delegatecall(data);
    }
}
```

**Safe Properties:**
- `delegatecall_target_whitelisted: true`
- `has_access_gate: true` (on addTrustedTarget)
- Validation before delegatecall

---

### Pattern 2: Hardcoded Target

**Signature:** `CONST->DELEGATECALL`

```solidity
contract SafeProxy {
    address public constant IMPLEMENTATION = 0x123...;  // ✓ Immutable

    function execute(bytes calldata data) public {
        IMPLEMENTATION.delegatecall(data);  // ✓ SAFE (fixed target)
    }
}
```

**Safe Properties:**
- `delegatecall_target_user_controlled: false`
- Target is constant, cannot be changed

---

### Pattern 3: Admin-Only Control

**Signature:** `ADMIN->W:storage->DELEGATECALL`

```solidity
contract SafeUpgradeableProxy {
    address public implementation;
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }

    function setImplementation(address newImpl) public onlyOwner {
        // Additional validation
        require(newImpl != address(0));
        require(newImpl.code.length > 0);  // Must be contract

        implementation = newImpl;  // ✓ SAFE (owner-only)
    }

    function execute(bytes calldata data) public {
        implementation.delegatecall(data);
    }
}
```

**Safe Properties:**
- `has_access_gate: true`
- `delegatecall_target_admin_controlled: true`
- Validation: non-zero, has code

---

### Pattern 4: Immutable After Construction

```solidity
contract SafeImmutableProxy {
    address public immutable implementation;

    constructor(address _implementation) {
        require(_implementation != address(0));
        require(_implementation.code.length > 0);
        implementation = _implementation;
    }

    function execute(bytes calldata data) public {
        implementation.delegatecall(data);  // ✓ SAFE (immutable)
    }
}
```

**Safe Properties:**
- `delegatecall_target_immutable: true`
- Set once in constructor
- Cannot be changed post-deployment

---

## Pattern Variations

### Callcode (Deprecated)

```solidity
// VULNERABLE (and deprecated)
function delegateViaCallcode(address target, bytes calldata data) public {
    target.callcode(data);  // Same vulnerability as delegatecall
}
```

**Note:** `callcode` is deprecated but has same security implications as `delegatecall`.

### Inline Assembly

```solidity
// VULNERABLE
function delegateAsm(address target, bytes calldata data) public {
    assembly {
        let result := delegatecall(
            gas(),
            target,          // VULNERABLE: User-controlled
            add(data, 0x20),
            mload(data),
            0,
            0
        )
    }
}
```

---

## Detection Discriminators

**Vulnerable if ALL:**
1. Uses delegatecall/callcode
2. Target is user-controlled (parameter, user-set storage, user-modified array)
3. No whitelist validation
4. No access control OR public/external

**Safe if ANY:**
1. Target is hardcoded/constant
2. Target validated against whitelist
3. Function restricted to admin/owner
4. Target is immutable (set in constructor)

---

**Source:** Slither Detector Documentation
**Added:** 2026-01-09
**Pattern Count:** 4 vulnerable, 4 safe
