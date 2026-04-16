# Unbounded Loop Detection

## Overview
Detect loops iterating over dynamic arrays without fixed bounds.

## Key Signals
- `has_unbounded_loop = true`
- Loop over storage array with `.length`
- No pagination or batch limit

## Detection Pattern
```yaml
match:
  tier_a:
    all:
      - property: has_unbounded_loop
        value: true
```
