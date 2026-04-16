# Uniswap V4 Hooks Permission Patterns

## Vulnerable Pattern: Missing PoolManager Check

### Code Structure (Semantic)

```solidity
// VULNERABLE: Hook callback without access control
contract VulnerableHook {
    // State that affects pool behavior
    mapping(PoolId => address) public poolToToken;

    // MISSING: onlyPoolManager modifier
    function beforeInitialize(
        address,
        PoolKey calldata key,
        uint160,
        bytes calldata
    ) external returns (bytes4) {
        // Anyone can call this! Should only be PoolManager
        poolToToken[key.toId()] = address(new ERC20());
        return IHooks.beforeInitialize.selector;
    }
}
```

**Operations**: `RECEIVES_CALLBACK` → `NO_AUTH_CHECK` → `WRITES_STATE`

**Signature**: `CALLBACK:public->W:state`

**Why Vulnerable**:
- Hook lifecycle function lacks caller validation
- Any address can invoke callback directly
- State modifications bypass intended PoolManager flow
- Can lock user funds or manipulate pool parameters

## Vulnerable Pattern: Missing Callback Access Control

### Code Structure (Semantic)

```solidity
// VULNERABLE: Callback without caller restriction
contract VulnerableAsyncHook {
    // MISSING: caller validation
    function unlockCallback(bytes calldata data) external returns (bytes memory) {
        // Should only be callable by this contract during unlock
        // Missing: require(msg.sender == address(this))

        (address user, uint amount) = abi.decode(data, (address, uint));
        TRANSFERS_FUNDS(user, amount);

        return "";
    }
}
```

**Operations**: `RECEIVES_CALLBACK` → `DECODES_DATA` → `TRANSFERS_FUNDS`

**Why Vulnerable**:
- Callback meant for internal use is publicly callable
- Attacker can craft malicious calldata
- Direct fund transfer without validation
- Bypass intended hook logic flow

## Safe Pattern: PoolManager-Only Modifier

### Code Structure (Semantic)

```solidity
// SAFE: Explicit PoolManager access control
contract SafeHook {
    IPoolManager public immutable poolManager;

    constructor(IPoolManager _poolManager) {
        poolManager = _poolManager;
    }

    modifier onlyPoolManager() {
        require(msg.sender == address(poolManager), "Not PoolManager");
        _;
    }

    function beforeSwap(
        address,
        PoolKey calldata key,
        IPoolManager.SwapParams calldata,
        bytes calldata
    ) external onlyPoolManager returns (bytes4, BeforeSwapDelta, uint24) {
        // Only PoolManager can call this
        PERFORMS_HOOK_LOGIC();

        return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }
}
```

**Operations**: `RECEIVES_CALLBACK` → `CHECK:pool_manager` → `PERFORMS_HOOK_LOGIC`

**Signature**: `CALLBACK->AUTH:pool_manager->LOGIC`

**Safe Properties**:
- Immutable PoolManager address
- Explicit modifier on all hook callbacks
- Clear access control pattern
- Cannot bypass via direct calls

## Safe Pattern: Self-Only Callback

### Code Structure (Semantic)

```solidity
// SAFE: Callback restricted to contract itself
contract SafeAsyncHook is BaseHook {
    modifier onlySelf() {
        require(msg.sender == address(this), "Not self");
        _;
    }

    function unlockCallback(bytes calldata data) external onlySelf returns (bytes memory) {
        // Only callable during internal unlock flow
        PERFORMS_INTERNAL_LOGIC(data);
        return "";
    }

    function beforeSwap(...) external onlyPoolManager returns (...) {
        // Trigger internal unlock
        poolManager.unlock(abi.encode(data));
        return ...;
    }
}
```

**Safe Properties**:
- Callback only callable by contract itself
- Prevents external invocation
- Maintains intended call flow
- Clear separation of internal/external functions

## Safe Pattern: BaseHook Inheritance

### Code Structure (Semantic)

```solidity
// SAFE: Using BaseHook from v4-periphery
import {BaseHook} from "v4-periphery/BaseHook.sol";

contract SafeInheritedHook is BaseHook {
    constructor(IPoolManager _poolManager) BaseHook(_poolManager) {}

    // BaseHook provides onlyPoolManager modifier automatically
    function beforeSwap(
        address sender,
        PoolKey calldata key,
        IPoolManager.SwapParams calldata,
        bytes calldata
    ) internal override returns (bytes4, BeforeSwapDelta, uint24) {
        // Internal function - BaseHook handles access control
        PERFORMS_HOOK_LOGIC();

        return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }
}
```

**Safe Properties**:
- BaseHook provides built-in access control
- Hook functions are internal (not external)
- BaseHook wrapper handles PoolManager validation
- Follows Uniswap V4 best practices

## Vulnerable Pattern: Upgradeable Hook

### Code Structure (Semantic)

```solidity
// VULNERABLE: Delegatecall to mutable implementation
contract UpgradeableHook {
    address public implementation;  // Mutable!

    function setImplementation(address newImpl) external onlyOwner {
        implementation = newImpl;  // Can be changed
    }

    fallback() external {
        // Delegates to potentially malicious implementation
        address impl = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}
```

**Why Vulnerable**:
- Implementation can be swapped for malicious contract
- No timelock or governance delay
- Users have no warning of upgrade
- Can drain funds post-deployment
