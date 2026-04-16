# Detection: TWAP Manipulation

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| uses_twap_oracle | true | YES |
| twap_window_seconds | < 1800 | YES |
| twap_pool_liquidity | low | NO |
| visibility | public, external | YES |

## Semantic Operations

**Vulnerable Sequence:**
- `READS_ORACLE(twap_short) -> MODIFIES_CRITICAL_STATE`
- `CALLS_EXTERNAL(low_liquidity_pool) -> READS_ORACLE -> MODIFIES_CRITICAL_STATE`

**Safe Sequence:**
- `READS_ORACLE(twap_long) -> VALIDATES_BOUNDS -> MODIFIES_CRITICAL_STATE`
- `READS_ORACLE(twap) -> CROSS_VALIDATES(chainlink) -> MODIFIES_CRITICAL_STATE`

## Behavioral Signatures

- `X:twap->C:price->W:state` - TWAP to state without validation
- `X:pool->R:cumulative->C:avg->W:collateral` - Cumulative price to collateral
- `R:observations->C:twap->W:liquidation` - Observations to liquidation

## Detection Checklist

1. Protocol uses TWAP oracle (Uniswap V2/V3 style)
2. TWAP window is less than 30 minutes
3. Source pool has low liquidity (< $10M TVL)
4. No cross-validation with other price sources
5. No bounds on acceptable price deviation
6. Price used for high-value operations (liquidations, large swaps)

## TWAP Window Analysis

| Window | Manipulation Difficulty | Recommendation |
|--------|------------------------|----------------|
| < 10 min | Easy | Never use |
| 10-30 min | Moderate | Risky |
| 30-60 min | Hard | Acceptable |
| > 60 min | Very Hard | Recommended |

## Liquidity Requirements

Minimum TVL recommendations based on protocol exposure:

| Protocol TVL | Min Pool Liquidity |
|--------------|-------------------|
| < $1M | $5M |
| $1M - $10M | $20M |
| $10M - $100M | $50M |
| > $100M | $100M+ |

## False Positive Indicators

- TWAP window >= 30 minutes
- Source pool TVL > $50M
- Cross-validation with Chainlink or Band
- Maximum price change bounds enforced
- Economic analysis shows manipulation unprofitable
- Multiple TWAP sources aggregated
