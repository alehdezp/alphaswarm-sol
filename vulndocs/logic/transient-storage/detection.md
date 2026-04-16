# Transient Storage Misuse - Detection Guide

## Overview

Transient storage (EIP-1153, Cancun upgrade 2024) provides transaction-scoped storage that resets between transactions. Misuse occurs when protocols use transient storage for security-critical state without proper validation, allowing attackers to inject malicious values during callbacks.

## Detection Signals

### Tier A: Deterministic Detection

**Primary Signals (VKG Properties):**

1. **Uses Transient Storage**
   - Property: `uses_transient_storage`
   - Detection: Function contains TSTORE or TLOAD opcodes
   - Confidence: 95%

2. **External Calls Present**
   - Property: `external_call_sites > 0`
   - Detection: Function makes external calls that could callback
   - Confidence: 85%

3. **Transient Value in Access Check**
   - Property: `transient_value_in_access_check`
   - Detection: Access control logic reads from transient storage
   - Confidence: 90%

**Semantic Operations:**

- `STORES_TRANSIENT_VALUE` - Uses TSTORE opcode
- `LOADS_TRANSIENT_VALUE` - Uses TLOAD opcode
- `CALLS_EXTERNAL` - External call that may callback
- `CHECKS_PERMISSION` - Access control verification

**Behavioral Signature:**

Vulnerable: `T:store->X:call->C:access{T:load}`
- Store value to transient storage
- Make external call (callback opportunity)
- Access check reads transient storage

Safe: `T:store->C:validate->T:load`
- Validate transient value before critical use

### Tier B: LLM Reasoning Required

**Context Questions:**

1. Is transient storage used for authentication or authorization state?
2. Can external calls callback before transient value is consumed?
3. Is there validation that transient values were set by authorized code?
4. Could attacker control transient storage slots during callback?

**False Positive Indicators:**

- Transient storage only for temporary calculations (no security impact)
- Transient values validated against expected constants
- Reentrancy guard prevents callback manipulation
- Transient storage used only for read caching

## Manual Checks

Auditors should verify:

1. **Identify Transient Usage**
   - Search for `tstore`/`tload` in assembly blocks
   - Check Solidity 0.8.24+ transient keyword usage
   - Map which transient slots are used for what purpose

2. **Trace Callback Paths**
   - Identify all external calls in functions using transient storage
   - Map potential callback paths (ERC777 hooks, fallbacks, etc.)
   - Determine if callbacks can reach functions reading transient values

3. **Validate Security Boundaries**
   - Check if access control depends on transient values
   - Verify transient values are validated before security decisions
   - Ensure attacker cannot inject arbitrary transient values

4. **Review Transaction Lifecycle**
   - Confirm transient values reset between transactions
   - Check for race conditions in multi-call scenarios
   - Verify expected vs actual transient semantics

## Automated Checks

```yaml
check_1:
  type: property_match
  conditions:
    - uses_transient_storage: true
    - external_call_sites > 0
  risk: medium

check_2:
  type: sequence_order
  pattern:
    - STORES_TRANSIENT_VALUE
    - CALLS_EXTERNAL
    - LOADS_TRANSIENT_VALUE (in access check)
  risk: high

check_3:
  type: property_absence
  conditions:
    - uses_transient_storage: true
    - validates_transient_before_use: false
  risk: high
```

## Code Patterns

### Vulnerable Pattern

```solidity
// Transient storage for "authentication" (VULNERABLE)
contract VulnerableAuth {
    // Transient storage slot
    bytes32 private constant AUTH_SLOT = keccak256("auth.transient");

    function processWithCallback(address token) external {
        // Set transient auth flag
        assembly {
            tstore(AUTH_SLOT, 1)
        }

        // External call - callback opportunity!
        IERC20(token).transfer(msg.sender, amount);

        // Clear flag
        assembly {
            tstore(AUTH_SLOT, 0)
        }
    }

    function protectedFunction() external {
        uint256 authorized;
        assembly {
            authorized := tload(AUTH_SLOT)
        }

        // VULNERABLE: Trusts transient value without validation
        require(authorized == 1, "Unauthorized");

        // Critical operation
        _mintTokens(msg.sender);
    }
}

// Attack:
// 1. Call processWithCallback() with malicious token
// 2. In token's transfer callback, call protectedFunction()
// 3. protectedFunction() sees AUTH_SLOT = 1 (set by victim)
// 4. Access granted to attacker!
```

### Safe Pattern 1: Validate Transient Values

```solidity
contract SafeAuth {
    bytes32 private constant AUTH_SLOT = keccak256("auth.transient");
    bytes32 private constant NONCE_SLOT = keccak256("nonce.transient");
    uint256 private authNonce;

    function processWithCallback(address token) external {
        authNonce++;

        assembly {
            tstore(AUTH_SLOT, 1)
            tstore(NONCE_SLOT, authNonce)  // Store expected nonce
        }

        IERC20(token).transfer(msg.sender, amount);

        assembly {
            tstore(AUTH_SLOT, 0)
            tstore(NONCE_SLOT, 0)
        }
    }

    function protectedFunction() external {
        uint256 authorized;
        uint256 nonce;

        assembly {
            authorized := tload(AUTH_SLOT)
            nonce := tload(NONCE_SLOT)
        }

        // SAFE: Validate nonce matches expected value
        require(authorized == 1 && nonce == authNonce, "Unauthorized");

        _mintTokens(msg.sender);
    }
}
```

### Safe Pattern 2: Use Reentrancy Guard

```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract SafeWithGuard is ReentrancyGuard {
    bytes32 private constant AUTH_SLOT = keccak256("auth.transient");

    function processWithCallback(address token) external nonReentrant {
        assembly {
            tstore(AUTH_SLOT, 1)
        }

        IERC20(token).transfer(msg.sender, amount);

        assembly {
            tstore(AUTH_SLOT, 0)
        }
    }

    function protectedFunction() external nonReentrant {
        // SAFE: Reentrancy guard prevents callback attacks
        uint256 authorized;
        assembly {
            authorized := tload(AUTH_SLOT)
        }
        require(authorized == 1, "Unauthorized");
        _mintTokens(msg.sender);
    }
}
```

### Safe Pattern 3: Avoid Transient for Security State

```solidity
contract BestPractice {
    // Use regular storage for security-critical state
    mapping(address => bool) private authorized;

    // Reserve transient for non-critical temporary values
    bytes32 private constant TEMP_CALC_SLOT = keccak256("temp.calc");

    function authorize(address user) external onlyOwner {
        authorized[user] = true;  // Regular storage
    }

    function protectedFunction() external {
        require(authorized[msg.sender], "Unauthorized");

        // OK to use transient for temporary calculations
        assembly {
            let temp := mul(balance, rate)
            tstore(TEMP_CALC_SLOT, temp)
        }

        _executeWithTempValue();
    }
}
```

## Detection Tools

- **Slither**: May detect transient storage usage (check latest version)
- **Mythril**: Symbolic execution can trace callback paths
- **Manual Review**: Essential for validating transient semantics

## References

- EIP-1153: Transient Storage Opcodes
- SIR Protocol Exploit: https://www.coveragelabs.io/blog/post/sir-exploit
- Solidity 0.8.24 Release Notes
