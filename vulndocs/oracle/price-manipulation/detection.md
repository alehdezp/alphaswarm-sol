# Detection: Price Manipulation

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| uses_spot_price | true | YES |
| has_twap_check | false | YES |
| reads_from_amm | true | NO |
| visibility | public, external | YES |
| performs_division | true | NO |

## Semantic Operations

**Vulnerable Sequence:**
- `READS_EXTERNAL_VALUE -> PERFORMS_DIVISION -> MODIFIES_CRITICAL_STATE`
- `CALLS_EXTERNAL(pool) -> READS_ORACLE -> MODIFIES_CRITICAL_STATE`

**Safe Sequence:**
- `READS_ORACLE(twap) -> PERFORMS_DIVISION -> MODIFIES_CRITICAL_STATE`
- `READS_EXTERNAL_VALUE -> VALIDATES_BOUNDS -> MODIFIES_CRITICAL_STATE`

## Behavioral Signatures

- `X:amm->C:spot->W:state` - AMM spot price directly to state
- `X:dex->C:reserves->C:ratio->W:bal` - Reserve ratio used for balance
- `R:reserves->C:div->W:price` - Division of reserves for pricing

## Detection Checklist

1. Function reads from DEX/AMM (Uniswap, Curve, Balancer)
2. Price calculated from instantaneous reserves
3. No TWAP (time-weighted average price) implementation
4. No multi-block averaging or delay
5. Price used for collateral valuation or swaps
6. No sanity bounds on price changes

## Advanced Detection: Median Oracle Aggregation

**Vulnerable Pattern (UwU Lend-style):**
- Median aggregation with majority manipulatable sources
- Multiple price feeds sharing same attack vector (e.g., all Curve pools)
- No liquidity threshold for price source inclusion
- Signature: `READS_MULTIPLE_SOURCES(median) -> MAJORITY_DEX_SPOT -> VULNERABLE`

**Key Risk Factors:**
1. Number of manipulatable sources >= (total sources / 2) + 1
2. All manipulatable sources use same protocol (Curve, Uniswap)
3. No validation of liquidity depth per source
4. Uses instantaneous spot price (`get_p()`) vs TWAP

## False Positive Indicators

- TWAP oracle used with sufficient window (>= 30 minutes)
- Chainlink, Band, or other decentralized oracle used
- Price change capped per block/transaction
- Flash loan detection via same-block transfer check
- Multiple price sources with median aggregation **AND** diverse protocols
- Liquidity threshold enforced for price source inclusion
- Read-only reentrancy guard on price functions
