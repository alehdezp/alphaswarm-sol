# Remediation: State Isolation Vulnerabilities

## Fix Strategies

### Strategy 1: Pool-Scoped Storage (Recommended)

**When to Use:**
- Hook/contract designed for multiple pools/instances
- State needs to be tracked per-pool
- Performance overhead acceptable (minimal)

**Implementation:**

```solidity
// BEFORE: Vulnerable
contract VulnerableHook {
    uint256 public totalAmount;
}

// AFTER: Fixed
contract SafeHook {
    mapping(PoolId => uint256) public totalAmount;
    // OR
    mapping(address => uint256) public totalAmountByPool;
}
```

**Full Example:**

```solidity
abstract contract MultiPoolSafeHook is IHook {
    using PoolIdLibrary for PoolKey;

    // ✅ All state scoped to pool
    mapping(PoolId => uint256) public totalLiquidity;
    mapping(PoolId => uint256) public totalFees;
    mapping(PoolId => mapping(address => uint256)) public userShares;
    mapping(PoolId => uint256) public lastUpdate;

    function afterAddLiquidity(
        address sender,
        PoolKey calldata key,
        uint256 liquidity
    ) external override returns (bytes4) {
        PoolId poolId = key.toId();

        totalLiquidity[poolId] += liquidity;
        userShares[poolId][sender] += liquidity;
        lastUpdate[poolId] = block.timestamp;

        return IHook.afterAddLiquidity.selector;
    }

    function getPoolState(PoolId poolId)
        external
        view
        returns (
            uint256 liquidity,
            uint256 fees,
            uint256 updated
        )
    {
        return (
            totalLiquidity[poolId],
            totalFees[poolId],
            lastUpdate[poolId]
        );
    }
}
```

**Pros:**
- Complete state isolation
- Supports unlimited pools
- No deployment constraints

**Cons:**
- Slight gas overhead (mapping lookup)
- More complex state management

---

### Strategy 2: Enforce Single-Pool Deployment

**When to Use:**
- Hook logically belongs to one pool
- State isolation not the primary concern
- Want gas optimization

**Implementation:**

```solidity
contract SinglePoolHook is IHook {
    // ✅ Immutable pool binding
    PoolId public immutable POOL_ID;
    address public immutable POOL_ADDRESS;

    uint256 public totalAmount;  // Safe: only one pool

    constructor(PoolKey memory poolKey) {
        POOL_ID = poolKey.toId();
        POOL_ADDRESS = address(poolKey.pool);
    }

    modifier onlyMyPool(PoolKey calldata key) {
        require(key.toId() == POOL_ID, "Unauthorized pool");
        _;
    }

    function afterSwap(
        address sender,
        PoolKey calldata key,
        SwapParams calldata params
    ) external override onlyMyPool(key) returns (bytes4) {
        totalAmount += params.amountSpecified;
        return IHook.afterSwap.selector;
    }
}
```

**Factory Pattern:**

```solidity
contract HookFactory {
    mapping(PoolId => address) public hooks;

    event HookCreated(PoolId indexed poolId, address hook);

    function createHookForPool(PoolKey memory poolKey)
        external
        returns (address)
    {
        PoolId poolId = poolKey.toId();
        require(hooks[poolId] == address(0), "Hook already exists");

        SinglePoolHook hook = new SinglePoolHook(poolKey);
        hooks[poolId] = address(hook);

        emit HookCreated(poolId, address(hook));
        return address(hook);
    }

    function getHook(PoolId poolId) external view returns (address) {
        return hooks[poolId];
    }
}
```

**Pros:**
- Gas efficient (no mapping lookups)
- Simple state management
- Clear ownership model

**Cons:**
- Requires deployment per pool
- Factory overhead
- More contracts to manage

---

### Strategy 3: Hybrid Approach with Access Control

**When to Use:**
- Some state is global, some is per-pool
- Need flexibility

**Implementation:**

