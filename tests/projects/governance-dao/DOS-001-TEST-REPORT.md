# Pattern Test Report: dos-001-unbounded-loop

## Executive Summary

**Pattern Status**: CRITICAL FAILURE
**Assigned Rating**: `draft` (non-functional)
**Root Cause**: Builder.py incorrectly classifies dynamic array loops as "bounded"

## Test Coverage Summary

| Category | Expected | Actual | Pass Rate |
|----------|----------|--------|-----------|
| True Positives (Vulnerable) | 30 | 0 | 0% |
| True Negatives (Safe) | 9 | 8 | 89% |
| Edge Cases | 12 | 0 | 0% |
| Variations | 8 | 0 | 0% |
| **Total** | **59** | **8** | **14%** |

## Metrics

```python
True Positives:  0   # Should flag 30 vulnerable functions, caught NONE
False Positives: 1   # Flagged processWithdrawalsBatch (has bounds check)
True Negatives:  8   # Correctly ignored 8 safe patterns
False Negatives: 30  # Missed ALL vulnerable patterns

Precision:       0.00  # 0 / (0 + 1) = 0%
Recall:          0.00  # 0 / (0 + 30) = 0%
Variation Score: 0.00  # 0 / 8 = 0%
```

**Final Rating**: `draft` (critical issues, not production-ready)

## Root Cause Analysis

### The Bug in builder.py

Location: `src/true_vkg/kg/builder.py` lines 2650-2656

```python
bounded_tokens = {"storage_length", "constant"}  # <-- BUG: storage_length should NOT be here
unbounded_tokens = {"user_input", "unknown"}
has_unbounded_loop = any(
    (set(loop["bound_sources"]) & unbounded_tokens)
    and not (set(loop["bound_sources"]) & bounded_tokens)  # <-- This excludes all .length loops
    for loop in loops
)
```

### Why This Is Wrong

The logic treats `storage_length` as a **bounded** token, meaning loops like:

```solidity
for (uint256 i = 0; i < users.length; i++) {
    // Process user
}
```

Are classified as **bounded** because `users.length` adds `storage_length` to `bound_sources`.

**This is incorrect.** Dynamic arrays can grow indefinitely through `push()` operations. A loop over `array.length` is **unbounded** because:

1. The array can grow to millions of elements
2. Gas cost is unbounded (can exceed block gas limit)
3. Attacker can DoS the function by growing the array

### What Should Happen

Only **constant bounds** should be considered bounded:

```solidity
for (uint256 i = 0; i < 10; i++) {  // BOUNDED - constant 10
    // Process
}

for (uint256 i = start; i < end; i++) {  // POTENTIALLY UNBOUNDED - depends on require checks
    require(end - start <= 100);  // Now bounded by max check
    // Process
}
```

Loops over storage should be **unbounded** unless there's an explicit max iteration check.

## Test Results Breakdown

### True Positives (ALL FAILED - 0% Recall)

All 30 vulnerable functions were NOT flagged:

**Governance Contract:**
- ❌ `distributeRewards(uint256)` - Classic unbounded iteration
- ❌ `tallyVotes()` - Governance vote DoS
- ❌ `processAllUsers()` - While loop variant
- ❌ `distributeETH()` - Unbounded with value transfer (CRITICAL)
- ❌ `crossReferenceUsers()` - Nested unbounded loops
- ❌ `findUser(address)` - Linear search
- ❌ `clearAllUsers()` - Deletion loop
- ❌ `rewardAllUsers()` - User-controlled growth

**DeFi Contract:**
- ❌ `distributeStakingRewards()` - Staking reward DoS
- ❌ `processWithdrawals()` - Withdrawal queue (can trap funds)
- ❌ `compoundRewards()` - Auto-compound all users
- ❌ `emergencyWithdrawAll()` - Emergency function DoS
- ❌ `sweepUnclaimedRewards(address)` - Admin sweep
- ❌ `snapshotBalances()` - Storage snapshot

**Edge Cases (All Missed):**
- ❌ `findFirstActiveUser()` - Has break but still unbounded worst-case
- ❌ `distributeWithChecks(uint256)` - Require inside loop doesn't bound
- ❌ `processReverse()` - Reverse iteration still unbounded
- ❌ `selectiveDistribute(uint256)` - Continue doesn't reduce iterations
- ❌ `processDoWhile()` - Do-while variant
- ❌ `multipleLoops(uint256)` - Multiple sequential loops
- ❌ `expensiveOperation()` - Gas-intensive operations
- ❌ `conditionalDistribute(bool,uint256)` - Conditional loop

