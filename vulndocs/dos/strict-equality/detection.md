# Strict Equality Detection

## Overview
Identify balance checks using exact equality that can be manipulated.

## Key Signals
- `has_strict_equality_check = true`
- Comparison with `address(this).balance`
- Refund or finalize conditions using `==`
