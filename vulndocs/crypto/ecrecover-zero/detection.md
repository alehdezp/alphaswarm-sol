# ECRecover Zero Address Detection

## Overview
Identify ecrecover usage without zero address validation.

## Key Signals
- `uses_ecrecover = true`
- `checks_zero_address = false`
- Signer compared directly to expected
