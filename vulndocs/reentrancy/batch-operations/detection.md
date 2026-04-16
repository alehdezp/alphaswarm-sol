# Detection: Batch Operation Reentrancy

**Subcategory**: reentrancy/batch-operations
**Severity**: Critical
**Pattern ID**: vm-015 (to be created)
**Discovered**: 2026-01-09 via Penpie Hack ($27M)

---

## Overview

Batch operation reentrancy occurs when a function processes multiple items in a loop, making external calls to untrusted contracts, and updates state after each iteration. While a single operation may be safe, the batch processing amplifies reentrancy risk by allowing attackers to:
1. Register malicious contracts as "valid" through factory checks
2. Reenter during external calls within the loop
3. Manipulate state during batch processing before guards are applied

**Key Distinction**: Unlike classic reentrancy where the vulnerable function itself is re-entered, batch reentrancy exploits the loop amplification where state changes accumulate before validation.

---

## Graph Signals

| Property | Expected | Critical? | Description |
|----------|----------|-----------|-------------|
| `external_calls_in_loop` | `true` | YES | Function makes external calls inside loop |
| `has_reentrancy_guard` | `false` | YES | No reentrancy protection on batch function |
| `writes_user_balance` | `true` | YES | Updates user balance or accounting |
| `calls_untrusted` | `true` | YES | Calls contracts not hardcoded/verified |
| `has_validation_after_external_call` | `false` | NO | No post-call state validation |
| `visibility` | `["public", "external"]` | YES | Externally callable |
| `loop_has_bounds_check` | `false` | NO | Unbounded or attacker-controlled loop |

---

## Operation Sequences

### VULNERABLE Pattern
```
R:bal → FOR(items) { X:untrusted(item) → W:bal } → END
```

**Behavioral Signature**: `R:bal→X:untrusted(loop)→W:bal`

**Attack Flow**:
1. Function reads initial balance/state
2. Loop iterates over attacker-controlled or mixed items
3. Each iteration calls external contract (e.g., `redeemRewards()`)
4. Malicious contract reenters batch function or manipulates state
5. State writes occur during inconsistent state
6. Accumulated effect drains funds

### SAFE Pattern
```
R:bal → FOR(items) { validate(item) } → W:bal → FOR(items) { X:trusted(item) }
```

**Safety Mechanisms**:
- Validate all items BEFORE external calls
- Apply reentrancy guard to batch function
- Use checks-effects-interactions per iteration
- Write state before external calls
- Only call trusted/verified contracts

---

## Real-World Exploit: Penpie Hack

