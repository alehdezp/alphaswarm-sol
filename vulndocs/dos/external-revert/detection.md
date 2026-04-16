# External Revert Detection

## Overview
Identify external calls that can revert and block execution.

## Key Signals
- `uses_transfer = true` without try/catch
- External calls in loops without error handling
- Push over pull payment pattern
