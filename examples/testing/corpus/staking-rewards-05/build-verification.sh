#!/bin/bash
set -e
echo "=== Build Verification: staking-rewards-05 ==="
solc --bin --abi contracts/core/MeritPool.sol 2>&1
solc --bin --abi contracts/core/MeritPool_safe.sol 2>&1
echo "All contracts compiled successfully."
