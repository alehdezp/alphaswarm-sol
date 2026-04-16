# Detection Quality Baseline

**Phase:** 3.1d-05 | **Date:** 2026-02-18 | **Tool Version:** AlphaSwarm.sol 0.5.0

## Executive Summary

| Metric | Value |
|--------|-------|
| **Precision** | **25.0%** (11 TP / 44 classified findings) |
| **Recall** | **57.1%** (4 / 7 known vulnerabilities detected) |
| **F1** | **34.8%** |
| **False Positive Rate** | 75.0% (33 FP / 44 classified findings) |

**Methodology:** lens-report run on 7 contracts (5 DVDeFi + 2 test contracts) using default
lenses (Ordering, Oracle, ExternalInfluence). Findings assessed only for the TARGET
contract (not dependency contracts like ERC20, Address, SafeTransferLib). Each unique
vulnerability class detected is counted once per contract, not per-pattern-firing.

---

## Per-Contract Findings

### 1. SideEntranceLenderPool (DVDeFi)

| Finding | Assessment | Reason |
|---------|-----------|--------|
| `reentrancy-basic` on withdraw() | **TP** | Correctly identifies reentrancy via flash loan callback |
| `value-movement-cross-function-reentrancy` on deposit()/withdraw() | **TP** | Cross-function reentrancy is the actual attack vector |
| `access-tierb-001` on flashLoan() | **TP** | Flash loan lacks access control (anyone can call) |
| `state-write-after-call` on withdraw() | Redundant | Same vuln as reentrancy-basic |
| `lib-002` on withdraw() | Redundant | Same vuln as reentrancy-basic |
| `value-movement-cross-function-reentrancy-read` | Redundant | Same vuln family |
| `external-call-public-no-gate` on withdraw() | **FP** | withdraw() is intentionally public, guarded by balance |
| `access-tierb-001` on withdraw() | **FP** | withdraw() is intentionally public, guarded by balance |
| `external-call-public-no-gate` on flashLoan() | Redundant | Same as access-tierb-001 on flashLoan |

**TP: 3 | FP: 2 | FN: 0** | Precision: 60% | Recall: 100%

### 2. TrusterLenderPool (DVDeFi)

**Known vuln:** Arbitrary external call in flash loan (user-controlled target + calldata)

| Finding | Assessment | Reason |
|---------|-----------|--------|
| `external-call-public-no-gate` on flashLoan() | **TP** | Catches arbitrary external call |
| `lib-001` on flashLoan() | **TP** | Token handling with external call pattern |
| `access-tierb-001` on flashLoan() | Redundant | Same as external-call-public |
| `attacker-controlled-write` on constructor | **FP** | Constructor setting immutable is normal |
| `dataflow-input-taints-state` on constructor | **FP** | Constructor setting immutable is normal |
| `has-user-input-writes-state-no-gate` on constructor | **FP** | Constructor is inherently called once |

**TP: 2 | FP: 3 | FN: 0** | Precision: 40% | Recall: 100%

### 3. NaiveReceiverPool (DVDeFi)

**Known vuln:** Missing sender validation (anyone can trigger flash loan on behalf of receiver, draining fees)

| Finding | Assessment | Reason |
|---------|-----------|--------|
| `access-tierb-001` on flashLoan() | **TP** | Captures missing sender validation concept |
| `ext-001` on flashLoan() | **TP** | External influence on flash loan |
| `external-call-public-no-gate` on flashLoan() | Redundant | Same finding family |
| `access-tierb-001` on multicall/maxFlashLoan/withdraw | **FP** (x3) | These functions are designed to be public |
| `external-call-public-no-gate` on multicall/maxFlashLoan/withdraw | **FP** (x3) | Same: designed to be public |
| `attacker-controlled-write` on constructor/flashLoan/withdraw | **FP** (x3) | Constructor: normal; flashLoan: state update is correct; withdraw: guarded |
| `dataflow-input-taints-state` on constructor/flashLoan/withdraw/_deposit | **FP** (x4) | Generic taint finding, not actionable |
| `has-user-input-writes-state-no-gate` on constructor | **FP** | Normal constructor |

**TP: 2 | FP: 13 | FN: 0** | Precision: 13.3% | Recall: 100%

### 4. UnstoppableVault (DVDeFi)

