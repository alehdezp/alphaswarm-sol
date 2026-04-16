# Transient Storage Misuse - Code Patterns

## Vulnerable Patterns

### Pattern 1: Callback Access Control Bypass

**Vulnerability:** Access control flag stored in transient storage, checked after external call.

```solidity
// VULNERABLE: Transient flag manipulated during callback
contract VulnerableCallback {
    bytes32 private constant IS_AUTHORIZED = keccak256("is.authorized");

    function initiateOperation(address externalContract) external {
        // Set authorization flag
        assembly { tstore(IS_AUTHORIZED, 1) }

        // External call - attacker callbacks here
        IExternal(externalContract).notify();

        // Clear flag
        assembly { tstore(IS_AUTHORIZED, 0) }
    }

    function privilegedAction() external {
        uint256 auth;
        assembly { auth := tload(IS_AUTHORIZED) }

        // VULNERABLE: Attacker's callback sees auth=1
        require(auth == 1, "Not authorized");

        _criticalOperation();
    }
}
```

**Operations:** `STORES_TRANSIENT_VALUE`, `CALLS_EXTERNAL`, `LOADS_TRANSIENT_VALUE`, `CHECKS_PERMISSION`

**Signature:** `T:store->X:call->C:access{T:load}`

---

### Pattern 2: Unvalidated Transient State

**Vulnerability:** Using transient storage values without validating their origin.

```solidity
// VULNERABLE: No validation of transient value source
contract UnvalidatedTransient {
    bytes32 private constant USER_TIER = keccak256("user.tier");

    function setTierAndProcess(uint256 tier, address callback) external {
        assembly { tstore(USER_TIER, tier) }

        // Callback opportunity
        if (callback != address(0)) {
            ICallback(callback).onProcess();
        }

        _applyTierBenefits();
    }

    function _applyTierBenefits() internal {
        uint256 tier;
        assembly { tier := tload(USER_TIER) }

        // VULNERABLE: No check that tier was set by authorized caller
        if (tier >= 3) {
            _grantPremiumAccess();
        }
    }
}
```

**Operations:** `STORES_TRANSIENT_VALUE`, `CALLS_EXTERNAL`, `LOADS_TRANSIENT_VALUE`

**Signature:** `T:store->X:call->T:load{unvalidated}`

---

### Pattern 3: Multi-Function Transient Sharing

**Vulnerability:** Multiple functions sharing transient storage without synchronization.

```solidity
// VULNERABLE: Shared transient slot across functions
contract SharedTransient {
    bytes32 private constant TEMP_AMOUNT = keccak256("temp.amount");

    function withdraw(uint256 amount, address token) external {
        assembly { tstore(TEMP_AMOUNT, amount) }

        // External call before consuming transient value
        IERC20(token).transferFrom(msg.sender, address(this), amount);

        _processWithdrawal();
    }

    function _processWithdrawal() internal {
        uint256 amount;
        assembly { amount := tload(TEMP_AMOUNT) }

        // VULNERABLE: Callback could modify TEMP_AMOUNT
        balances[msg.sender] += amount;
    }
}
```

**Operations:** `STORES_TRANSIENT_VALUE`, `CALLS_EXTERNAL`, `LOADS_TRANSIENT_VALUE`

**Signature:** `T:store->X:call->T:load{shared_slot}`

---

## Safe Patterns

### Safe Pattern 1: Nonce-Based Validation

**Fix:** Validate transient values with storage-based nonces.

```solidity
// SAFE: Nonce prevents injection
contract SafeNonceValidation {
    bytes32 private constant IS_AUTHORIZED = keccak256("is.authorized");
    bytes32 private constant AUTH_NONCE_SLOT = keccak256("auth.nonce");

    uint256 private authNonce;  // Storage-based counter

    function initiateOperation(address externalContract) external {
        authNonce++;  // Increment in storage

        // Store both flag and nonce
        assembly {
            tstore(IS_AUTHORIZED, 1)
            tstore(AUTH_NONCE_SLOT, sload(authNonce.slot))
        }

        IExternal(externalContract).notify();

        assembly {
            tstore(IS_AUTHORIZED, 0)
            tstore(AUTH_NONCE_SLOT, 0)
        }
    }

    function privilegedAction() external {
        uint256 auth;
        uint256 nonce;

        assembly {
            auth := tload(IS_AUTHORIZED)
            nonce := tload(AUTH_NONCE_SLOT)
        }

        // SAFE: Verify nonce matches expected value
        require(
            auth == 1 && nonce == authNonce,
            "Invalid auth state"
        );

        _criticalOperation();
    }
}
```

**Operations:** `WRITES_STORAGE`, `STORES_TRANSIENT_VALUE`, `LOADS_TRANSIENT_VALUE`, `VALIDATES_STATE`

**Signature:** `W:nonce->T:store{auth+nonce}->X:call->T:load->C:validate{nonce}`

---

