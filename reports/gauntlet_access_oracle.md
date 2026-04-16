# Access Control & Oracle Gauntlet Report

**Suite ID:** `gauntlet-access-oracle`
**Version:** 1.0.0
**Date:** 2026-01-31
**Status:** READY FOR EXECUTION

---

## Overview

The Access Control & Oracle Gauntlet tests AlphaSwarm.sol's ability to detect:
- Access control vulnerabilities (missing auth, delegatecall, ownership)
- Oracle manipulation vulnerabilities (staleness, decimals, single source, L2 sequencer)
- Cross-contract reasoning (inherited protection, decimal propagation)

This gauntlet uses **binary scoring** with a 2x penalty for false positives and false negatives.

---

## Test Cases Summary

| Case ID | Contract | Expected | Vulnerability Type | Status |
|---------|----------|----------|-------------------|--------|
| AC-VULN-001 | AccessVault_01.sol | VULNERABLE | Missing auth on upgrade | pending |
| AC-VULN-002 | AccessVault_02.sol | VULNERABLE | Delegatecall target control | pending |
| AC-VULN-003 | AccessVault_03.sol | VULNERABLE | Ownership manipulation | pending |
| AC-SAFE-001 | AccessVault_04.sol | SAFE | OpenZeppelin Ownable2Step | pending |
| OR-VULN-001 | OracleVault_01.sol | VULNERABLE | Oracle staleness | pending |
| OR-VULN-002 | OracleVault_02.sol | VULNERABLE | Decimal mismatch | pending |
| OR-VULN-003 | OracleVault_03.sol | VULNERABLE | Single oracle source | pending |
| OR-VULN-004 | OracleVault_04.sol | VULNERABLE | L2 sequencer grace | pending |
| OR-SAFE-001 | OracleVault_05.sol | SAFE | Proper oracle validation | pending |
| OR-SAFE-002 | OracleVault_06.sol | SAFE | Multi-oracle aggregation | pending |

---

## Scoring Rules

| Classification | Points |
|----------------|--------|
| True Positive (correctly identified vulnerable) | +1 |
| True Negative (correctly identified safe) | +1 |
| False Positive (flagged safe as vulnerable) | -2 |
| False Negative (missed vulnerability) | -2 |

**Pass Threshold:** 10/10 correct (100% accuracy, 0 FP, 0 FN)

---

## Vulnerability Details

### Access Control Vulnerabilities

#### AC-VULN-001: Missing Auth on Upgrade
**Contract:** `AccessVault_01.sol`
**Severity:** Critical
**Pattern:** `access-control-missing`, `upgrade-unprotected`

**Description:**
The `upgradeTo()` function in a UUPS proxy lacks the `onlyOwner` modifier. Any external caller can invoke `upgradeTo()` and point the proxy to a malicious implementation, taking complete control of the contract.

**Detection Signals:**
- `upgrade_function_public`
- `no_access_control_on_critical`
- `modifies_implementation_slot`

**Remediation:**
```solidity
function _authorizeUpgrade(address newImplementation) internal override onlyOwner {
    // Only owner can authorize upgrades
}
```

---

#### AC-VULN-002: Delegatecall Target Control
**Contract:** `AccessVault_02.sol`
**Severity:** Critical
**Pattern:** `delegatecall-untrusted`

**Description:**
The `execute()` function accepts a user-controlled address and performs `delegatecall` to it. An attacker can pass a malicious contract that executes arbitrary code in the context of the vault, potentially draining all funds.

**Detection Signals:**
- `delegatecall_with_user_input`
- `no_target_validation`
- `has_value_storage`

**Remediation:**
```solidity
mapping(address => bool) public allowedTargets;

function execute(address target, bytes calldata data) external onlyOwner returns (bytes memory) {
    require(allowedTargets[target], "Target not whitelisted");
    (bool success, bytes memory result) = target.delegatecall(data);
    require(success, "Delegatecall failed");
    return result;
}
```

---

#### AC-VULN-003: Ownership Manipulation
**Contract:** `AccessVault_03.sol`
**Severity:** High
**Pattern:** `ownership-single-step`

**Description:**
`transferOwnership()` is a single-step operation without confirmation from the new owner. This is vulnerable to front-running attacks and typos in the new owner address.

**Detection Signals:**
- `public_ownership_transfer`
- `no_two_step_transfer`
- `single_owner_model`

**Remediation:**
Use OpenZeppelin's `Ownable2Step` pattern:
```solidity
import "@openzeppelin/contracts/access/Ownable2Step.sol";
// transferOwnership sets pendingOwner
// acceptOwnership must be called by new owner
```

---

### Oracle Vulnerabilities

#### OR-VULN-001: Oracle Staleness
**Contract:** `OracleVault_01.sol`
**Severity:** High
**Pattern:** `oracle-staleness`

**Description:**
Chainlink price feed is used without checking the `updatedAt` timestamp. During oracle downtime or network congestion, stale prices can be exploited for arbitrage.

**Detection Signals:**
- `chainlink_price_feed`
- `no_staleness_check`
- `price_used_in_calculation`

**Remediation:**
```solidity
(, int256 answer, , uint256 updatedAt, ) = priceFeed.latestRoundData();
require(updatedAt >= block.timestamp - STALENESS_THRESHOLD, "Stale price");
```

---

#### OR-VULN-002: Decimal Mismatch
**Contract:** `OracleVault_02.sol`
**Severity:** Critical
**Pattern:** `oracle-decimal-mismatch`

**Description:**
Contract assumes 18 decimals but Chainlink returns 8 decimals. This 10^10 difference causes massive over/under-valuation of assets.