```solidity
contract HybridHook is IHook {
    // Global state (intentionally shared)
    uint256 public globalFeePool;
    address public feeRecipient;

    // Pool-specific state
    mapping(PoolId => uint256) public poolLiquidity;
    mapping(PoolId => mapping(address => uint256)) public userShares;

    // Access control
    mapping(PoolId => bool) public authorizedPools;

    modifier onlyAuthorizedPool(PoolKey calldata key) {
        require(authorizedPools[key.toId()], "Pool not authorized");
        _;
    }

    function authorizePool(PoolKey calldata key) external onlyOwner {
        authorizedPools[key.toId()] = true;
    }

    function afterAddLiquidity(
        address sender,
        PoolKey calldata key,
        uint256 liquidity
    ) external override onlyAuthorizedPool(key) returns (bytes4) {
        PoolId poolId = key.toId();

        // ✅ Pool-scoped state
        poolLiquidity[poolId] += liquidity;
        userShares[poolId][sender] += liquidity;

        // ✅ Global state (intentional)
        uint256 fee = liquidity / 1000;
        globalFeePool += fee;

        return IHook.afterAddLiquidity.selector;
    }
}
```

**Pros:**
- Flexible for complex use cases
- Can share intentional global state
- Per-pool isolation where needed

**Cons:**
- More complex logic
- Requires careful design
- Higher audit surface

---

## Migration Guide

### Step 1: Audit Current State Variables

```solidity
// Identify all state variables
contract MyHook {
    uint256 public var1;  // ← Needs scoping?
    mapping(address => uint256) public var2;  // ← Needs scoping?
    address public constant ADMIN = ...;  // ← OK (constant)
}
```

**Decision Matrix:**

| Variable Type | Multi-Pool? | Action |
|--------------|------------|--------|
| Pool-specific accounting | Yes | Add `mapping(PoolId => ...)` |
| User balances per pool | Yes | Add `mapping(PoolId => mapping(address => ...))` |
| Global config/admin | No | Keep as-is (document intent) |
| Constants | No | Keep as-is |

### Step 2: Update State Variables

```solidity
// BEFORE
contract MyHook {
    uint256 public totalLiquidity;
    mapping(address => uint256) public userBalances;
}

// AFTER
contract MyHook {
    mapping(PoolId => uint256) public totalLiquidity;
    mapping(PoolId => mapping(address => uint256)) public userBalances;
}
```

### Step 3: Update Function Implementations

```solidity
// BEFORE
function updateLiquidity(address user, uint256 amount) internal {
    totalLiquidity += amount;
    userBalances[user] += amount;
}

// AFTER
function updateLiquidity(
    PoolId poolId,
    address user,
    uint256 amount
) internal {
    totalLiquidity[poolId] += amount;
    userBalances[poolId][user] += amount;
}
```

### Step 4: Update External/Hook Functions

```solidity
// BEFORE
function afterSwap(
    address sender,
    PoolKey calldata key,
    SwapParams calldata params
) external override {
    updateLiquidity(sender, params.amount);
}

// AFTER
function afterSwap(
    address sender,
    PoolKey calldata key,
    SwapParams calldata params
) external override {
    PoolId poolId = key.toId();
    updateLiquidity(poolId, sender, params.amount);
}
```

### Step 5: Add Getter Functions

```solidity
// Provide pool-scoped getters
function getLiquidity(PoolId poolId) external view returns (uint256) {
    return totalLiquidity[poolId];
}

function getUserBalance(PoolId poolId, address user)
    external
    view
    returns (uint256)
{
    return userBalances[poolId][user];
}

// Aggregate across pools if needed
function getTotalLiquidityAllPools() external view returns (uint256) {
    // Note: Requires tracking active pools
    uint256 total = 0;
    for (uint256 i = 0; i < activePools.length; i++) {
        total += totalLiquidity[activePools[i]];
    }
    return total;
}
```

---

## Testing & Validation

### Test 1: Multi-Pool State Isolation

