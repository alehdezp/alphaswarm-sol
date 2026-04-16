# Code Patterns: State Isolation Vulnerabilities

## Vulnerable Patterns

### Pattern 1: Unscoped Hook State

```solidity
// VULNERABLE: Multi-pool hook with shared state
abstract contract VulnerableHook is IHook {
    // ❌ State shared across ALL pools
    uint256 public totalLiquidity;
    mapping(address => uint256) public userBalances;
    uint256 public lastUpdateTime;

    function afterAddLiquidity(
        address sender,
        PoolKey calldata key,
        uint256 liquidity
    ) external override {
        // State pollution: affects all pools using this hook
        totalLiquidity += liquidity;
        userBalances[sender] += liquidity;
        lastUpdateTime = block.timestamp;
    }

    function beforeRemoveLiquidity(
        address sender,
        PoolKey calldata key,
        uint256 liquidity
    ) external override {
        // VULNERABILITY: Uses global state
        // If hook registered for Pool A and Pool B:
        // - Adding liquidity to Pool A increases totalLiquidity
        // - Removing from Pool B uses wrong totalLiquidity value
        require(liquidity <= totalLiquidity, "Insufficient liquidity");
        totalLiquidity -= liquidity;
        userBalances[sender] -= liquidity;
    }
}
```

**Behavioral Signature:**
```
OPERATION: REGISTERS_HOOK(pool_A)
OPERATION: REGISTERS_HOOK(pool_B)
OPERATION: WRITES_STATE(totalLiquidity) via pool_A
OPERATION: READS_STATE(totalLiquidity) via pool_B
RESULT: State collision, pool_B sees pool_A's state
```

### Pattern 2: Singleton with Instance-Agnostic Storage

```solidity
// VULNERABLE: Vault manager with unscoped accounting
contract VaultManager {
    // ❌ No vault-specific scoping
    uint256 public totalDeposits;
    uint256 public totalShares;
    mapping(address => uint256) public userShares;

    function deposit(address vault, uint256 amount) external {
        // VULNERABILITY: State updates affect ALL vaults
        totalDeposits += amount;

        uint256 shares = calculateShares(amount);
        totalShares += shares;
        userShares[msg.sender] += shares;

        // Even though 'vault' parameter exists, state is global!
    }

    function withdraw(address vault, uint256 shares) external {
        // VULNERABILITY: Uses global state for per-vault operations
        require(shares <= userShares[msg.sender], "Insufficient shares");

        uint256 amount = (shares * totalDeposits) / totalShares;
        userShares[msg.sender] -= shares;
        totalShares -= shares;
        totalDeposits -= amount;

        // Attacker can deposit to Vault A, withdraw from Vault B
        // using inflated totalDeposits from Vault A
    }
}
```

**Behavioral Signature:**
```
OPERATION: WRITES_STATE(totalDeposits, no_vault_key)
OPERATION: READS_STATE(totalDeposits, no_vault_key) for different vault
SIGNATURE: W:state(global)->R:state(global, wrong_context)->EXPLOIT
```

### Pattern 3: Missing Pool ID in Callback State

```solidity
// VULNERABLE: AMM hook with callback state
contract SwapHook is IHook {
    // ❌ Callback state not scoped to pool
    struct CallbackData {
        address tokenIn;
        address tokenOut;
        uint256 amountIn;
        bool inProgress;
    }

    CallbackData private _currentSwap;

    function beforeSwap(
        address sender,
        PoolKey calldata key,
        SwapParams calldata params
    ) external override {
        // VULNERABILITY: If two pools call this simultaneously
        // (different transactions in same block), state collision
        require(!_currentSwap.inProgress, "Swap in progress");

        _currentSwap = CallbackData({
            tokenIn: key.currency0,
            tokenOut: key.currency1,
            amountIn: params.amountIn,
            inProgress: true
        });
    }

    function afterSwap(
        address sender,
        PoolKey calldata key,
        SwapParams calldata params
    ) external override {
        // Uses _currentSwap without verifying it's for THIS pool
        // Pool A can corrupt Pool B's callback state
        processCallback(_currentSwap);
        delete _currentSwap;
    }
}
```

**Behavioral Signature:**
```
OPERATION: SETS_CALLBACK_STATE(pool_A, no_pool_id)
OPERATION: SETS_CALLBACK_STATE(pool_B, no_pool_id) ← Overwrites pool_A
OPERATION: PROCESSES_CALLBACK(pool_A, wrong_state)
SIGNATURE: W:callback(A)->W:callback(B)->R:callback(A, data_from_B)
```

## Safe Patterns

### Pattern 1: Pool-Scoped Hook State

```solidity
// SAFE: Multi-pool hook with isolated state
abstract contract SafeHook is IHook {
    // ✅ State scoped to pool ID
    mapping(PoolId => uint256) public totalLiquidity;
    mapping(PoolId => mapping(address => uint256)) public userBalances;
    mapping(PoolId => uint256) public lastUpdateTime;

    function afterAddLiquidity(
        address sender,
        PoolKey calldata key,
        uint256 liquidity
    ) external override {
        PoolId poolId = key.toId();  // Get unique pool identifier

        // State updates isolated to specific pool
        totalLiquidity[poolId] += liquidity;
        userBalances[poolId][sender] += liquidity;
        lastUpdateTime[poolId] = block.timestamp;
    }

    function beforeRemoveLiquidity(
        address sender,
        PoolKey calldata key,
        uint256 liquidity
    ) external override {
        PoolId poolId = key.toId();

        // Uses correct pool-specific state
        require(
            liquidity <= totalLiquidity[poolId],
            "Insufficient liquidity"
        );
        totalLiquidity[poolId] -= liquidity;
        userBalances[poolId][sender] -= liquidity;
    }
}
```

