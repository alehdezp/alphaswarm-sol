#!/bin/bash
set -e
echo "=== Build Verification: flash-loan-vault-04 ==="
solc --bin --abi contracts/core/FlashVault.sol 2>&1
solc --bin --abi contracts/core/FlashVault_safe.sol 2>&1
echo "All contracts compiled successfully."
