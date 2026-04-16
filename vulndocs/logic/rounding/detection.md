# Rounding Errors Detection

## Overview
Identify rounding issues favoring attackers.

## Key Signals
- `uses_division = true`
- Division before multiplication
- Rounding down on user payments, up on protocol costs
