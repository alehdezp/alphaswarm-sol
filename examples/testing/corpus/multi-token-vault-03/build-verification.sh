#!/bin/bash
set -e
echo "=== Build Verification: multi-token-vault-03 ==="
solc --bin --abi contracts/libraries/TokenAccounting.sol contracts/core/MultiAssetVault.sol 2>&1
solc --bin --abi contracts/libraries/TokenAccounting.sol contracts/core/MultiAssetVault_safe.sol 2>&1
echo "All contracts compiled successfully."
