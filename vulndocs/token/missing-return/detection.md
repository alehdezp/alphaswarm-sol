# Missing Return Value Detection

## Overview
Identify unsafe token transfer patterns.

## Key Signals
- `uses_safe_erc20 = false`
- `token_return_guarded = false`
- Direct ERC20 interface calls