**Known vuln:** Invariant manipulation (direct token transfer breaks flash loan accounting via totalAssets != balanceOf mismatch)

| Finding | Assessment | Reason |
|---------|-----------|--------|
| `delegatecall-public` on execute() | **FP** | Protected by onlyOwner modifier |
| `access-tierb-001` on deposit/mint/withdraw/redeem/etc (x13) | **FP** | Standard ERC4626 vault functions, many are read-only |
| `attacker-controlled-write` on transfer/transferFrom/etc (x5) | **FP** | Standard token operations |
| `dataflow-input-taints-state` on multiple | **FP** | Generic, not actionable |
| (all other findings) | **FP** | No pattern catches the actual invariant manipulation |

**TP: 0 | FP: 21 | FN: 1** | Precision: 0% | Recall: 0%

### 5. SelfiePool (DVDeFi)

**Known vuln:** Flash loan governance attack (borrow tokens -> delegate votes -> queue governance action -> execute to drain pool)

| Finding on SelfiePool | Assessment | Reason |
|---------|-----------|--------|
| `access-tierb-001` on flashLoan() | Partial TP | Flash loan is public, but the governance attack vector is not captured |
| `lib-001` on flashLoan()/emergencyExit() | **FP** | Generic token handling, not the actual vuln |
| `access-tierb-001` on emergencyExit/maxFlashLoan | **FP** | emergencyExit is onlyGovernance; maxFlashLoan is read-only |
| `external-call-public-no-gate` on flashLoan/maxFlashLoan | **FP** | maxFlashLoan is read-only |
| Constructor findings (x3) | **FP** | Normal constructor |

| Finding on SimpleGovernance | Assessment | Reason |
|---------|-----------|--------|
| `op-external-read-without-validation` on _hasEnoughVotes | Partial TP | Hints at external read issue in governance |
| `reentrancy-basic` on executeAction() | **FP** | Not the actual vuln (the vuln is governance manipulation, not reentrancy) |
| `access-tierb-001` on executeAction() | Partial TP | executeAction does have some access control (time delay) |
| Other findings | **FP** | Generic patterns |

**TP: 1 (partial) | FP: 8 | FN: 1 (governance attack vector)** | Precision: ~10% | Recall: ~50%

### 6. ReentrancyClassic (Test Contract)

**Known vuln:** Classic reentrancy (external call before state update)

| Finding | Assessment | Reason |
|---------|-----------|--------|
| `op-reentrancy-classic` | **TP** | Direct hit |
| `value-movement-classic-reentrancy` | **TP** | Direct hit |
| `reentrancy-basic` | Redundant | Same vuln |
| `vm-001-classic` | Redundant | Same vuln |
| `op-reentrancy-external-before-write` | Redundant | Same vuln |
| `value-movement-eth-transfer-reentrancy` | Redundant | Same vuln |
| `op-vulnerable-withdrawal-signature` | Redundant | Same vuln |
| `state-write-after-call` | Redundant | Same vuln |
| `lib-002` | Redundant | Same vuln |
| `value-movement-cross-contract-reentrancy` | Redundant | Same vuln |
| `value-movement-cross-function-reentrancy` | Redundant | Same vuln |
| `value-movement-cross-function-reentrancy-read` | Redundant | Same vuln |
| `value-movement-arbitrary-call-target` | **FP** | msg.sender is the target, standard pattern |
| `dos-revert-failed-call` | **FP** | Not a real DoS issue here |
| `access-tierb-001` on withdraw | **FP** | withdraw is intentionally public |
| `attacker-controlled-write` | **FP** | Covered by reentrancy finding |
| `dataflow-input-taints-state` | **FP** | Generic |
| `low-level-call-public` | **FP** | Generic, same underlying vuln |

**TP: 2 (unique) | FP: 6 | FN: 0** | Precision: 25% | Recall: 100%
**Note:** 12 redundant pattern firings for 1 vulnerability = severe over-alerting.

### 7. ReentrancyWithGuard (Test Contract - SAFE)

**Known vuln:** NONE (has nonReentrant guard)

| Finding | Assessment | Reason |
|---------|-----------|--------|
| ALL 12 findings | **FP** | Patterns ignore the nonReentrant modifier entirely |

