#!/bin/bash
set -e
echo "=== Build Verification: yield-aggregator-03 ==="
solc --bin --abi contracts/core/YieldRouter.sol 2>&1
solc --bin --abi contracts/core/YieldRouter_safe.sol 2>&1
echo "All contracts compiled successfully."
