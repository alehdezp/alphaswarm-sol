# Detection: Delegatecall Control

## Identification Signals

### Semantic Operations
- `USES_DELEGATECALL` - Function contains delegatecall/callcode
- `READS_USER_INPUT` - Target address derived from user input
- `MODIFIES_CRITICAL_STATE` - Can affect contract storage

### Behavioral Signature
```
R:input->DELEGATECALL:target
```
Read user input → delegatecall to user-controlled target

### Graph Properties

**Vulnerable Pattern:**
```yaml
properties:
  uses_delegatecall: true
  delegatecall_target_user_controlled: true
  has_access_gate: false
  visibility: [public, external]
```

**Safe Pattern:**
```yaml
properties:
  uses_delegatecall: true
  delegatecall_target_whitelisted: true
  has_access_gate: true
```

## Detection Method

### Tier A (Deterministic)

**Core Signal:**
```yaml
all:
  - property: uses_delegatecall
    value: true
  - property: delegatecall_target_user_controlled
    value: true

none:
  - property: has_access_gate
    value: true
  - property: delegatecall_target_whitelisted
    value: true
```

### Tier B (LLM Reasoning)

**Context Questions:**
1. Is the delegatecall target derived from user input (function parameter, storage set by users)?
2. Is there a whitelist validation for allowed targets?
3. Can an attacker supply arbitrary addresses?
4. Is the data payload also user-controlled?

**False Positive Indicators:**
- Target is hardcoded address
- Target validated against mapping of trusted addresses
- Function restricted to admin/owner only
- Target is immutable storage set in constructor

## Attack Preconditions

1. **Target Control:** User can specify delegatecall target address
2. **Data Control (optional):** User can control calldata payload
3. **No Validation:** No whitelist or validation of target address
4. **Public Access:** Function is public/external without access control

## Attack Postconditions

1. **Storage Manipulation:** Attacker's code executes in contract context
2. **Fund Extraction:** Can withdraw all contract funds
3. **Self-Destruction:** Can call selfdestruct
4. **Privilege Escalation:** Can modify owner/admin variables

## Code Pattern Detection

### Vulnerable Pattern

```solidity
function delegate(address to, bytes data) public {
    to.delegatecall(data);  // ← User controls 'to'
}
```

**Signals:**
- Parameter `to` is `address` type
- No validation/whitelist check on `to`
- No access modifier (public/external to all)

### Additional Vulnerable Patterns

```solidity
// User sets target in storage
address public implementation;
function setImplementation(address impl) public {
    implementation = impl;  // No validation
}
function execute(bytes data) public {
    implementation.delegatecall(data);  // Uses user-set address
}
```

```solidity
// Array of targets, user chooses index
address[] public targets;
function delegateToTarget(uint index, bytes data) public {
    targets[index].delegatecall(data);  // User controls index
}
```

## Detection Checklist

**Manual Checks:**
- [ ] Identify all delegatecall/callcode usage
- [ ] Trace target address source (parameter, storage, computation)
- [ ] Check for whitelist validation
- [ ] Verify access control on delegatecall functions
- [ ] Review data payload control
- [ ] Check for emergency pause mechanisms

**Automated Checks:**
```yaml
checks:
  - check: "uses_delegatecall"
    expected: true

  - check: "delegatecall_target_source"
    expected: "user_input"  # Parameter or user-set storage

  - check: "has_target_whitelist"
    expected: false  # Vulnerability if false

  - check: "has_access_gate"
    expected: false  # Vulnerability if false
```

## Slither Detector

**Detector:** `controlled-delegatecall`
**Severity:** High
**Confidence:** Medium

**Detection Logic:**
- Identifies delegatecall/callcode to addresses that can be controlled by users
- Checks if target is derived from function parameters or user-modifiable storage

**Command:**
```bash
slither contract.sol --detect controlled-delegatecall
```

## Related Detection Patterns

1. **Uninitialized Proxy** - Delegatecall to unset implementation
2. **Storage Collision** - Delegatecall causing storage overwrites
3. **Selfdestruct** - Delegatecall to contract with selfdestruct

---

**Source:** Slither Detector Documentation
**Added:** 2026-01-09
**Confidence:** High (validated by Slither tooling)
