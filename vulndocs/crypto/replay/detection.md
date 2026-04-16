# Replay Attack Detection

## Overview
Identify signatures without proper replay protection.

## Key Signals
- `uses_chainid = false`
- No nonce in signed message
- Missing EIP-712 domain separator
