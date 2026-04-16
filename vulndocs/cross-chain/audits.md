# Cross-Chain Category - Audit Research Notes

**Updated:** 2026-01-29 (Phase 7.2-03)
**Source:** audits.yaml audit discovery

This document tracks audit findings and real-world exploits related to cross-chain vulnerabilities.
All URLs are logged in `.vrs/corpus/metadata/urls.yaml` with access timestamps.

## High-Impact Findings (2022-2026)

### 1. Wormhole Guardian Signature Bypass (February 2022)
- **Loss:** $320M
- **Chain:** Solana/Ethereum
- **Type:** signature-validation
- **VulnDocs Path:** `cross-chain/signature-validation/` (to be linked)
- **Audit ID:** `wormhole-signature-feb2022`
- **Key Finding:** Solana program allowed bypassing guardian signatures
- **Source:** [Rekt News](https://rekt.news/wormhole-rekt/)

### 2. Ronin Network Validator Compromise (March 2022)
- **Loss:** $625M
- **Chain:** Ronin
- **Type:** bridge-compromise
- **VulnDocs Path:** `cross-chain/bridge-compromise/`
- **Audit ID:** `ronin-multisig-mar2022`
- **Key Finding:** 5/9 validator keys compromised allowing drain
- **Source:** [Rekt News](https://rekt.news/ronin-network-rekt/)

## Detection Pattern Implications

### Signature Validation Signals
- Missing signature verification
- Incorrect signature recovery (ecrecover issues)
- Malleable signatures accepted
- Insufficient signer threshold

### Bridge Compromise Signals
- Low validator count or threshold
- Key management vulnerabilities
- Single point of failure in validator set
- Missing replay protection

### Message Validation Signals
- Zero-root or default value acceptance
- Missing source chain verification
- Insufficient payload validation

## Ground Truth Mapping

| Audit ID | Ground Truth ID | Contract | Status |
|----------|-----------------|----------|--------|
| wormhole-signature-feb2022 | - | Wormhole | N/A (Solana) |
| ronin-multisig-mar2022 | - | Ronin Bridge | Pending |

## References

All sources logged in `.vrs/corpus/metadata/urls.yaml` under category `cross-chain/*`.