```solidity
function testMultiPoolIsolation() public {
    MyHook hook = new MyHook();

    PoolKey memory poolA = createPool(tokenX, tokenY, hook);
    PoolKey memory poolB = createPool(tokenM, tokenN, hook);

    // Add liquidity to Pool A
    addLiquidity(poolA, alice, 1000 ether);

    // Add liquidity to Pool B
    addLiquidity(poolB, bob, 500 ether);

    // Assert isolation
    assertEq(
        hook.getLiquidity(poolA.toId()),
        1000 ether,
        "Pool A liquidity incorrect"
    );
    assertEq(
        hook.getLiquidity(poolB.toId()),
        500 ether,
        "Pool B liquidity incorrect"
    );
    assertEq(
        hook.getUserBalance(poolA.toId(), alice),
        1000 ether,
        "Alice balance in Pool A incorrect"
    );
    assertEq(
        hook.getUserBalance(poolB.toId(), alice),
        0,
        "Alice should have 0 in Pool B"
    );
}
```

### Test 2: Cross-Pool State Pollution

```solidity
function testNoStatePollution() public {
    MyHook hook = new MyHook();

    PoolKey memory poolA = createPool(tokenX, tokenY, hook);
    PoolKey memory poolB = createPool(tokenM, tokenN, hook);

    addLiquidity(poolA, alice, 1000 ether);
    uint256 poolAStateBefore = hook.getLiquidity(poolA.toId());

    // Operations on Pool B should NOT affect Pool A state
    addLiquidity(poolB, bob, 5000 ether);
    removeLiquidity(poolB, bob, 2000 ether);

    uint256 poolAStateAfter = hook.getLiquidity(poolA.toId());

    assertEq(
        poolAStateBefore,
        poolAStateAfter,
        "Pool A state was polluted by Pool B operations"
    );
}
```

### Test 3: Single-Pool Enforcement

```solidity
function testSinglePoolEnforcement() public {
    PoolKey memory poolA = createPool(tokenX, tokenY);
    SinglePoolHook hook = new SinglePoolHook(poolA);

    PoolKey memory poolB = createPool(tokenM, tokenN);

    // Should succeed for Pool A
    hook.afterSwap(alice, poolA, swapParams);

    // Should revert for Pool B
    vm.expectRevert("Unauthorized pool");
    hook.afterSwap(bob, poolB, swapParams);
}
```

---

## Documentation Requirements

### Code Comments

```solidity
/// @notice Multi-pool hook with isolated state per pool
/// @dev All state variables are scoped to PoolId to prevent cross-pool pollution
/// @custom:security-note This hook can be registered for multiple pools safely
contract SafeMultiPoolHook is IHook {
    /// @notice Total liquidity per pool
    /// @dev Keyed by PoolId to ensure isolation
    mapping(PoolId => uint256) public totalLiquidity;
}
```

### README Documentation

```markdown
## Multi-Pool Support

This hook is designed to support multiple pools safely. All state is scoped
to `PoolId` to prevent state collision across pools.

### Architecture
- **State Scoping:** All pool-specific state uses `mapping(PoolId => ...)`
- **Isolation Guarantee:** Operations on Pool A cannot affect Pool B state
- **Testing:** Verified with multi-pool integration tests

### Usage
```solidity
// Safe: Same hook for multiple pools
hook.register(poolA);
hook.register(poolB);
```

### Migration from Single-Pool
See `MIGRATION.md` for upgrading from single-pool hooks.
```

---

## Deployment Checklist

- [ ] All state variables reviewed for scoping needs
- [ ] Pool-specific state uses `mapping(PoolId => ...)`
- [ ] OR single-pool enforcement implemented
- [ ] Multi-pool test cases passing
- [ ] Cross-pool pollution tests passing
- [ ] Documentation updated
- [ ] Audit completed with multi-pool focus
- [ ] Gas benchmarks compared (before/after)
- [ ] Migration guide provided if upgrading existing hooks
