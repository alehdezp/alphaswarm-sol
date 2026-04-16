# Oracle Category - Audit Research Notes

**Updated:** 2026-01-29 (Phase 7.2-03)
**Source:** audits.yaml audit discovery

This document tracks audit findings and real-world exploits related to oracle vulnerabilities.
All URLs are logged in `.vrs/corpus/metadata/urls.yaml` with access timestamps.

## High-Impact Findings (2020-2026)

### 1. UwU Lend Curve Spot Manipulation (June 2024)
- **Loss:** $23M
- **Chain:** Ethereum
- **Type:** price-manipulation
- **VulnDocs Path:** `oracle/price-manipulation/specifics/uwu-curve-spot-manipulation/`
- **Audit ID:** `uwu-lend-oracle-jun2024`
- **Key Finding:** Direct Curve pool spot price used without TWAP protection
- **Source:** [Neptune Mutual Analysis](https://medium.com/neptune-mutual/understanding-the-uwu-lend-exploit-b32ea552f030)

### 2. Mango Markets Oracle Manipulation (October 2022)
- **Loss:** $117M
- **Chain:** Solana
- **Type:** price-manipulation
- **VulnDocs Path:** `oracle/price-manipulation/`
- **Audit ID:** `mango-oracle-oct2022`
- **Key Finding:** Low liquidity perpetual oracle allowed massive price manipulation
- **Source:** [Rekt News](https://rekt.news/mango-markets-rekt/)

### 3. Beanstalk Flash Loan Governance (April 2022)
- **Loss:** $182M
- **Chain:** Ethereum
- **Type:** price-manipulation (combined with governance)
- **VulnDocs Path:** `oracle/price-manipulation/`
- **Audit ID:** `beanstalk-oracle-apr2022`
- **Key Finding:** Flash loan used to manipulate governance vote and drain protocol
- **Source:** [Rekt News](https://rekt.news/beanstalk-rekt/)

### 4. Inverse Finance Keep3r Oracle (April 2022)
- **Loss:** $15M
- **Chain:** Ethereum
- **Type:** price-manipulation
- **VulnDocs Path:** `oracle/price-manipulation/`
- **Audit ID:** `inverse-oracle-apr2022`
- **Key Finding:** On-chain TWAP oracle manipulated via large swap
- **Source:** [Rekt News](https://rekt.news/inverse-rekt/)

### 5. Harvest Finance Flash Loan (October 2020)
- **Loss:** $34M
- **Chain:** Ethereum
- **Type:** price-manipulation
- **VulnDocs Path:** `oracle/price-manipulation/`
- **Audit ID:** `harvest-flashloan-oct2020`
- **Key Finding:** Flash loan used to manipulate Curve pool price for arbitrage
- **Source:** [Rekt News](https://rekt.news/harvest-finance-rekt/)

## L2 Sequencer Guidance (Critical for 2025+)

### Chainlink L2 Sequencer Uptime Feeds
- **Type:** guidance
- **VulnDocs Path:** `oracle/sequencer-uptime/`
- **Audit ID:** `chainlink-l2-sequencer-guidance`
- **Key Finding:** Must wait grace period after sequencer restart before trusting prices
- **Economic Risk:** Potential manipulation during sequencer downtime recovery window
- **Source:** [Chainlink Docs](https://docs.chain.link/data-feeds/l2-sequencer-uptime-feeds)

**Pattern Implications:**
- Oracle reads on L2 MUST check sequencer uptime feed
- Grace period after restart is REQUIRED
- Pattern: `oracle-l2-sequencer-grace-missing` (exemplar for Phase 7.2)

## Detection Pattern Implications

### Price Manipulation Signals
- Direct spot price reads without TWAP
- Single-block price calculations
- Flash loan borrowing in same transaction as price-dependent actions
- Missing slippage protection

### Stale Price Signals
- No `updatedAt` timestamp validation
- No heartbeat check against oracle timeout
- No sequencer uptime check on L2

### TWAP Manipulation Signals
- Short TWAP windows (<30 minutes)
- Low liquidity pools as price source
- Multi-block transactions possible

## Ground Truth Mapping

| Audit ID | Ground Truth ID | Contract | Status |
|----------|-----------------|----------|--------|
| uwu-lend-oracle-jun2024 | - | UwU Lend | Pending |
| mango-oracle-oct2022 | - | Mango Markets | N/A (Solana) |
| beanstalk-oracle-apr2022 | - | Beanstalk | Pending |
| inverse-oracle-apr2022 | - | Inverse Finance | Pending |
| harvest-flashloan-oct2020 | - | Harvest Finance | Pending |
| chainlink-l2-sequencer-guidance | - | Reference | Guidance |

## Exemplar Pattern: oracle-l2-sequencer-grace-missing

This audit research directly informs the Phase 7.2 exemplar pattern:
- **ID:** `oracle-l2-sequencer-grace-missing`
- **Severity:** High (Critical if liquidation/collateral involved)
- **Detection:** Missing grace period after sequencer restart
- **Chain Scope:** Optimism, Arbitrum, Base, zkSync, Polygon zkEVM

See `oracle/sequencer-uptime/` for pattern definitions.

## References

All sources logged in `.vrs/corpus/metadata/urls.yaml` under category `oracle/*`.
