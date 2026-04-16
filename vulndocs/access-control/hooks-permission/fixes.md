# Uniswap V4 Hooks Permission Fixes

## Remediation Approaches

### 1. Use BaseHook Inheritance (High Effectiveness - RECOMMENDED)

**Fix**: Inherit from Uniswap's BaseHook contract.

```solidity
import {BaseHook} from "v4-periphery/src/utils/BaseHook.sol";

contract SecureHook is BaseHook {
    constructor(IPoolManager _poolManager) BaseHook(_poolManager) {}

    // Override internal functions - BaseHook handles access control
    function _beforeSwap(
        address sender,
        PoolKey calldata key,
        IPoolManager.SwapParams calldata params,
        bytes calldata hookData
    ) internal override returns (bytes4, BeforeSwapDelta, uint24) {
        // Your hook logic here
        // No need to check msg.sender - BaseHook does it

        return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }
}
```

**Safe Operations**: `INHERITS:BaseHook` → `OVERRIDE:internal` → `AUTO_ACCESS_CONTROL`

**Why Effective**:
- BaseHook provides onlyPoolManager modifier automatically
- Hook implementations are internal (cannot be called externally)
- Follows official Uniswap V4 patterns
- Tested and audited by Uniswap team

### 2. Explicit PoolManager Validation (High Effectiveness)

**Fix**: Implement onlyPoolManager modifier on all hook callbacks.

```solidity
contract SecureHook {
    IPoolManager public immutable poolManager;

    constructor(IPoolManager _poolManager) {
        poolManager = _poolManager;
    }

    modifier onlyPoolManager() {
        require(msg.sender == address(poolManager), "Only PoolManager");
        _;
    }

    // Apply to ALL hook lifecycle functions
    function beforeSwap(...) external onlyPoolManager returns (...) {
        // Hook logic
    }

    function afterSwap(...) external onlyPoolManager returns (...) {
        // Hook logic
    }

    function beforeAddLiquidity(...) external onlyPoolManager returns (...) {
        // Hook logic
    }

    // ... all other hook functions
}
```

**Checklist**:
- [ ] onlyPoolManager on beforeInitialize
- [ ] onlyPoolManager on afterInitialize
- [ ] onlyPoolManager on beforeSwap
- [ ] onlyPoolManager on afterSwap
- [ ] onlyPoolManager on beforeAddLiquidity
- [ ] onlyPoolManager on afterAddLiquidity
- [ ] onlyPoolManager on beforeRemoveLiquidity
- [ ] onlyPoolManager on afterRemoveLiquidity
- [ ] onlyPoolManager on beforeDonate
- [ ] onlyPoolManager on afterDonate

### 3. Self-Only Callback Restriction (Medium Effectiveness)

**Fix**: Restrict callback functions to contract itself.

```solidity
contract SecureAsyncHook is BaseHook {
    modifier onlySelf() {
        require(msg.sender == address(this), "Only self");
        _;
    }

    function unlockCallback(bytes calldata data) external onlySelf returns (bytes memory) {
        // Only callable during poolManager.unlock() from this contract
        (address user, uint amount) = abi.decode(data, (address, uint));

        // Perform internal operations
        _handleUnlock(user, amount);

        return "";
    }

    function beforeSwap(...) external onlyPoolManager returns (...) {
        // Trigger unlock which will call unlockCallback internally
        bytes memory result = poolManager.unlock(abi.encode(user, amount));
        return ...;
    }
}
```

**Safe Properties**:
- Callback cannot be invoked externally
- Maintains intended call flow
- Prevents calldata manipulation attacks

### 4. Immutable Hook Dependencies (High Effectiveness)

**Fix**: Make critical addresses immutable.

```solidity
contract SecureHook {
    // IMMUTABLE - cannot be changed after deployment
    IPoolManager public immutable poolManager;
    address public immutable owner;

    constructor(IPoolManager _poolManager, address _owner) {
        poolManager = _poolManager;
        owner = _owner;
    }

    // No functions to change poolManager or owner
    // Prevents rug pull via address modification
}
```

**Safe Properties**:
- PoolManager address cannot be changed
- Prevents attack via address swap
- Clear security guarantees

### 5. Avoid Upgradeable Patterns (Critical)

**Fix**: Do NOT use upgradeable hooks unless absolutely necessary.

**If upgrades required**:
```solidity
// Use timelock and transparent governance
contract UpgradeableHook {
    address public implementation;
    address public pendingImplementation;
    uint public upgradeTimestamp;
    uint constant UPGRADE_DELAY = 7 days;

    function proposeUpgrade(address newImpl) external onlyGovernance {
        pendingImplementation = newImpl;
        upgradeTimestamp = block.timestamp + UPGRADE_DELAY;
        emit UpgradeProposed(newImpl, upgradeTimestamp);
    }

    function executeUpgrade() external {
        require(block.timestamp >= upgradeTimestamp, "Too early");
        require(pendingImplementation != address(0), "No pending upgrade");

        implementation = pendingImplementation;
        pendingImplementation = address(0);
        emit UpgradeExecuted(implementation);
    }

    // ... delegatecall logic
}
```

**Safe Properties**:
- 7-day delay gives users time to exit
- Transparent governance process
- Clear upgrade timeline
- Users can monitor pending changes

**Better Alternative**: Don't use upgradeable hooks at all.

### 6. Use HookScan for Validation (Medium Effectiveness)

**Fix**: Run automated static analysis before deployment.

```bash
# Install HookScan
git clone https://github.com/blocksecteam/hookscan

# Scan your hook contract
hookscan analyze MyHook.sol

# Check for:
# - UniswapPublicHook (public hook functions)
# - UniswapPublicCallback (public callbacks)
# - UniswapUpgradableHook (mutable delegates)
# - UniswapSuicidalHook (selfdestruct)
```

**Detectors**:
- UniswapPublicHook: Critical
- UniswapPublicCallback: Critical
- UniswapUpgradableHook: High
- UniswapSuicidalHook: Critical

## Security Checklist

**Before Deployment**:
- [ ] All hook callbacks have onlyPoolManager modifier OR inherit BaseHook
- [ ] No public functions that modify hook state
- [ ] PoolManager address is immutable
- [ ] Callback functions restricted to contract itself (if used)
- [ ] No upgradeable pattern OR timelock with 7+ day delay
- [ ] No selfdestruct in hook code
- [ ] HookScan analysis passed
- [ ] Unit tests verify access control on all hooks
- [ ] Fuzzing performed on hook state modifications

**During Integration**:
- [ ] Hook permissions match intended behavior (via hook address flags)
- [ ] Pool creation uses correct hook address encoding
- [ ] Users understand hook behavior and risks
- [ ] Emergency pause mechanism (if needed) is secure

**Post-Deployment Monitoring**:
- [ ] Monitor for unexpected direct calls to hook
- [ ] Track hook state changes via events
- [ ] Alert on suspicious patterns
- [ ] Regular security reviews as Uniswap V4 evolves
