# Slippage Exploitation Detection

## Overview
Identify swaps with inadequate slippage protection.

## Key Signals
- `risk_missing_slippage_parameter = true`
- `risk_missing_deadline_check = true`
- Hardcoded 0 or 100% slippage
