# Detection: Sequencer Uptime

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| reads_oracle_price | true | YES |
| has_sequencer_uptime_check | false | YES |
| has_grace_period_check | false | NO |
| is_l2_deployment | true | YES |

## Semantic Operations

**Vulnerable Sequence:**
- `READS_ORACLE -> MODIFIES_CRITICAL_STATE`

**Safe Sequence:**
- `READS_SEQUENCER_STATUS -> VALIDATES_UPTIME -> READS_ORACLE -> MODIFIES_CRITICAL_STATE`
- `READS_SEQUENCER_STATUS -> VALIDATES_GRACE_PERIOD -> READS_ORACLE`

## Behavioral Signatures

- `X:oracle->C:price->W:state` - Oracle price to state without sequencer check
- `X:chainlink->R:price->W:liquidation` - Direct price to liquidation

## Detection Checklist

1. Contract deployed on L2 (Arbitrum, Optimism, etc.)
2. Uses Chainlink or similar price oracle
3. No call to sequencer uptime feed before price read
4. No grace period check after sequencer comes back online
5. Price used for liquidations or critical state changes
6. No fallback mechanism for sequencer downtime

## L2-Specific Requirements

For Arbitrum:
- Sequencer Uptime Feed: `0xFdB631F5EE196F0ed6FAa767959853A9F217697D`

For Optimism:
- Sequencer Uptime Feed: `0x371EAD81c9102C9BF4874A9075FFFf170F2Ee389`

## False Positive Indicators

- Sequencer uptime feed checked before any price reads
- Grace period (typically 1 hour) enforced after recovery
- Contract only deployed on L1 Ethereum
- Manual pause mechanism during sequencer downtime
- Price updates explicitly blocked when sequencer is down
