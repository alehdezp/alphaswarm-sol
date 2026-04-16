# Reentrancy Gauntlet Report

**Suite ID:** gauntlet-reentrancy
**Version:** 1.0.0
**Date:** 2026-01-31
**Status:** TEMPLATE (awaiting execution)

---

## Summary

| Metric | Value |
|--------|-------|
| Total Cases | 10 |
| Vulnerable | 5 |
| Safe | 5 |
| Pass Threshold | 100% (10/10) |
| Required Gates | G0, G1, G2, G4 |

---

## Results

| Case ID | Contract | Expected | Actual | Result |
|---------|----------|----------|--------|--------|
| RE-VULN-001 | Vault_01.sol | VULNERABLE | - | PENDING |
| RE-SAFE-001 | Vault_02.sol | SAFE | - | PENDING |
| RE-VULN-002 | Vault_03.sol | VULNERABLE | - | PENDING |
| RE-SAFE-002 | Vault_04.sol | SAFE | - | PENDING |
| RE-VULN-003 | Vault_05.sol | VULNERABLE | - | PENDING |
| RE-SAFE-003 | Vault_06.sol | SAFE | - | PENDING |
| RE-VULN-004 | Vault_07.sol | VULNERABLE | - | PENDING |
| RE-SAFE-004 | Vault_08.sol | SAFE | - | PENDING |
| RE-VULN-005 | Vault_09.sol | VULNERABLE | - | PENDING |
| RE-SAFE-005 | Vault_10.sol | SAFE | - | PENDING |

---

## Scoring

| Metric | Count | Points |
|--------|-------|--------|
| True Positives (TP) | - | +1 each |
| True Negatives (TN) | - | +1 each |
| False Positives (FP) | - | -2 each |
| False Negatives (FN) | - | -2 each |
| **Total Score** | - | / 10 |

**Scoring Formula:**
```
Score = (TP * +1) + (TN * +1) + (FP * -2) + (FN * -2)
```

**Pass Criteria:**
- Score = 10 (all correct)
- FP = 0 (no false alarms)
- FN = 0 (no missed vulnerabilities)

---

## Vulnerability Types Tested

### VULNERABLE Cases (5)

1. **RE-VULN-001: Classic CEI Violation**
   - Contract: Vault_01.sol
   - Pattern: External call before state update
   - Detection signal: `TRANSFERS_VALUE_OUT` before `WRITES_USER_BALANCE`

2. **RE-VULN-002: Guard on Wrong Function**
   - Contract: Vault_03.sol
   - Pattern: Reentrancy guard only on deposit, not withdraw
   - Detection signal: Partial guard coverage

3. **RE-VULN-003: Cross-Function Reentrancy**
   - Contract: Vault_05.sol
   - Pattern: Re-entry via transfer() during withdraw()
   - Detection signal: Shared state across functions with external call

4. **RE-VULN-004: Read-Only Reentrancy**
   - Contract: Vault_07.sol
   - Pattern: View function returns stale data during callback
   - Detection signal: View function reads state pending update

5. **RE-VULN-005: Callback Reentrancy**
   - Contract: Vault_09.sol
   - Pattern: Flash loan callback before state finalization
   - Detection signal: External callback invocation mid-operation

### SAFE Cases (5)

1. **RE-SAFE-001: ReentrancyGuard**
   - Contract: Vault_02.sol
   - Protection: OpenZeppelin-style nonReentrant modifier
   - False positive trap: Still has external call after state

2. **RE-SAFE-002: Pull Pattern**
   - Contract: Vault_04.sol
   - Protection: Two-step withdrawal (initiate + claim)
   - False positive trap: Has external call in claim()

3. **RE-SAFE-003: CEI Pattern**
   - Contract: Vault_06.sol
   - Protection: Checks-Effects-Interactions ordering
   - False positive trap: Has external call and value transfer

4. **RE-SAFE-004: Mutex Lock**
   - Contract: Vault_08.sol
   - Protection: Custom mutex (locked variable)
   - False positive trap: Not standard OpenZeppelin pattern

5. **RE-SAFE-005: No External Calls**
   - Contract: Vault_10.sol
   - Protection: Pure internal accounting
   - False positive trap: Writes balances, has public functions

---

## False Positive Analysis

| Case | Trap Description | Risk Level |
|------|------------------|------------|
| RE-SAFE-001 | Guard present but external call after state | Medium |
| RE-SAFE-002 | External call in claim() function | Low |
| RE-SAFE-003 | Has external call + value transfer | High |
| RE-SAFE-004 | Custom pattern, not standard library | Medium |
| RE-SAFE-005 | Writes state, has public interface | Low |

---

## False Negative Analysis

| Case | Detection Challenge | Risk Level |
|------|---------------------|------------|
| RE-VULN-002 | Guard exists but on wrong function | High |
| RE-VULN-003 | Cross-function requires call graph analysis | High |
| RE-VULN-004 | Read-only reentrancy, no direct exploit | Medium |
| RE-VULN-005 | Callback pattern, indirect reentrancy | Medium |

---

## Gate Status

| Gate | Status | Notes |
|------|--------|-------|
| G0 (Preflight) | PENDING | Environment validation |
| G1 (Evidence) | PENDING | Proof tokens required |
| G2 (Graph) | PENDING | BSKG must be valid |
| G4 (Mutation) | PENDING | Detection threshold |

---

## Remediation Hints

### For False Positives

If the system incorrectly flags a SAFE contract:

1. **Check guard detection**: Verify ReentrancyGuard/mutex patterns are recognized
2. **Check CEI detection**: Verify state-write-before-call ordering is detected
3. **Check pull pattern**: Verify two-step withdrawal is recognized
4. **Reduce sensitivity**: Adjust pattern thresholds

### For False Negatives

If the system misses a VULNERABLE contract:

1. **Add cross-function analysis**: Track state dependencies across functions
2. **Add callback detection**: Identify external callback invocations
3. **Add read-only detection**: Track view functions reading pending updates
4. **Improve guard scope**: Check if guard covers all entry points

---

## Run History

| Run ID | Date | TP | TN | FP | FN | Score | Result |
|--------|------|----|----|----|----|-------|--------|
| - | - | - | - | - | - | - | PENDING |

---

## References

- **Manifest:** tests/gauntlet/reentrancy_manifest.yaml
- **Runner:** scripts/e2e/run_gauntlet_reentrancy.sh
- **Scoring:** configs/gauntlet_scoring.yaml
- **Spec:** .planning/phases/07.3.3-adversarial-gauntlet/07.3.3-GAUNTLET-SPEC.md
- **Contracts:** tests/gauntlet/reentrancy/Vault_*.sol

---

## Execution Instructions

```bash
# Dry run (list cases)
./scripts/e2e/run_gauntlet_reentrancy.sh --dry-run

# Full execution
./scripts/e2e/run_gauntlet_reentrancy.sh --verbose

# With custom output
./scripts/e2e/run_gauntlet_reentrancy.sh --output .vrs/gauntlet/custom
```

After execution, update this report with actual results from:
- `.vrs/gauntlet/reentrancy/{run_id}/final_results.yaml`
- `.vrs/gauntlet/reentrancy/{run_id}/evidence/pack.yaml`
