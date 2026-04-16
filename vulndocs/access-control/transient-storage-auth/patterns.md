# Code Patterns: Transient Storage Authentication Bypass

## Vulnerable Pattern

### Direct Transient Storage Auth

```solidity
// VULNERABLE: Uses transient storage for authentication
contract VulnerableVault {
    function uniswapCallback(
        int256 amount0,
        int256 amount1,
        bytes calldata data
    ) external {
        // Read authorized address from transient storage
        address authorized;
        assembly {
            authorized := tload(0x1)
        }

        // VULNERABLE: Attacker can overwrite slot 0x1 before this check
        require(msg.sender == authorized, "Unauthorized");

        // Execute privileged operation
        _mintTokens(amount0, amount1);
    }

    function swap(address pool, uint256 amount) external {
        // Store pool address in transient storage
        assembly {
            tstore(0x1, pool)
        }

        // External call (attacker can manipulate tstore during callback)
        IUniswapPool(pool).swap(address(this), amount, data);
    }
}
```

**Operations:**
- `WRITES_TRANSIENT_STORAGE` (tstore)
- `READS_TRANSIENT_STORAGE` (tload)
- `CHECKS_PERMISSION`
- `CALLS_EXTERNAL`

**Signature:** `W:tstore->X:call->W:tstore(malicious)->R:tload->CHECK:bypassed`

---

## Safe Pattern 1: State Variable Authentication

```solidity
// SAFE: Uses immutable state variable
contract SecureVault {
    address public immutable TRUSTED_POOL;

    constructor(address pool) {
        TRUSTED_POOL = pool;
    }

    function uniswapCallback(
        int256 amount0,
        int256 amount1,
        bytes calldata data
    ) external {
        // SAFE: Read from immutable storage, not transient
        require(msg.sender == TRUSTED_POOL, "Unauthorized");

        _mintTokens(amount0, amount1);
    }
}
```

**Operations:**
- `READS_STORAGE` (not transient)
- `CHECKS_PERMISSION`

**Safe Properties:**
- `uses_immutable_auth: true`
- `transient_storage_auth: false`

---

## Safe Pattern 2: Signature-Based Authentication

```solidity
// SAFE: Uses signature verification instead of transient storage
contract SecureVault {
    function executeCallback(
        int256 amount0,
        int256 amount1,
        bytes calldata signature
    ) external {
        // SAFE: Cryptographic authentication
        bytes32 messageHash = keccak256(abi.encode(amount0, amount1, msg.sender));
        address signer = ECDSA.recover(messageHash, signature);

        require(signer == TRUSTED_SIGNER, "Invalid signature");

        _mintTokens(amount0, amount1);
    }
}
```

**Operations:**
- `VALIDATES_SIGNATURE`
- `CHECKS_PERMISSION`

**Safe Properties:**
- `uses_signature_auth: true`
- `cryptographic_verification: true`

---

## Safe Pattern 3: Deterministic Pool Verification

```solidity
// SAFE: Verifies pool address via deterministic computation
contract SecureVault {
    address public immutable FACTORY;

    function uniswapCallback(
        int256 amount0,
        int256 amount1,
        bytes calldata data
    ) external {
        // SAFE: Compute expected pool address
        address expectedPool = IUniswapFactory(FACTORY).getPool(token0, token1, fee);

        require(msg.sender == expectedPool, "Unauthorized pool");

        _mintTokens(amount0, amount1);
    }
}
```

**Operations:**
- `CALLS_EXTERNAL(factory)` - read-only
- `VALIDATES_ADDRESS`
- `CHECKS_PERMISSION`

**Safe Properties:**
- `deterministic_validation: true`
- `uses_factory_verification: true`

---

## Anti-Pattern: Transient Storage + Callback

```solidity
// ANTI-PATTERN: Never use transient storage for auth in callback contexts
function authenticatedCallback() external {
    address auth;
    assembly {
        auth := tload(0x1)  // ❌ NEVER DO THIS
    }
    require(msg.sender == auth);
}
```

**Why Vulnerable:**
- Transient storage is transaction-scoped, not call-scoped
- Attacker can overwrite slots during callbacks
- No permanent record in state
- Cleared after transaction, leaving no audit trail