**Date**: September 3, 2024
**Loss**: $27M USD
**Source**: [SolidityScan Analysis](https://blog.solidityscan.com/penpie-hack-analysis-29034a6f2a61)

**Vulnerability**:
```solidity
// VULNERABLE: _harvestBatchMarketRewards
function _harvestBatchMarketRewards(address[] calldata markets) external {
    for (uint i = 0; i < markets.length; i++) {
        address market = markets[i];
        // MISSING: reentrancy guard
        // UNSAFE: calls untrusted contract
        IMarket(market).redeemRewards(); // Attacker reenters here

        // State update happens AFTER external call
        rewards[msg.sender] += calculateRewards(market);
    }
}
```

**Attack Steps**:
1. Attacker created counterfeit SY token contract
2. Registered malicious contract via `PendleMarketFactoryV3` (passed factory validation)
3. Called `_harvestBatchMarketRewards` with mix of legit + malicious markets
4. Malicious market's `redeemRewards()` reentered batch function
5. Inflated rewards through repeated calls during loop
6. Drained $27M in tokens

**Root Cause**:
- No reentrancy guard on batch function
- Relied on factory validation instead of behavioral guards
- State updates occurred after external calls in loop

---

## False Positive Indicators

These conditions suggest the pattern is SAFE:

1. **Reentrancy Guard Present**:
   ```solidity
   modifier nonReentrant() { ... }
   function batchProcess() external nonReentrant { ... }
   ```

2. **Checks-Effects-Interactions Per Iteration**:
   ```solidity
   for (uint i = 0; i < items.length; i++) {
       // Update state BEFORE external call
       balances[user] -= amounts[i];
       items[i].transfer(user, amounts[i]);
   }
   ```

3. **Trusted Contracts Only**:
   ```solidity
   // Hardcoded trusted addresses
   for (uint i = 0; i < trustedContracts.length; i++) {
       trustedContracts[i].call(...);
   }
   ```

4. **Two-Phase Processing**:
   ```solidity
   // Phase 1: State changes
   for (...) { balances[user] -= amount; }
   // Phase 2: External calls
   for (...) { token.transfer(user, amount); }
   ```

5. **Per-Iteration State Consistency**:
   ```solidity
   for (...) {
       uint before = balance;
       external.call();
       require(balance >= before, "inconsistent state");
   }
   ```

---

## Detection Checklist

- [ ] Function has loop that iterates over external calls?
- [ ] External calls are to untrusted/user-provided contracts?
- [ ] State writes occur after external calls within loop?
- [ ] No `nonReentrant` modifier on function?
- [ ] No per-iteration state validation?
- [ ] Loop bounds are attacker-controlled or unbounded?
- [ ] Function is publicly callable?
- [ ] Affects user balances or critical accounting?

**If 5+ checks are YES** → HIGH CONFIDENCE vulnerable to batch reentrancy

---

## Recommended Fixes

### Fix 1: Apply Reentrancy Guard (Best)
```solidity
function batchProcess(address[] calldata items) external nonReentrant {
    for (uint i = 0; i < items.length; i++) {
        items[i].call(...);
    }
}
```

### Fix 2: Checks-Effects-Interactions Per Iteration
```solidity
function batchProcess(address[] calldata items) external {
    for (uint i = 0; i < items.length; i++) {
        // Effects FIRST
        balance -= amounts[i];
        // Interactions AFTER
        items[i].call(...);
    }
}
```

### Fix 3: Two-Phase Processing
```solidity
function batchProcess(address[] calldata items) external {
    // Phase 1: All state changes
    for (uint i = 0; i < items.length; i++) {
        validateAndUpdateState(items[i]);
    }
    // Phase 2: All external calls
    for (uint i = 0; i < items.length; i++) {
        items[i].call(...);
    }
}
```

### Fix 4: Whitelist + Trust Validation
```solidity
mapping(address => bool) public trustedContracts;

function batchProcess(address[] calldata items) external {
    for (uint i = 0; i < items.length; i++) {
        require(trustedContracts[items[i]], "untrusted");
        items[i].call(...);
    }
}
```

---

## Related Vulnerabilities

- **Classic Reentrancy** (vm-001): Single-function reentrancy
- **Cross-Function Reentrancy** (vm-005): Reentrancy across multiple functions
- **Read-Only Reentrancy** (vm-010): View functions during inconsistent state
- **External Calls in Loop** (dos-005): DoS via gas exhaustion

---

## BSKG Properties Used

### Primary Detection
- `external_calls_in_loop = true`
- `has_reentrancy_guard = false`
- `writes_user_balance = true`

### Supporting Signals
- `calls_untrusted = true`
- `visibility in [public, external]`
- `state_write_after_external_call = true`

### Operations
- `TRANSFERS_VALUE_OUT`
- `READS_USER_BALANCE`
- `WRITES_USER_BALANCE`
- `CALLS_UNTRUSTED`

---

## Testing Guidance

Create test contracts with:
1. **True Positive**: Batch function with loop + untrusted calls + no guard
2. **True Negative**: Batch function with reentrancy guard
3. **Edge Case**: Mixed trusted/untrusted calls in loop
4. **Variation**: Two-phase processing (state then calls)

Example test:
```python
def test_batch_reentrancy_detection():
    graph = load_graph("BatchReentrancyVulnerable")
    func = graph.get_function("batchHarvestRewards")
    assert func.external_calls_in_loop == True
    assert func.has_reentrancy_guard == False
    assert func.writes_user_balance == True
```

---

**Last Updated**: 2026-01-09
**Status**: Documented, pattern creation pending
