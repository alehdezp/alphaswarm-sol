# Reentrancy Category - Audit Research Notes

**Updated:** 2026-01-29 (Phase 7.2-03)
**Source:** audits.yaml audit discovery

This document tracks audit findings and real-world exploits related to reentrancy vulnerabilities.
All URLs are logged in `.vrs/corpus/metadata/urls.yaml` with access timestamps.

## High-Impact Findings (2022-2026)

### 1. GMX v1 Cross-Function Reentrancy (July 2025)
- **Loss:** $42M (partially recovered via bounty)
- **Chain:** Arbitrum
- **Type:** cross-function
- **VulnDocs Path:** `reentrancy/cross-function/specifics/gmx-v1-reentrancy/`
- **Audit ID:** `gmx-v1-reentrancy-jul2025`
- **Key Finding:** Cross-function reentrancy via ETH refund callback combined with non-atomic state updates
- **Source:** [Halborn Post-Mortem](https://www.halborn.com/blog/post/explained-the-gmx-hack-july-2025)

### 2. Penpie Permissionless Callback (September 2024)
- **Loss:** $27M
- **Chain:** Ethereum
- **Type:** classic
- **VulnDocs Path:** `reentrancy/classic/specifics/penpie-permissionless-callback/`
- **Audit ID:** `penpie-reentrancy-sep2024`
- **Key Finding:** Market creation with attacker-controlled callback allowed classic reentrancy
- **Source:** [Penpie Post-Mortem](https://blog.penpiexyz.io/penpie-post-mortem-report-1ac9863b663a)

### 3. Curve Vyper Reentrancy (August 2023)
- **Loss:** $70M+ across pools
- **Chain:** Ethereum
- **Type:** read-only (compiler bug)
- **VulnDocs Path:** `reentrancy/read-only/`
- **Audit ID:** `curve-readonly-reentrancy-aug2023`
- **Key Finding:** Vyper compiler bug bypassed reentrancy lock
- **Source:** [HackMD Analysis](https://hackmd.io/@vyperlang/HJUgNMhs2)

### 4. Euler Finance Donation Reentrancy (March 2023)
- **Loss:** $200M (recovered)
- **Chain:** Ethereum
- **Type:** cross-function
- **VulnDocs Path:** `reentrancy/cross-function/`
- **Audit ID:** `euler-reentrancy-mar2023`
- **Key Finding:** donateToReserves allowed manipulation before liquidation check
- **Source:** [Halborn Post-Mortem](https://www.halborn.com/blog/post/explained-the-euler-finance-hack-march-2023)

### 5. Fei/Rari Fuse Pool Reentrancy (April 2022)
- **Loss:** $80M
- **Chain:** Ethereum
- **Type:** classic
- **VulnDocs Path:** `reentrancy/classic/`
- **Audit ID:** `fei-tribe-merge-apr2022`
- **Key Finding:** Reentrancy in Fuse pool borrow functions
- **Source:** [Fei Post-Mortem](https://medium.com/fei-protocol/fei-rari-hack-post-mortem-7fa9c7a3e3a0)

### 6. Level Finance Referral Reentrancy (May 2023)
- **Loss:** $1.1M
- **Chain:** BSC
- **Type:** classic
- **VulnDocs Path:** `reentrancy/classic/`
- **Audit ID:** `level-finance-referral-may2023`
- **Key Finding:** Referral claim function vulnerable to reentrancy
- **Source:** [Rekt News](https://rekt.news/level-finance-rekt/)

## Detection Pattern Implications

### Cross-Function Pattern Signals
- Look for `state_write_after_external_call` + `shared_state_variables > 1`
- `nonReentrant` on single function is NOT sufficient
- Check for global reentrancy guards across all state-modifying functions

### Classic Pattern Signals
- External call before state update
- Callback opportunity via ETH transfer or token hooks
- Missing or partial reentrancy guards

### Read-Only Pattern Signals
- View functions reading stale state during reentrancy
- External protocols relying on mid-execution state
- Compiler-level protections can have bugs

## Ground Truth Mapping

| Audit ID | Ground Truth ID | Contract | Status |
|----------|-----------------|----------|--------|
| gmx-v1-reentrancy-jul2025 | - | GMX PositionRouter | Pending |
| penpie-reentrancy-sep2024 | - | Penpie Market | Pending |
| curve-readonly-reentrancy-aug2023 | - | Curve Pools | Pending |
| euler-reentrancy-mar2023 | - | Euler EToken | Pending |
| fei-tribe-merge-apr2022 | - | Rari Fuse | Pending |
| level-finance-referral-may2023 | - | Level Finance | Pending |

## References

All sources logged in `.vrs/corpus/metadata/urls.yaml` under category `reentrancy/*`.
