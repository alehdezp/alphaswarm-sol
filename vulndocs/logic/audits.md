# Logic Category - Audit Research Notes

**Updated:** 2026-01-29 (Phase 7.2-03)
**Source:** audits.yaml audit discovery

This document tracks audit findings and real-world exploits related to logic vulnerabilities.
All URLs are logged in `.vrs/corpus/metadata/urls.yaml` with access timestamps.

## High-Impact Findings (2022-2026)

### 1. 1inch Yul Calldata Corruption (March 2025)
- **Loss:** $5M+ at risk (whitehat prevented)
- **Chain:** Ethereum
- **Type:** configuration
- **VulnDocs Path:** `logic/configuration/specifics/1inch-calldata-corruption/`
- **Audit ID:** `1inch-calldata-mar2025`
- **Key Finding:** Yul assembly incorrectly handled calldata, allowing exploitation
- **Source:** [1inch Blog](https://blog.1inch.io/vulnerability-discovered-in-resolver-contract/)

### 2. Clipper Single-Asset Invariant Bypass (December 2024)
- **Loss:** $450K
- **Chain:** Multiple (Optimism, Base, etc.)
- **Type:** invariant-violation
- **VulnDocs Path:** `logic/invariant-violation/specifics/clipper-single-asset-bypass/`
- **Audit ID:** `clipper-invariant-dec2024`
- **Key Finding:** Single-asset swap function violated pool invariants
- **Source:** [Clipper Post-Mortem](https://blog.clipper.exchange/clipper-dec-24-exploit-post-mortem/)

### 3. zkLend Precision Loss (February 2025)
- **Loss:** $9.6M
- **Chain:** StarkNet
- **Type:** arithmetic
- **VulnDocs Path:** `logic/arithmetic/specifics/zklend-precision-loss/`
- **Audit ID:** `zklend-precision-feb2025`
- **Key Finding:** First depositor inflation attack via precision manipulation
- **Source:** [zkLend Post-Mortem](https://zklend.io/blog/post-mortem)

### 4. Balancer v2 Rounding Error (November 2025)
- **Loss:** $128M
- **Chain:** Ethereum
- **Type:** arithmetic
- **VulnDocs Path:** `logic/arithmetic/specifics/balancer-v2-rounding/`
- **Audit ID:** `balancer-rounding-nov2025`
- **Key Finding:** Rounding direction error in stable pool math allowed extraction
- **Source:** [Balancer Forum](https://forum.balancer.fi/t/balancer-v2-vulnerability-disclosure-and-mitigation)

### 5. Euler v2 LTV Gap (October 2024)
- **Loss:** Potential bad debt (caught in audit)
- **Chain:** Ethereum
- **Type:** liquidation-mechanics
- **VulnDocs Path:** `logic/liquidation-mechanics/specifics/euler-ltv-gap/`
- **Audit ID:** `euler-v2-ltv-2024`
- **Key Finding:** Borrow LTV vs liquidation LTV gap could leave bad debt
- **Source:** [OpenZeppelin Audit](https://blog.openzeppelin.com/euler-vault-kit-evk-audit)

### 6. Uniswap v4 Hooks State Isolation (September 2024)
- **Loss:** N/A (caught in audit)
- **Chain:** Ethereum
- **Type:** state-isolation
- **VulnDocs Path:** `logic/state-isolation/`
- **Audit ID:** `uniswap-v4-hooks-m1-2024`
- **Key Finding:** Hook contracts must properly isolate state across pools
- **Source:** [OpenZeppelin Audit](https://blog.openzeppelin.com/uniswap-hooks-library-milestone-1-audit)

### 7. Nomad Zero-Root Validation (August 2022)
- **Loss:** $190M
- **Chain:** Multiple
- **Type:** validation
- **VulnDocs Path:** `logic/validation/` (to be created)
- **Audit ID:** `nomad-validation-aug2022`
- **Key Finding:** Zero-initialized root accepted as valid, allowing arbitrary messages
- **Source:** [Rekt News](https://rekt.news/nomad-rekt/)

## Detection Pattern Implications

### Arithmetic Signals
- Division before multiplication (precision loss)
- Rounding direction inconsistencies (down for protocol, up for user or vice versa)
- First depositor scenarios with empty pool state
- Integer overflow/underflow in unchecked blocks

### Invariant Violation Signals
- Single-asset operations on multi-asset pools
- State transitions that bypass validation checks
- Inconsistent state between related contracts

### Validation Signals
- Zero or default value acceptance without explicit checks
- Missing length/bounds validation
- Type confusion in calldata parsing

### State Isolation Signals (Uniswap v4 Hooks)
- Cross-pool state leakage
- Shared storage between independent pools
- Hook callback state pollution

## Ground Truth Mapping

| Audit ID | Ground Truth ID | Contract | Status |
|----------|-----------------|----------|--------|
| 1inch-calldata-mar2025 | - | 1inch Resolver | Pending |
| clipper-invariant-dec2024 | - | Clipper DEX | Pending |
| zklend-precision-feb2025 | - | zkLend | N/A (StarkNet) |
| balancer-rounding-nov2025 | - | Balancer v2 | Pending |
| euler-v2-ltv-2024 | - | Euler EVK | Pending |
| uniswap-v4-hooks-m1-2024 | - | Uniswap v4 Hooks | Pending |
| nomad-validation-aug2022 | - | Nomad Bridge | Pending |

## Uniswap v4 Specific Findings

The Uniswap v4 hooks audit is particularly relevant for Phase 7.2:
- Hook permission validation required
- Pool key validation needed
- State isolation between beforeSwap/afterSwap
- Reentrancy via hook callbacks

See `logic/state-isolation/` and `access-control/hooks-permission/` for related patterns.

## References

All sources logged in `.vrs/corpus/metadata/urls.yaml` under category `logic/*`.
