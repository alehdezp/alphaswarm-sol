# Threat-to-Pattern Mapping Matrix

**Status:** Specification
**Version:** 1.0.0
**Source:** CRITIQUE-REMEDIATION.md WS1.3
**Affects:** Phase 2, patterns/

---

## Overview

Every attack surface in VKG's threat model MUST have:
1. **At least one deterministic pattern** for detection
2. **At least one safe set contract** proving low false positives

This matrix tracks coverage and identifies gaps.

---

## Threat Matrix

| # | Attack Surface | Patterns | Safe Set Contracts | Status |
|---|----------------|----------|-------------------|--------|
| 1 | [Access Control](#1-access-control) | 5 patterns | 3 contracts | COVERED |
| 2 | [Reentrancy](#2-reentrancy) | 4 patterns | 2 contracts | COVERED |
| 3 | [Oracle Manipulation](#3-oracle-manipulation) | 6 patterns | 2 contracts | COVERED |
| 4 | [MEV/Ordering](#4-mevordering) | 4 patterns | 1 contract | COVERED |
| 5 | [Governance](#5-governance) | 2 patterns | 1 contract | PARTIAL |
| 6 | [Upgradeability](#6-upgradeability) | 5 patterns | 2 contracts | COVERED |
| 7 | [Token Flaws](#7-token-flaws) | 6 patterns | 2 contracts | COVERED |
| 8 | [Denial of Service](#8-denial-of-service) | 3 patterns | 0 contracts | GAP |

---

## 1. Access Control

**Attack:** Missing or bypassable authorization gates allow unauthorized state changes.

### Patterns

| Pattern ID | Name | Severity | Tier |
|------------|------|----------|------|
| `auth-001` | Missing Access Gate on State Write | High | A |
| `auth-002` | tx.origin Authentication | High | A |
| `auth-003` | Privileged State Without Protection | Critical | A |
| `vm-001` | Public Value Transfer Without Gate | Critical | A |
| `vm-002` | External Wrapper Without Gate | High | A |

### Safe Set Contracts

| Contract | Source | Why Safe |
|----------|--------|----------|
| `OZ Ownable.sol` | OpenZeppelin v5 | Proper onlyOwner modifier |
| `OZ AccessControl.sol` | OpenZeppelin v5 | Role-based access with checks |
| `Compound Comptroller.sol` | Compound v2 | Admin-gated functions |

### Pattern Properties

```yaml
core_signal:
  - visibility: [public, external]
  - writes_privileged_state: true
  - has_access_gate: false

discriminators:
  - NOT is_view_or_pure
  - NOT is_constructor
  - NOT is_receive_or_fallback
```

---

## 2. Reentrancy

**Attack:** External calls allow callback before state updates, enabling repeated withdrawals.

### Patterns

| Pattern ID | Name | Severity | Tier |
|------------|------|----------|------|
| `reentrancy-classic` | State Write After External Call | Critical | A |
| `reentrancy-cross-function` | Cross-Function Reentrancy | High | A |
| `reentrancy-read-only` | Read-Only Reentrancy | Medium | A |
| `reentrancy-erc777` | ERC777 Callback Reentrancy | High | A |

### Safe Set Contracts

| Contract | Source | Why Safe |
|----------|--------|----------|
| `OZ ReentrancyGuard.sol` | OpenZeppelin v5 | nonReentrant modifier |
| `Uniswap V3 Pool.sol` | Uniswap v3 | lock modifier, CEI pattern |

### Pattern Properties

```yaml
core_signal:
  - state_write_after_external_call: true
  - OR has_all_operations: [TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]
    sequence_order:
      before: TRANSFERS_VALUE_OUT
      after: WRITES_USER_BALANCE

discriminators:
  - has_reentrancy_guard: false
  - NOT calls_only_trusted_contracts
```

---

## 3. Oracle Manipulation

**Attack:** Stale, manipulable, or missing price feed checks enable value extraction.

### Patterns

| Pattern ID | Name | Severity | Tier |
|------------|------|----------|------|
| `oracle-staleness` | Missing Staleness Check | High | A |
| `oracle-roundid` | Missing RoundId Validation | Medium | A |
| `oracle-sequencer` | Missing L2 Sequencer Check | High | A |
| `oracle-twap-window` | TWAP Window Too Short | Medium | A |
| `oracle-spot-price` | Spot Price Dependency | High | A |
| `oracle-decimals` | Missing Decimals Normalization | Medium | A |

### Safe Set Contracts

| Contract | Source | Why Safe |
|----------|--------|----------|
| `Chainlink PriceConsumerV3.sol` | Chainlink Examples | Full validation |
| `Aave V3 AaveOracle.sol` | Aave v3 | Staleness + fallback |

### Pattern Properties

```yaml
core_signal:
  - reads_oracle_price: true
  - OR calls_chainlink_feed: true
  - OR reads_external_value: true

discriminators:
  - has_staleness_check: false
  - OR has_roundid_check: false
```

---

## 4. MEV/Ordering

**Attack:** Transaction ordering exploitation via sandwich attacks, backruns, or deadline bypass.

### Patterns

| Pattern ID | Name | Severity | Tier |
|------------|------|----------|------|
| `mev-slippage-missing` | Missing Slippage Protection | High | A |
| `mev-deadline-missing` | Missing Deadline Check | Medium | A |
| `mev-frontrun` | Frontrunnable State Change | High | A |
| `mev-backrun` | Backrunnable Price Update | Medium | A |

### Safe Set Contracts

| Contract | Source | Why Safe |
|----------|--------|----------|
| `Uniswap V3 SwapRouter.sol` | Uniswap v3 | deadline + amountOutMinimum |

### Pattern Properties

```yaml
core_signal:
  - swap_like: true
  - OR has_price_impact: true

discriminators:
  - risk_missing_slippage_parameter: true
  - OR risk_missing_deadline_check: true
```

---

## 5. Governance

**Attack:** Timelock bypass, voting power inflation, or proposal manipulation.

### Patterns

| Pattern ID | Name | Severity | Tier |
|------------|------|----------|------|
| `gov-timelock-bypass` | Timelock Bypass | Critical | A |
| `gov-flash-loan-vote` | Flash Loan Voting | High | A |

### Safe Set Contracts

| Contract | Source | Why Safe |
|----------|--------|----------|
| `Compound GovernorBravo.sol` | Compound | Proper timelock integration |

### Coverage Gap

**Missing Patterns:**
- `gov-vote-inflation`: Voting power inflation via token manipulation
- `gov-proposal-spam`: Proposal spam via low threshold

**Action Required:** Create patterns or document as out-of-scope.

---

## 6. Upgradeability

**Attack:** Proxy/implementation mismatch, storage collision, or uninitialized implementation.

### Patterns

| Pattern ID | Name | Severity | Tier |
|------------|------|----------|------|
| `upgrade-no-gap` | Missing Storage Gap | High | A |
| `upgrade-no-guard` | Unprotected Upgrade Function | Critical | A |
| `upgrade-initializer` | Missing Initializer Protection | High | A |
| `upgrade-selfdestruct` | Selfdestruct in Implementation | Critical | A |
| `upgrade-delegatecall` | Delegatecall to Untrusted | Critical | A |

### Safe Set Contracts

| Contract | Source | Why Safe |
|----------|--------|----------|
| `OZ TransparentUpgradeableProxy.sol` | OpenZeppelin v5 | Proper admin separation |
| `OZ UUPSUpgradeable.sol` | OpenZeppelin v5 | _authorizeUpgrade protection |

### Pattern Properties

```yaml
core_signal:
  - is_proxy_like: true
  - OR is_upgradeable: true

discriminators:
  - upgradeable_without_storage_gap: true
  - OR has_unprotected_upgrade: true
```

---

## 7. Token Flaws

**Attack:** Non-standard token behavior, fee-on-transfer, or return value issues.

### Patterns

| Pattern ID | Name | Severity | Tier |
|------------|------|----------|------|
| `token-unchecked-return` | Unchecked ERC20 Return | High | A |
| `token-fee-on-transfer` | Fee-on-Transfer Not Handled | Medium | A |
| `token-reentrancy-erc777` | ERC777 Token Reentrancy | High | A |
| `token-approval-race` | Approval Race Condition | Medium | A |
| `token-infinite-approval` | Infinite Approval Risk | Low | A |
| `token-non-standard` | Non-Standard Token Interface | Medium | A |

### Safe Set Contracts

| Contract | Source | Why Safe |
|----------|--------|----------|
| `OZ ERC20.sol` | OpenZeppelin v5 | Standard compliant |
| `OZ SafeERC20.sol` | OpenZeppelin v5 | Safe transfer wrappers |

### Pattern Properties

```yaml
core_signal:
  - uses_erc20_transfer: true
  - OR uses_erc20_approve: true

discriminators:
  - uses_safe_erc20: false
  - token_return_guarded: false
```

---

## 8. Denial of Service

**Attack:** Unbounded loops, gas griefing, or block-dependent operations.

### Patterns

| Pattern ID | Name | Severity | Tier |
|------------|------|----------|------|
| `dos-unbounded-loop` | Unbounded Loop | High | A |
| `dos-external-in-loop` | External Call in Loop | Medium | A |
| `dos-strict-equality` | Strict Equality DoS | Medium | A |

### Safe Set Contracts

**COVERAGE GAP: No safe set contracts defined.**

**Action Required:**
1. Add `OZ EnumerableSet.sol` - bounded iteration
2. Add Uniswap batching contracts - chunked processing
3. Create synthetic safe contracts for testing

### Pattern Properties

```yaml
core_signal:
  - has_unbounded_loop: true
  - OR external_calls_in_loop: true
  - OR has_strict_equality_check: true

discriminators:
  - loop_has_bound: false
  - loop_iterations_from_user_input: true
```

---

## Coverage Summary

```
Coverage Matrix
===============

Attack Surface        | Patterns | Safe Set | Status
----------------------|----------|----------|--------
Access Control        |    5     |    3     | COVERED
Reentrancy            |    4     |    2     | COVERED
Oracle Manipulation   |    6     |    2     | COVERED
MEV/Ordering          |    4     |    1     | COVERED
Governance            |    2     |    1     | PARTIAL (missing vote-inflation)
Upgradeability        |    5     |    2     | COVERED
Token Flaws           |    6     |    2     | COVERED
Denial of Service     |    3     |    0     | GAP (no safe set)

Total Patterns: 35
Total Safe Set: 15
Coverage: 7/8 attack surfaces fully covered
```

---

## Gap Remediation Plan

### 1. Governance Gaps

| Gap | Action | Priority | Phase |
|-----|--------|----------|-------|
| Vote inflation pattern | Create `gov-vote-inflation` pattern | SHOULD | 2 |
| Proposal spam pattern | Create `gov-proposal-spam` pattern | COULD | Future |

### 2. DoS Safe Set Gap

| Gap | Action | Priority | Phase |
|-----|--------|----------|-------|
| No safe set | Add OZ EnumerableSet to safe set | MUST | 2 |
| No safe set | Create synthetic bounded-loop contract | MUST | 2 |

---

## Validation Commands

```bash
# Verify threat coverage (AUTOMATED - runs in CI)
python scripts/validate_threat_matrix.py

# CI mode (exits 1 on errors)
python scripts/validate_threat_matrix.py --ci

# Output:
# Attack Surface Coverage: 7/8 (87.5%)
# Gaps:
#   - DoS: No safe set contracts
#   - Governance: Missing vote-inflation pattern

# List patterns by attack surface
vkg patterns list --by-threat

# Validate safe set has no false positives
vkg analyze tests/safe-set/ --expect-clean
```

## CI Integration

This matrix is validated by `scripts/validate_threat_matrix.py` which:
1. Loads all patterns from `vulndocs/*/*/patterns/*.yaml`
2. Categorizes them by threat surface
3. Validates all matrix-referenced patterns exist
4. Reports coverage gaps

**CI Check (Phase 2):**
```yaml
# .github/workflows/ci.yml
- name: Validate Threat Matrix
  run: python scripts/validate_threat_matrix.py --ci
```

---

## Safe Set Locations

```
tests/safe-set/
├── access-control/
│   ├── OZ_Ownable.sol
│   ├── OZ_AccessControl.sol
│   └── Compound_Comptroller.sol
├── reentrancy/
│   ├── OZ_ReentrancyGuard.sol
│   └── Uniswap_V3_Pool.sol
├── oracle/
│   ├── Chainlink_PriceConsumer.sol
│   └── Aave_Oracle.sol
├── mev/
│   └── Uniswap_SwapRouter.sol
├── governance/
│   └── Compound_GovernorBravo.sol
├── upgradeability/
│   ├── OZ_TransparentProxy.sol
│   └── OZ_UUPS.sol
├── token/
│   ├── OZ_ERC20.sol
│   └── OZ_SafeERC20.sol
└── dos/
    └── # GAP - needs contracts
```

---

## Acceptance Criteria

- [ ] Matrix created with all 8 attack surfaces
- [ ] Each has at least 1 pattern or marked as gap
- [ ] Safe set contracts identified for 7/8 surfaces
- [ ] Gap remediation plan documented
- [ ] Validation command specified: `vkg threat-coverage`
- [ ] Safe set directory structure defined

---

*Threat-to-Pattern Mapping Matrix | Version 1.0.0 | 2026-01-07*
