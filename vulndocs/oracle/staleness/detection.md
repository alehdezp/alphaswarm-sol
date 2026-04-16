# Detection: Stale Price Data

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| reads_oracle_price | true | YES |
| has_staleness_check | false | YES |
| checks_round_completeness | false | NO |
| visibility | public, external | YES |

## Semantic Operations

**Vulnerable Sequence:**
- `READS_ORACLE -> MODIFIES_CRITICAL_STATE`
- `CALLS_EXTERNAL(oracle) -> PERFORMS_DIVISION -> MODIFIES_CRITICAL_STATE`

**Safe Sequence:**
- `READS_ORACLE -> VALIDATES_FRESHNESS -> MODIFIES_CRITICAL_STATE`
- `CALLS_EXTERNAL(oracle) -> VALIDATES_ROUND -> PERFORMS_DIVISION`

## Behavioral Signatures

- `X:oracle->C:price->W:state` - Oracle price to state without validation
- `X:chainlink->R:price->W:bal` - Chainlink to balance without freshness check
- `R:latestRound->C:price->W:collateral` - Round data to collateral

## Detection Checklist

1. Function calls `latestRoundData()` or similar oracle method
2. Price value is extracted and used
3. No check on `updatedAt` timestamp
4. No check on `answeredInRound >= roundId`
5. No maximum age threshold enforced
6. Price used for liquidation, collateral, or swap calculations

## Chainlink-Specific Checks

```solidity
// All these should be present:
require(price > 0, "Invalid price");
require(updatedAt > 0, "Round not complete");
require(answeredInRound >= roundId, "Stale round");
require(block.timestamp - updatedAt < MAX_STALENESS, "Stale price");
```

## False Positive Indicators

- `updatedAt` compared against `block.timestamp - threshold`
- `answeredInRound >= roundId` validation present
- Heartbeat interval checked (asset-specific)
- Fallback price source for stale data scenarios
- Circuit breaker on stale data detection
- Price cached with expiry timestamp
