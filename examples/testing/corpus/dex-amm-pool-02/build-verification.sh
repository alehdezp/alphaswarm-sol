#!/bin/bash
set -e
echo "=== Build Verification: dex-amm-pool-02 ==="
echo "Compiling vulnerable contracts..."
solc --bin --abi contracts/libraries/SwapMath.sol contracts/core/LiquidityEngine.sol 2>&1
echo ""
echo "Compiling safe contracts..."
solc --bin --abi contracts/libraries/SwapMath.sol contracts/core/LiquidityEngine_safe.sol 2>&1
echo ""
echo "All contracts compiled successfully."
