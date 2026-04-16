# Detection: State Isolation Vulnerabilities

## Identification Signals

### Tier A: Deterministic Properties

**Core Signal:**
```yaml
all:
  - property: uses_multi_instance_pattern
    value: true
  - property: has_shared_state_variables
    value: true
  - property: missing_instance_identifier_in_storage
    value: true
```

**Secondary Signals:**
- `implements_hook_interface: true` (Uniswap V4, similar protocols)
- `singleton_contract: true`
- `state_variables_not_scoped_to_instance: true`
- `supports_multiple_pools: true` (implicit or explicit)

### Tier B: LLM Reasoning Context

**Business Logic Questions:**
1. Is this contract/hook intended to be used with multiple pools/instances?
2. Are state variables explicitly scoped to pool/instance IDs?
3. Does the contract assume single-pool usage despite multi-pool capability?
4. Is there documentation stating "one hook per pool" or similar?
5. Can the same hook address be registered for multiple pools?

**Risk Indicators:**
- Base contract designed for inheritance without enforced single-instance deployment
- State variables use simple storage (not mappings keyed by pool ID)
- Documentation ambiguity on multi-pool support
- No explicit checks preventing multi-pool registration

## Behavioral Signatures

### Vulnerable Pattern
```
REGISTERS_HOOK(pool_1) → SETS_STATE(var_X) →
REGISTERS_HOOK(pool_2) → SETS_STATE(var_X) →
STATE(var_X, pool_1) = OVERWRITTEN
```

**Operation Sequence:**
```
R:pool_id → W:state(no_key) → R:pool_id_2 → W:state(no_key) → COLLISION
```

### Safe Pattern
```
REGISTERS_HOOK(pool_1) → SETS_STATE(pool_1 => var_X) →
REGISTERS_HOOK(pool_2) → SETS_STATE(pool_2 => var_Y) →
STATE(var_X, pool_1) = ISOLATED
```

**Operation Sequence:**
```
R:pool_id → W:state[pool_id] → R:pool_id_2 → W:state[pool_id_2] → ISOLATED
```

## Check Patterns

### Manual Code Review Checks

1. **State Variable Scoping:**
   ```solidity
   // VULNERABLE: Shared state across pools
   contract BaseHook {
       uint256 public totalAmount;  // ❌ No pool isolation

       function updateAmount(uint256 amount) external {
           totalAmount += amount;  // State collision risk
       }
   }

   // SAFE: Pool-scoped state
   contract BaseHook {
       mapping(address => uint256) public totalAmount;  // ✅ Pool-isolated

       function updateAmount(address poolId, uint256 amount) external {
           totalAmount[poolId] += amount;  // No collision
       }
   }
   ```

2. **Hook Registration:**
   ```solidity
   // Check: Can same hook be registered for multiple pools?
   // If yes, verify state isolation
   ```

3. **Storage Layout:**
   ```solidity
   // Verify: Are all state variables either:
   // - Scoped to pool/instance ID in mapping key
   // - OR contract enforces single-pool deployment
   ```

### Automated Detection

**Slither Detector Candidate:**
```python
def detect_missing_state_isolation(contract):
    if not is_multi_instance_capable(contract):
        return []

    violations = []
    for var in contract.state_variables:
        if not is_scoped_to_instance(var):
            violations.append({
                'variable': var.name,
                'issue': 'Missing instance/pool scoping',
                'severity': 'CRITICAL'
            })
    return violations
```

**VKG Properties:**
```yaml
uses_multi_instance_pattern:
  description: "Contract designed for use with multiple instances/pools"
  detection: "Check for hook interface, multiple pool registration capability"

has_shared_state_variables:
  description: "State variables shared across all instances"
  detection: "State variables not in mapping keyed by instance ID"

missing_instance_identifier_in_storage:
  description: "Storage keys missing pool/instance identifier"
  detection: "Non-constant state vars without pool ID in mapping key"
```

## Detection Confidence

| Scenario | Confidence | Rationale |
|----------|-----------|-----------|
| Hook with shared state + multi-pool support | **95%** | Clear violation |
| Singleton with state vars + no pool scoping | **85%** | High likelihood |
| Base contract + inheritance + no instance checks | **75%** | Needs context |
| Documentation states "single pool only" | **60%** | Implementation may differ |

## False Positive Scenarios

1. **Intentional Global State:**
   - Hook legitimately aggregates data across all pools
   - Mitigation: Document intent, ensure no per-pool accounting needed

2. **Single-Pool Enforced:**
   - Contract enforces single-pool deployment in factory/registry
   - Mitigation: Add explicit checks or documentation

3. **Stateless Hooks:**
   - Hook has no state variables or only constants
   - Mitigation: No risk if truly stateless

## Integration with VKG

### Graph Representation

```yaml
node:
  type: Function
  name: "updatePoolState"
  properties:
    uses_multi_instance_pattern: true
    has_shared_state_variables: true
    missing_instance_identifier_in_storage: true
    writes_state: true

edges:
  - from: "updatePoolState"
    to: "totalAmount"
    type: "WRITES_STATE"
    properties:
      scoped_to_instance: false  # ❌ Collision risk
```

### Cross-Function Analysis

Detect if:
1. Hook registered for Pool A
2. Hook registered for Pool B (same address)
3. State writes from Pool A operations affect Pool B state

**Detection Algorithm:**
```python
for hook in hooks:
    pools = get_registered_pools(hook)
    if len(pools) > 1:
        state_vars = get_state_variables(hook)
        for var in state_vars:
            if not is_scoped_to_pool(var):
                flag_vulnerability(hook, var, pools)
```
