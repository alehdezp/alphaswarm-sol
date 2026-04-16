# Price Oracle Manipulation Detection

## Overview
Identify protocols using manipulable spot price oracles.

## Key Signals
- `reads_oracle_price = true`
- Reading from AMM reserves directly
- No TWAP averaging or Chainlink feed
