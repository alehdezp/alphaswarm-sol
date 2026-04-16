# Uniswap V4 Hooks Permission Detection

## Semantic Operations

```yaml
operations:
  - IMPLEMENTS_HOOK_INTERFACE
  - RECEIVES_CALLBACK
  - MODIFIES_POOL_STATE
  - CHECKS_CALLER
  - CALLS_EXTERNAL
```

## Behavioral Signature

```
CALLBACK_IN->NO_AUTH_CHECK->WRITES_STATE
```

## Detection Properties

```yaml
properties:
  implements_hooks_interface: true
  has_beforeSwap_callback: true
  has_afterSwap_callback: true
  has_beforeModifyPosition_callback: true
  restricts_pool_manager: false  # VULNERABLE
  has_access_modifier: false      # VULNERABLE
  allows_public_callback: true    # VULNERABLE
```

## Preconditions

- Hook implements lifecycle callbacks (before/after swap, modify liquidity)
- Hook stores state that affects pool behavior
- Callback functions lack caller validation
- Direct calls to hooks bypass PoolManager
- Hook controls user funds or pool parameters

## Detection Signals (Tier A - Deterministic)

### Pattern: Missing Access Control on Callbacks

```yaml
all:
  - property: implements_hooks_interface
    value: true
  - has_operation: RECEIVES_CALLBACK
  - has_operation: MODIFIES_POOL_STATE
none:
  - property: checks_caller_is_pool_manager
    value: true
  - property: has_only_pool_manager_modifier
    value: true
```

### Critical Functions

Hook lifecycle functions requiring access control:
- `beforeInitialize` / `afterInitialize`
- `beforeSwap` / `afterSwap`
- `beforeAddLiquidity` / `afterAddLiquidity`
- `beforeRemoveLiquidity` / `afterRemoveLiquidity`
- `beforeDonate` / `afterDonate`
- `unlockCallback` (if implemented)

### HookScan Detectors

```yaml
detectors:
  UniswapPublicHook:
    description: "Hook functions callable by anyone, not just PoolManager"
    severity: critical

  UniswapPublicCallback:
    description: "Callback functions not restricted to contract itself"
    severity: critical

  UniswapUpgradableHook:
    description: "Hook delegates to mutable addresses"
    severity: high

  UniswapSuicidalHook:
    description: "Hook contains SELFDESTRUCT"
    severity: critical
```

## LLM Reasoning Signals (Tier B)

Context questions for LLM analysis:

1. "Are hook lifecycle functions only callable by the PoolManager contract?"
2. "Does the hook store state that affects swap calculations or liquidity operations?"
3. "Can an attacker call hook functions directly to manipulate pool behavior?"
4. "Does the hook implement access control modifiers on all callbacks?"
5. "Are there any admin or privileged functions that bypass normal hook flow?"
6. "Can the hook be upgraded or does it delegate to external contracts?"

## Safe Properties

```yaml
safe_properties:
  has_only_pool_manager_modifier: true
  validates_caller_in_all_hooks: true
  uses_immutable_pool_manager: true
  no_public_state_modifiers: true
  no_delegatecall_to_mutable: false
```

## Safe Signature

```
CALLBACK_IN->CHECK:pool_manager->WRITES_STATE
```
