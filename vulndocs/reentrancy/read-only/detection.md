# Detection: Read-Only Reentrancy

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| is_view_function | true | YES |
| reads_external_state | true | YES |
| external_dependency | pool/oracle | YES |

## Key Pattern

View functions reading from external contracts (like Curve pools, Balancer vaults) during mid-transaction state can receive manipulated values.

## Detection Checklist

1. Function reads from external protocol (getVirtualPrice, etc.)
2. External protocol has callback mechanisms
3. Read happens without checking reentrancy flags
4. Value is used for pricing/collateral calculations