**Detection Signals:**
- `hardcoded_decimal_assumption`
- `no_decimals_call`
- `price_calculation_mismatch`

**Remediation:**
```solidity
uint8 decimals = priceFeed.decimals();
uint256 normalizedPrice = uint256(answer);
if (decimals < 18) {
    normalizedPrice = normalizedPrice * (10 ** (18 - decimals));
}
```

---

#### OR-VULN-003: Single Oracle Source
**Contract:** `OracleVault_03.sol`
**Severity:** Medium
**Pattern:** `oracle-single-source`

**Description:**
Single Chainlink feed with no fallback. If the oracle is compromised, deprecated, or returns anomalous data, the entire protocol is at risk.

**Detection Signals:**
- `single_price_source`
- `no_fallback_oracle`
- `no_circuit_breaker`

**Remediation:**
```solidity
(uint256 primaryPrice, bool primaryValid) = getOraclePrice(primaryOracle);
(uint256 fallbackPrice, bool fallbackValid) = getOraclePrice(fallbackOracle);
require(primaryValid || fallbackValid, "All oracles failed");
```

---

#### OR-VULN-004: L2 Sequencer Grace Period
**Contract:** `OracleVault_04.sol`
**Severity:** High
**Pattern:** `oracle-l2-sequencer`

**Description:**
On L2 networks (Arbitrum, Optimism), missing sequencer uptime feed check. After sequencer comes back online, stale prices persist during a grace period, allowing arbitrage attacks.

**Detection Signals:**
- `l2_deployment_detected`
- `no_sequencer_uptime_check`
- `no_grace_period_handling`

**Remediation:**
```solidity
(, int256 answer, uint256 startedAt, , ) = sequencerUptimeFeed.latestRoundData();
bool isSequencerUp = answer == 0;
require(isSequencerUp, "Sequencer is down");
uint256 timeSinceUp = block.timestamp - startedAt;
require(timeSinceUp > GRACE_PERIOD_TIME, "Grace period not over");
```

---

## Safe Cases (Negative Controls)

### AC-SAFE-001: OpenZeppelin Ownable2Step
**Contract:** `AccessVault_04.sol`
**Pattern:** Proper access control with inheritance

The contract correctly inherits from `Ownable2StepUpgradeable`:
- Two-step ownership transfer prevents accidents
- `onlyOwner` modifier on all critical functions
- Upgrade authorization properly protected

**False Positive Trap:** Has upgrade function (but protected via inherited modifier)

---

### OR-SAFE-001: Proper Oracle Validation
**Contract:** `OracleVault_05.sol`
**Pattern:** Complete oracle safety checks

Implements all recommended safety checks:
- Staleness check with timestamp validation
- Round completeness check (`answeredInRound >= roundId`)
- Proper decimal normalization via `decimals()` call
- Circuit breaker for anomalous price deviations

**False Positive Trap:** Uses Chainlink oracle (but with proper validation)

---

### OR-SAFE-002: Multi-Oracle Aggregation
**Contract:** `OracleVault_06.sol`
**Pattern:** Defense in depth with fallback oracles

Implements defense in depth:
- Primary + fallback oracle with aggregation
- L2 sequencer uptime check with grace period
- Cross-oracle deviation check (max 5%)
- Median price calculation

**False Positive Trap:** Complex external calls (but correct implementation)

---

## Cross-Contract Reasoning Traps

These cases are designed to test cross-contract reasoning:

| Case | Trap Type | Challenge |
|------|-----------|-----------|
| AC-VULN-001 | Upgrade in Proxy | Must trace proxy -> implementation delegatecall |
| OR-VULN-002 | Decimal Propagation | Must trace oracle.decimals() return value |
| AC-SAFE-001 | Inherited Protection | Must resolve inheritance to avoid FP |

---

## Execution

### Run the Gauntlet

```bash
# Dry run (list cases)
./scripts/e2e/run_gauntlet_access_oracle.sh --dry-run

# Full execution
./scripts/e2e/run_gauntlet_access_oracle.sh --verbose

# With custom output
./scripts/e2e/run_gauntlet_access_oracle.sh --output .vrs/gauntlet/run-001
```

### Required Gates

| Gate | Description | Requirement |
|------|-------------|-------------|
| G0 | Preflight | Environment validation |
| G1 | Evidence | Proof tokens present |
| G2 | Graph | BSKG valid and complete |
| G4 | Mutation | Detection threshold met |

---

## Results Template

After execution, update this section with actual results:

```yaml
# Paste from final_results.yaml
run_id: "gauntlet-access-oracle-YYYYMMDD-HHMMSS"
suite_id: "gauntlet-access-oracle"
completed_at: "YYYY-MM-DDTHH:MM:SSZ"
total_cases: 10
metrics:
  true_positives: X
  true_negatives: X
  false_positives: X
  false_negatives: X
  score: X
  max_score: 10
passed: true/false
```

---

## False Positive Analysis

If false positives occur, document them here:

| Case | Expected | Actual | Root Cause | Fix |
|------|----------|--------|------------|-----|
| - | - | - | - | - |

---

## References

- **Manifest:** `tests/gauntlet/access_oracle_manifest.yaml`
- **Contracts:** `tests/gauntlet/access_oracle/`
- **Runner:** `scripts/e2e/run_gauntlet_access_oracle.sh`
- **Scoring Config:** `configs/gauntlet_scoring.yaml`
- **Spec:** `.planning/phases/07.3.3-adversarial-gauntlet/07.3.3-GAUNTLET-SPEC.md`