### Safe Pattern 2: ReentrancyGuard Protection

**Fix:** Use reentrancy guard to prevent callback manipulation.

```solidity
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

// SAFE: Reentrancy guard blocks callbacks
contract SafeWithGuard is ReentrancyGuard {
    bytes32 private constant IS_AUTHORIZED = keccak256("is.authorized");

    function initiateOperation(address externalContract) external nonReentrant {
        assembly { tstore(IS_AUTHORIZED, 1) }

        IExternal(externalContract).notify();

        assembly { tstore(IS_AUTHORIZED, 0) }
    }

    function privilegedAction() external nonReentrant {
        uint256 auth;
        assembly { auth := tload(IS_AUTHORIZED) }

        // SAFE: nonReentrant prevents callback during initiateOperation
        require(auth == 1, "Not authorized");

        _criticalOperation();
    }
}
```

**Operations:** `CHECKS_REENTRANCY_GUARD`, `STORES_TRANSIENT_VALUE`, `CALLS_EXTERNAL`

**Signature:** `G:nonReentrant->T:store->X:call`

---

### Safe Pattern 3: Storage for Security, Transient for Performance

**Fix:** Use regular storage for security-critical state.

```solidity
// SAFE: Separate security and performance concerns
contract BestPractice {
    // Security-critical: Regular storage
    mapping(address => bool) private authorized;
    mapping(address => uint256) private userTier;

    // Performance optimization: Transient storage
    bytes32 private constant TEMP_CALC = keccak256("temp.calc");

    function authorizeUser(address user, uint256 tier) external onlyOwner {
        authorized[user] = true;      // Storage
        userTier[user] = tier;        // Storage
    }

    function privilegedAction() external {
        // SAFE: Read from storage
        require(authorized[msg.sender], "Not authorized");

        uint256 tier = userTier[msg.sender];

        // OK: Transient for temporary calculations
        assembly {
            let calc := mul(tier, 100)
            tstore(TEMP_CALC, calc)
        }

        _executeWithTempValue();
    }

    function _executeWithTempValue() internal view {
        uint256 calc;
        assembly { calc := tload(TEMP_CALC) }

        // Use calc for read-only operations
    }
}
```

**Operations:** `WRITES_STORAGE`, `READS_STORAGE`, `STORES_TRANSIENT_VALUE` (non-critical)

**Signature:** `W:storage{auth}->R:storage{auth}->T:store{temp_calc}`

---

### Safe Pattern 4: Explicit Transient Lifecycle

**Fix:** Clear transient values immediately after use, validate before reads.

```solidity
// SAFE: Explicit lifecycle management
contract ExplicitLifecycle {
    bytes32 private constant PROCESS_FLAG = keccak256("process.flag");

    function processOperation(address token) external {
        // Set flag with known value
        bytes32 expectedValue = keccak256(abi.encodePacked(msg.sender, block.timestamp));

        assembly { tstore(PROCESS_FLAG, expectedValue) }

        // External call
        IERC20(token).transfer(address(this), amount);

        // Immediately validate and consume
        bytes32 actual;
        assembly {
            actual := tload(PROCESS_FLAG)
            tstore(PROCESS_FLAG, 0)  // Clear immediately
        }

        // SAFE: Verify value wasn't tampered
        require(actual == expectedValue, "Transient value corrupted");

        _completeProcess();
    }
}
```

**Operations:** `STORES_TRANSIENT_VALUE`, `CALLS_EXTERNAL`, `LOADS_TRANSIENT_VALUE`, `VALIDATES_VALUE`

**Signature:** `T:store{hash}->X:call->T:load->C:validate{hash}->T:clear`

---

## Pattern Comparison Table

| Pattern | Uses Transient | Has Callback | Validates Value | Safe? |
|---------|---------------|--------------|-----------------|-------|
| Callback Access Bypass | Yes | Yes | No | No |
| Unvalidated Transient | Yes | Yes | No | No |
| Shared Transient Slot | Yes | Yes | No | No |
| Nonce Validation | Yes | Yes | Yes (nonce) | Yes |
| ReentrancyGuard | Yes | Yes (blocked) | N/A | Yes |
| Storage for Security | No (for auth) | Yes | Yes (storage) | Yes |
| Explicit Lifecycle | Yes | Yes | Yes (hash) | Yes |

## Detection Summary

**High Risk Combination:**
- Uses transient storage: `STORES_TRANSIENT_VALUE`, `LOADS_TRANSIENT_VALUE`
- Makes external calls: `CALLS_EXTERNAL`
- No validation: `validates_transient_before_use = false`
- Used in access control: `transient_value_in_access_check = true`

**Safe Indicators:**
- Reentrancy guard present: `has_reentrancy_guard = true`
- Nonce validation: `validates_with_storage_nonce = true`
- Transient only for calculations: `transient_only_for_temp_values = true`
- Immediate clear after use: `clears_transient_immediately = true`
