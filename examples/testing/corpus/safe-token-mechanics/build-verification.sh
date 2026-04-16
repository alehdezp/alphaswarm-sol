#!/bin/bash
set -e
echo "=== Build Verification: safe-token-mechanics ==="
solc --bin --abi contracts/core/GuardedToken.sol 2>&1
echo "All contracts compiled successfully."