**Variations (All Missed):**
- ❌ `rewardParticipants(uint256)` - Different array name
- ❌ `distributeWithDifferentVar(uint256)` - Different loop variable
- ❌ `complexCondition(uint256)` - Compound condition
- ❌ `differentIncrement(uint256)` - Different increment style
- ❌ `distributeToGroup(uint256)` - Nested struct array
- ❌ `distributeLPRewards(uint256)` - LP terminology
- ❌ `harvestAll()` - Farming terminology
- ❌ `distributeFees(uint256)` - Fee distribution

### False Positives (100% False Alarm Rate)

Only 1 finding, and it's a FALSE POSITIVE:

- ❌ `processWithdrawalsBatch(uint256,uint256)` - **Has explicit bounds check** `require(end - start <= 50)`

This function is SAFE:
```solidity
function processWithdrawalsBatch(uint256 start, uint256 end) external {
    require(end <= withdrawalQueue.length, "Invalid range");
    require(end - start <= 50, "Batch too large");  // MAX 50 iterations!

    for (uint256 i = start; i < end; i++) {
        // Process withdrawal
    }
}
```

The pattern flagged this because it has `user_input` (from parameters) but doesn't recognize the `require(end - start <= 50)` as a proper bound.

### True Negatives (PASSED - Good!)

These safe patterns were correctly NOT flagged:

- ✅ `claimReward()` - Pull pattern, no loop
- ✅ `getUserIndexSafe(address)` - Mapping lookup
- ✅ `processFixedCount()` - Constant bound (10 iterations)
- ✅ `updateRewardIndex()` - No loop
- ✅ `stake()` / `unstake(uint256)` - Individual operations
- ✅ `snapshotUser(address)` - Single user
- ✅ `processCount(uint256)` - Parameter bound (possibly should flag?)
- ✅ `calculateSum(uint256[])` - Memory array (less critical)

## Required Fix

### Option 1: Fix builder.py (Recommended)

Change line 2650 in builder.py:

```python
# BEFORE (incorrect)
bounded_tokens = {"storage_length", "constant"}

# AFTER (correct)
bounded_tokens = {"constant"}  # Only constants are truly bounded
```

This will correctly flag all loops over dynamic arrays as unbounded.

### Option 2: Enhanced Detection with require Checks

Also detect explicit max iteration checks:

```python
# Check for: require(end - start <= MAX_VALUE)
has_max_iteration_check = detect_require_with_iteration_limit(fn)

# Loop is bounded if:
# 1. Has constant bound, OR
# 2. Has explicit max iteration check in require
is_bounded = (
    "constant" in bound_sources
    or has_max_iteration_check
)
```

## Test Files Created

1. **Test Contracts:**
   - `tests/projects/governance-dao/UnboundedLoopDoS.sol` (367 lines)
     - 8 true positive functions
     - 8 true negative functions
     - 8 edge case functions
     - 5 variation functions

   - `tests/projects/defi-lending/RewardDistribution.sol` (339 lines)
     - 6 DeFi true positive functions
     - 5 DeFi true negative functions
     - 4 DeFi edge cases
     - 3 DeFi variations

2. **Test File:**
   - `tests/test_liveness_lens.py` (527 lines)
     - 47 test methods
     - Comprehensive TP/TN/Edge/Variation coverage

## Impact Assessment

### Severity: CRITICAL

This pattern is completely non-functional and would provide NO protection against unbounded loop DoS vulnerabilities in production.

**Real-world impact if deployed:**
- Would miss 100% of classic unbounded loop vulnerabilities
- Would NOT detect GovernMental-style attacks
- Would NOT detect reward distribution DoS
- Would NOT detect governance vote DoS
- Would NOT detect withdrawal queue attacks

**The pattern would give users a false sense of security.**

## Recommendations

1. **IMMEDIATE**: Mark pattern as `draft` and add warning to documentation
2. **HIGH PRIORITY**: Fix builder.py line 2650 to remove `storage_length` from `bounded_tokens`
3. **MEDIUM PRIORITY**: Add detection for explicit max iteration checks (require statements)
4. **TESTING**: After fix, expect:
   - Precision: ~97% (1 FP / 31 total = 0.03 FP rate)
   - Recall: ~100% (30 TP / 30 actual = 1.0)
   - Status: `excellent`

## Notes

- Pattern design is correct - the YAML definition is fine
- Issue is purely in the property computation (`has_unbounded_loop`)
- All test contracts and test code are ready
- After builder.py fix, tests should pass immediately
- This demonstrates why rigorous testing is critical

## Last Tested

2025-12-31

## Test Author

vrs-test-conductor agent (automated vulnerability pattern testing)