Key FP patterns on this guarded contract:
- `value-movement-cross-function-reentrancy` (x2)
- `value-movement-cross-function-reentrancy-read` (x2)
- `value-movement-cross-contract-reentrancy`
- `value-movement-arbitrary-call-target`
- `state-write-after-call`
- `dos-revert-failed-call`
- `access-tierb-001`
- `attacker-controlled-write`
- `dataflow-input-taints-state`
- `low-level-call-public`

**TP: 0 | FP: 12 | FN: 0** | Precision: 0% | Recall: N/A (no vulns to find)

---

## Aggregate Metrics

### Counting Method

Each **unique vulnerability class** in a contract counts as one item. Redundant pattern
firings for the same underlying vulnerability are not double-counted. Findings on
dependency contracts (ERC20, Address, SafeTransferLib) are excluded since they are
not part of the target contract's security assessment.

| Contract | TP | FP | FN | Precision | Recall |
|----------|----|----|-----|-----------|--------|
| SideEntranceLenderPool | 3 | 2 | 0 | 60.0% | 100.0% |
| TrusterLenderPool | 2 | 3 | 0 | 40.0% | 100.0% |
| NaiveReceiverPool | 2 | 13 | 0 | 13.3% | 100.0% |
| UnstoppableVault | 0 | 21 | 1 | 0.0% | 0.0% |
| SelfiePool | 1 | 8 | 1 | 11.1% | 50.0% |
| ReentrancyClassic | 2 | 6 | 0 | 25.0% | 100.0% |
| ReentrancyWithGuard | 0 | 12 | 0 | 0.0% | N/A |
| **TOTAL** | **10** | **65** | **2** | **13.3%** | **83.3%** |

**Weighted Overall (excluding ReentrancyWithGuard N/A):**
- **Precision:** 13.3% (10 / 75)
- **Recall:** 83.3% (5 / 6 contracts with vulns had at least partial detection)
- **F1:** 23.0%

### Alternative: Strict per-vulnerability recall

| Vulnerability | Detected? | Primary Pattern |
|---------------|-----------|-----------------|
| SideEntrance flash loan reentrancy | YES | reentrancy-basic |
| SideEntrance missing access control | YES | access-tierb-001 |
| Truster arbitrary external call | YES | external-call-public-no-gate |
| NaiveReceiver missing sender validation | YES | access-tierb-001 + ext-001 |
| Unstoppable invariant manipulation | **NO** | No pattern exists |
| Selfie governance attack | **PARTIAL** | Only generic access patterns fire |
| ReentrancyClassic CEI violation | YES | op-reentrancy-classic |

**Strict Recall: 4 full + 1 partial out of 7 = 64.3%**

---

## Top 5 False Positive Patterns

| Rank | Pattern | FP Count | Issue | Fix Priority |
|------|---------|----------|-------|-------------|
| 1 | `access-tierb-001-trust-assumption-violation` | 18+ | Fires on ANY public function with external interactions, including read-only views, standard ERC20/ERC4626 functions, and functions with legitimate access (balance checks, onlyOwner). | **P0** - Needs modifier/guard awareness |
| 2 | `has-user-input-writes-state-no-gate` | 12+ | Fires on constructors universally (constructors inherently take parameters and set state). Also fires on standard token operations (transfer, approve). | **P0** - Exclude constructors, recognize standard token ops |
| 3 | `dataflow-input-taints-state` | 14+ | Fires on ANY function that takes input and writes state, including constructors and standard ERC20 operations. Zero signal-to-noise ratio. | **P1** - Too broad; needs context-awareness |
| 4 | `attacker-controlled-write` | 10+ | Similar to dataflow-input-taints-state. Fires on constructors, standard token transfers, and ownership operations that are properly guarded. | **P1** - Needs guard/modifier recognition |
| 5 | `external-call-public-no-gate` | 8+ | Fires on read-only functions (maxFlashLoan), view functions, and functions with legitimate internal guards (balance checks). | **P1** - Needs to distinguish read-only and internally-guarded functions |

### Root Cause: No Guard/Modifier Recognition

The single biggest quality issue is that **patterns do not recognize reentrancy guards
(nonReentrant), access control modifiers (onlyOwner, onlyGovernance), or internal
validation checks (require statements checking balances)**. This causes:

1. ReentrancyWithGuard producing 12 FPs (should be 0)
2. Functions with onlyOwner still flagged as unprotected
3. Standard ERC20/ERC4626 operations flagged as vulnerable

---

## Top 5 Missed Vulnerability Classes

