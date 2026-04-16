#!/bin/bash
set -e
echo "=== Build Verification: stress-test-max-obfuscation-01 ==="
solc --bin --abi contracts/libraries/ComputeEngine.sol contracts/periphery/PolicyOracle.sol contracts/core/AdaptivePoolManager.sol 2>&1
solc --bin --abi contracts/libraries/ComputeEngine.sol contracts/periphery/PolicyOracle_safe.sol contracts/core/AdaptivePoolManager_safe.sol 2>&1
echo "All contracts compiled successfully."
