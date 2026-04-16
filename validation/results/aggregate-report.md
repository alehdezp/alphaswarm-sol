# BSKG Validation Aggregate Report

## Summary

- **Projects analyzed:** 5
- **Projects:** blur-exchange, compound-v3, ens, uniswap-v3, yearn-v3
- **Project types:** nft_marketplace, dex, registry, lending, yield_vault

## Coverage Metrics

| Metric | Value |
|--------|-------|
| Total findings | 44 |
| BSKG detectable | 37 |
| Coverage | 84.1% |
| High/Critical total | 10 |
| High/Critical detectable | 10 |
| High/Critical coverage | 100.0% |

## Findings by Category

| Category | Total | BSKG Detectable | Coverage |
|----------|-------|----------------|----------|
| access_control | 8 | 8 | 100% |
| arithmetic | 3 | 3 | 100% |
| business_logic | 2 | 0 | 0% |
| cryptographic | 1 | 0 | 0% |
| dos | 6 | 5 | 83% |
| informational | 3 | 0 | 0% |
| input_validation | 1 | 1 | 100% |
| mev_slippage | 7 | 7 | 100% |
| oracle_manipulation | 5 | 5 | 100% |
| reentrancy | 3 | 3 | 100% |
| signature | 2 | 2 | 100% |
| timestamp | 1 | 1 | 100% |
| unchecked_return | 1 | 1 | 100% |
| upgrade_proxy | 1 | 1 | 100% |

## Findings by Severity

| Severity | Total | BSKG Detectable | Coverage |
|----------|-------|----------------|----------|
| HIGH | 10 | 10 | 100% |
| MEDIUM | 20 | 17 | 85% |
| LOW | 14 | 10 | 71% |

## Findings by Project Type

| Type | Projects | Total | BSKG Detectable |
|------|----------|-------|----------------|
| dex | uniswap-v3 | 9 | 8 |
| lending | compound-v3 | 8 | 6 |
| nft_marketplace | blur-exchange | 10 | 8 |
| registry | ens | 8 | 8 |
| yield_vault | yearn-v3 | 9 | 7 |

## Out of Scope (Gaps)

These findings require semantic understanding and are not detectable by VKG:

### business_logic
- compound-v3: Complex business logic in collateral factor calculation
- uniswap-v3: Liquidity position NFT transfer without fee collection

### cryptographic
- blur-exchange: Merkle proof collision for bulk orders

### dos
- yearn-v3: Deposit limit can lock funds temporarily

### informational
- blur-exchange: Missing event emission on critical state changes
- compound-v3: Event emission missing in admin functions
- yearn-v3: Missing event on management fee change