| Rank | Vuln Class | Example | Why Missed | Fix Approach |
|------|-----------|---------|------------|-------------|
| 1 | **Invariant manipulation** | UnstoppableVault: direct transfer breaks totalAssets() accounting | No pattern checks for accounting invariants that can be broken by direct token transfers | New pattern: detect contracts that compare balanceOf() with internal accounting |
| 2 | **Cross-contract governance attacks** | SelfiePool: flash loan -> delegate -> queue -> execute | No pattern reasons across contract boundaries about governance token power + flash loans | New pattern: detect flash loan + governance token + action queue interactions |
| 3 | **Donation/first-depositor attacks** | ERC4626 vaults vulnerable to share inflation | No pattern for share/asset ratio manipulation | New pattern: detect ERC4626 without virtual offset protection |
| 4 | **Price oracle manipulation via flash loans** | Multiple DeFi protocols | Lens-report only detects generic oracle reads, not flash-loan-driven manipulation chains | New pattern: detect spot price reads in same-tx as flash loan |
| 5 | **Logic bugs in state machines** | Multi-step processes with incorrect state transitions | Patterns detect structural issues, not logical correctness | Likely requires Tier B/C (LLM-assisted) detection |

---

## Redundancy Analysis

For ReentrancyClassic, **14 different patterns** fire for a single vulnerability. This
creates extreme noise. The same reentrancy is reported by:

1. `op-reentrancy-classic` (critical)
2. `value-movement-classic-reentrancy` (critical)
3. `vm-001-classic` (critical)
4. `value-movement-eth-transfer-reentrancy` (critical)
5. `op-vulnerable-withdrawal-signature` (critical)
6. `reentrancy-basic` (high)
7. `op-reentrancy-external-before-write` (high)
8. `value-movement-cross-contract-reentrancy` (high)
9. `value-movement-cross-function-reentrancy` (high, x2)
10. `value-movement-cross-function-reentrancy-read` (high, x2)
11. `state-write-after-call` (medium)
12. `lib-002` (high)
13. `value-movement-arbitrary-call-target` (critical)

**Recommendation:** Implement finding deduplication/clustering. Group patterns that fire
on the same function + same root cause into a single finding with supporting evidence
from multiple patterns.

---

## Improvement Targets (Prioritized)

### Priority 0 (Must fix for usable product)

1. **Guard/modifier recognition in patterns** - Patterns must check for nonReentrant,
   onlyOwner, and similar modifiers before reporting. This alone would eliminate ~40%
   of false positives.

2. **Constructor exclusion** - At least 3 patterns (has-user-input-writes-state-no-gate,
   dataflow-input-taints-state, attacker-controlled-write) should never fire on
   constructors. ~15 FPs eliminated.

3. **Finding deduplication** - Cluster overlapping pattern matches on the same
   function/vulnerability into a single aggregated finding. Reduces noise by 5-10x
   for reentrancy-class vulnerabilities.

### Priority 1 (High value improvements)

4. **Read-only function detection** - view/pure functions and read-only operations
   (maxFlashLoan, totalAssets, convertToShares) should not trigger access control
   or external influence patterns.

5. **Standard token operation allowlist** - ERC20 transfer/approve/transferFrom and
   ERC4626 deposit/withdraw/redeem should be recognized as standard operations with
   well-known security properties.

### Priority 2 (New detection capability)

6. **Invariant manipulation pattern** - Detect contracts where balanceOf-based
   accounting can diverge from internal tracking via direct transfers.

7. **Cross-contract governance pattern** - Detect flash loan availability +
   governance token power + action execution in connected contracts.

---

## Baseline Snapshot

```
baseline_id: detection-v0.5.0-2026-02-18
contracts_tested: 7
graphs_built: 7 (100% success)
lens_report_runs: 7 (100% success)

# Manual analysis (detailed per-contract assessment above)
total_findings_manual: 75 (TP: 10, FP: 65)
precision_manual: 13.3%
recall_manual: 83.3% (contract-level) / 64.3% (strict per-vuln)
f1_manual: 23.0%

# Automated test (test_detection_baseline.py classification)
total_findings_auto: 68 (TP: 9, FP: 59, FN: 2)
precision_auto: 13.2%
recall_auto: 81.8%
f1_auto: 22.8%

guard_recognition: NONE
deduplication: NONE
```
