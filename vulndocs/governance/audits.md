# Governance Category - Audit Research Notes

**Updated:** 2026-01-29 (Phase 7.2-03)
**Source:** audits.yaml audit discovery

This document tracks audit findings and real-world exploits related to governance vulnerabilities.
All URLs are logged in `.vrs/corpus/metadata/urls.yaml` with access timestamps.

## High-Impact Findings (2022-2026)

### 1. Tornado Cash Governance Hijack (May 2023)
- **Loss:** Full governance takeover
- **Chain:** Ethereum
- **Type:** proposal-manipulation
- **VulnDocs Path:** `governance/proposal-manipulation/`
- **Audit ID:** `tornado-governance-may2023`
- **Key Finding:** Malicious proposal granted control via selfdestruct + create2
- **Source:** [Rekt News](https://rekt.news/tornado-gov-rekt/)

## Detection Pattern Implications

### Proposal Manipulation Signals
- CREATE2 used in proposal execution
- SELFDESTRUCT + redeploy patterns
- Low quorum requirements
- Short voting/timelock periods
- Flash loan voting power accumulation

### Flash Loan Voting Signals
- Voting power snapshot in same block
- Token borrowing before governance action
- Missing snapshot delay

## Ground Truth Mapping

| Audit ID | Ground Truth ID | Contract | Status |
|----------|-----------------|----------|--------|
| tornado-governance-may2023 | - | Tornado Governance | Pending |

## References

All sources logged in `.vrs/corpus/metadata/urls.yaml` under category `governance/*`.