**Behavioral Signature:**
```
OPERATION: WRITES_STATE[pool_id](value)
OPERATION: READS_STATE[pool_id](value)
SIGNATURE: W:state[pool_A]->R:state[pool_A] ✅ Isolated
```

### Pattern 2: Enforced Single-Instance Deployment

```solidity
// SAFE: Hook enforces single-pool usage
contract SinglePoolHook is IHook {
    // ✅ Immutable pool binding
    PoolId public immutable POOL_ID;
    IPoolManager public immutable POOL_MANAGER;

    // State can be unscoped since only one pool uses this hook
    uint256 public totalLiquidity;
    mapping(address => uint256) public userBalances;

    constructor(PoolKey memory poolKey, IPoolManager poolManager) {
        POOL_ID = poolKey.toId();
        POOL_MANAGER = poolManager;
    }

    modifier onlyPool(PoolKey calldata key) {
        require(key.toId() == POOL_ID, "Wrong pool");
        _;
    }

    function afterAddLiquidity(
        address sender,
        PoolKey calldata key,
        uint256 liquidity
    ) external override onlyPool(key) {
        // Safe: Only one pool can call this
        totalLiquidity += liquidity;
        userBalances[sender] += liquidity;
    }
}
```

**Behavioral Signature:**
```
OPERATION: CHECKS_POOL_ID(key.toId() == POOL_ID)
OPERATION: WRITES_STATE(value) if check passes
SIGNATURE: CHECK(pool_id)->W:state ✅ Single-instance enforced
```

### Pattern 3: Explicit Multi-Instance Support with Factory

```solidity
// SAFE: Factory creates isolated hook instances
contract HookFactory {
    mapping(PoolId => address) public poolHooks;

    function createHook(PoolKey memory poolKey) external returns (address) {
        PoolId poolId = poolKey.toId();

        // ✅ One hook instance PER pool
        require(poolHooks[poolId] == address(0), "Hook exists");

        SinglePoolHook hook = new SinglePoolHook(poolKey, poolManager);
        poolHooks[poolId] = address(hook);

        return address(hook);
    }
}

// Each pool gets its own hook instance with isolated state
```

**Behavioral Signature:**
```
OPERATION: CREATES_INSTANCE(pool_id)
OPERATION: MAPS_INSTANCE[pool_id](hook_address)
SIGNATURE: DEPLOY(pool_A)->hook_A, DEPLOY(pool_B)->hook_B ✅ Isolated
```

### Pattern 4: Pool-Scoped Callback State

```solidity
// SAFE: Callback state includes pool identifier
contract SafeSwapHook is IHook {
    struct CallbackData {
        PoolId poolId;  // ✅ Include pool ID
        address tokenIn;
        address tokenOut;
        uint256 amountIn;
    }

    // ✅ Map callback state to pool
    mapping(PoolId => CallbackData) private _swapCallbacks;

    function beforeSwap(
        address sender,
        PoolKey calldata key,
        SwapParams calldata params
    ) external override {
        PoolId poolId = key.toId();

        require(
            _swapCallbacks[poolId].amountIn == 0,
            "Swap in progress for this pool"
        );

        _swapCallbacks[poolId] = CallbackData({
            poolId: poolId,
            tokenIn: key.currency0,
            tokenOut: key.currency1,
            amountIn: params.amountIn
        });
    }

    function afterSwap(
        address sender,
        PoolKey calldata key,
        SwapParams calldata params
    ) external override {
        PoolId poolId = key.toId();

        // Uses correct pool-specific callback state
        CallbackData memory data = _swapCallbacks[poolId];
        require(data.poolId == poolId, "Invalid callback state");

        processCallback(data);
        delete _swapCallbacks[poolId];
    }
}
```

**Behavioral Signature:**
```
OPERATION: SETS_CALLBACK[pool_id](data)
OPERATION: GETS_CALLBACK[pool_id](data)
SIGNATURE: W:callback[pool_A]->R:callback[pool_A] ✅ Isolated
```

## Detection Summary

| Pattern Type | Vulnerable | Safe | Detection Property |
|--------------|-----------|------|-------------------|
| Hook State | Unscoped variables | `mapping(PoolId => ...)` | `missing_instance_identifier` |
| Singleton | Global state for multi-instance | Enforced single-instance | `singleton_without_instance_checks` |
| Callback | No pool ID in state | Pool-scoped callbacks | `callback_state_not_scoped` |
| Factory | N/A | One instance per pool | `factory_enforces_isolation` |

## Testing Strategy

### Test Case: Multi-Pool State Collision

```solidity
function testStateCollision() public {
    // Deploy hook
    MyHook hook = new MyHook();

    // Create two pools with same hook
    PoolKey memory poolA = createPool(tokenX, tokenY, hook);
    PoolKey memory poolB = createPool(tokenA, tokenB, hook);

    // Interact with Pool A
    interactWithPool(poolA, 1000);
    uint256 stateA = hook.getState();

    // Interact with Pool B
    interactWithPool(poolB, 500);
    uint256 stateB = hook.getState();

    // VULNERABLE: stateA should still be 1000, but may be overwritten
    // SAFE: stateA = hook.getState(poolA.toId()) == 1000
    //       stateB = hook.getState(poolB.toId()) == 500
}
```
